import network, espnow, machine, utime, random, time
from machine import Pin, PWM, Timer
from umqtt.simple import MQTTClient

# WiFi credentials
WIFI_SSID = "Berkeley-IoT"
WIFI_PASS = "fG8jb-m*"

# Connect to WiFi
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(WIFI_SSID, WIFI_PASS)

e = espnow.ESPNow()
e.active(True)
e.irecv(True)
while not sta.isconnected():
    print("Connecting to WiFi...")
    time.sleep(0.5)
print("WiFi connected!")
sta.disconnect()
sta.config(channel=4)

#Set up MQTT callback, which takes the most recent data from the feed and parses it as an integer
target_number = None
received_number = None


# User-defined settings
ELAPSED_TIME = 30  # Time interval in milliseconds for calculations and state changes
ENCODER_RESOLUTION = 700 # FOr DFRobot 12V DC motor it is 700. 

# Define motor control pins for the Cytron Maker Drive
MOTOR_M1A_PIN = machine.PWM(machine.Pin(27))
MOTOR_M1B_PIN = machine.PWM(machine.Pin(33))

# Define encoder pins
ENCODER_A_PIN = machine.Pin(25, machine.Pin.IN, machine.Pin.PULL_UP)
ENCODER_B_PIN = machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_UP)
led_13 = Pin(13, Pin.OUT)
led_12 = Pin(12, Pin.OUT)

# Motor speed
SPEED = 1023  # Set to maximum speed
POSITION_TOLERANCE = 1  

# Encoder counter
encoder_count = 0

def encoder_handler(pin):
    global encoder_position
    a = ENCODER_A_PIN.value()
    b = ENCODER_B_PIN.value()
    
    # Check both edges for better accuracy [5]
    if (a ^ b) if (pin == ENCODER_A_PIN) else (b ^ a):
        encoder_position += 1 if (a ^ b) else -1

# Attach the interrupt handlers to the encoder pins
ENCODER_A_PIN.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)
ENCODER_B_PIN.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)
# Global Variables
global encoder_position
encoder_position = 0
target_position = 0

def move_to_angle(degrees):
    global target_position
    global pulses_needed
    #pulses_needed = int(degrees)
    pulses_needed = int((degrees / 360) * ENCODER_RESOLUTION)
    print(encoder_position)
    target_position = encoder_position + pulses_needed
    # Simple P-control (proportional only) [2]
    while abs(encoder_position - target_position) > POSITION_TOLERANCE:
        error = target_position - encoder_position
        speed = SPEED  # Adjust multiplier as needed
        print(encoder_position)
        print(f"Target: {degrees}° ({pulses_needed} pulses)")
        if error > 0:
            MOTOR_M1A_PIN.duty(speed)
            MOTOR_M1B_PIN.duty(0)
        else:
            MOTOR_M1A_PIN.duty(0)
            MOTOR_M1B_PIN.duty(speed)
    
    MOTOR_M1A_PIN.duty(0)
    MOTOR_M1B_PIN.duty(0)
    current_angle = (encoder_position / ENCODER_RESOLUTION) * 360
    print(f"Reached: {current_angle:.1f}°\n")
    read_and_reset_encoder()
    
def move_to_anglelol(degrees):
    global target_position
    global pulses_needed
    #pulses_needed = int(degrees)
    pulses_needed = int((degrees / 360) * ENCODER_RESOLUTION)
    target_position = encoder_position + pulses_needed

    
    # Simple P-control (proportional only) [2]
    while abs(encoder_position - target_position) > POSITION_TOLERANCE:
        error = target_position - encoder_position
        speed = SPEED  # Adjust multiplier as needed
        if error > 0:
            MOTOR_M1B_PIN.duty(speed)
            MOTOR_M1A_PIN.duty(0)
        else:
            MOTOR_M1B_PIN.duty(0)
            MOTOR_M1A_PIN.duty(speed)
    
    MOTOR_M1A_PIN.duty(0)
    MOTOR_M1B_PIN.duty(0)
    print(f"Target: 0° ({pulses_needed} pulses)")
    read_and_reset_encoder()
    
def motor_stop():
    MOTOR_M1A_PIN.duty(0)
    MOTOR_M1B_PIN.duty(0)

def read_and_reset_encoder():
    global encoder_count
    global encoder_position
    irq_state = machine.disable_irq()  # Disable interrupts
    value = encoder_count
    encoder_count = 0
    encoder_position = 0
    machine.enable_irq(irq_state)      # Re-enable interrupts
    return value

# Main loop with user-defined elapsed time and labeled output
last_time = utime.ticks_ms()
last_encoder_time = last_time
state = "forward"

threshold = 10
target_number = int(target_position)

while True:
    current_time = utime.ticks_ms()
    time_difference = utime.ticks_diff(current_time, last_time)
    encoder_timer_difference = utime.ticks_diff(current_time, last_encoder_time)

    now = utime.ticks_ms()
    
    
    if encoder_timer_difference >= ELAPSED_TIME:
    # Calculate speed in encoder counts per second
        counts = read_and_reset_encoder()
#         if abs(counts) > 0:
        speed_cps = counts / (ELAPSED_TIME / 1000)
        speed_rev = speed_cps/ENCODER_RESOLUTION
        last_encoder_time = current_time

    if time_difference >= 10000:  # 2 seconds have passed
        if state == "forward":
            #global number
            number = random.randint(2, 15)
            move_to_angle(number)
            last_time = current_time
            pause_ts = now
            motor_stop()
            publish_time = utime.ticks_ms()
        
        
            while utime.ticks_diff(utime.ticks_ms(), publish_time) < 15000:  # 5s timeout
                host, msg = e.irecv(1000)
                if msg:
                    try:
                        decoded_msg = msg.decode('utf-8').strip()  # Remove whitespace
                        received_number = float(decoded_msg)       # Parse as float first
                        received_number = int(received_number)     # Optional: Convert to integer (truncates)
                        #received_number = int(msg.decode('utf-8'))
                        print("Received angle:", received_number)
                    except Exception as ex:
                        print("Invalid message:", msg, ex)
                if received_number is not None and abs(received_number - number*6) <= threshold:
                    led_13.value(1)
                    led_12.value(0)
                    print(received_number)
                    print(number*6)
                    print("Match confirmed - green LED ON")
                else:
                    print(received_number)
                    print(number*6)
                    led_13.value(0)
                    led_12.value(1)
                    print("Match NOT confirmed - red LED ON")
        
            state = "backward"
        elif state == "backward":
            move_to_anglelol(number)
            last_time = current_time
            motor_stop()
            #utime.sleep(5)  
            state = "forward"






import network, espnow, machine, utime, random, time
from machine import Pin, PWM, Timer
from microdot import Microdot
import _thread

# WiFi credentials
WIFI_SSID = "Berkeley-IoT"
WIFI_PASS = "fG8jb-m*"

# Connect to WiFi
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(WIFI_SSID, WIFI_PASS)

while not sta.isconnected():
    pass

print('Connected. IP:', sta.ifconfig()[0])

e = espnow.ESPNow()
e.active(True)
e.irecv(True)
while not sta.isconnected():
    print("Connecting to WiFi...")
    time.sleep(0.5)
print("WiFi connected!")
sta.disconnect()
sta.config(channel=4)

# ========== Web Server Setup ==========
app = Microdot()
status_html = '''<!DOCTYPE html>
<html>
    <head>
        <title>Motor Control Status</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="2">
    </head>
    <body style="font-family: Arial; text-align: center;">
        <h1>🥁️ Motor Control Status</h1>
        <div style="border: 2px solid {color}; padding: 20px; margin: 20px auto; max-width: 500px;">
            <p style="font-size: 24px; color: {color};">{status}</p>
            <p>🎯 Target Angle: {target}°</p>
            <p>📡 Received Angle: {received}</p>
            <p>⏱ Last Update: {timestamp} seconds ago</p>
        </div>
    </body>
</html>
'''

status_data = {
    'match_confirmed': False,
    'last_update': 0,
    'current_target': 0,
    'received_value': None,
    'status_message': "Initializing..."
}

@app.route('/')
def status(request):
    color = '#4CAF50' if status_data['match_confirmed'] else '#f44336'
    elapsed = (utime.ticks_ms() - status_data['last_update']) // 1000 
    return status_html.format(
        color=color,
        status=status_data['status_message'],
        target=status_data['current_target'],
        received=status_data['received_value'] or "Waiting...",
        timestamp=elapsed
    ), 200, {'Content-Type': 'text/html'}

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
encoder_position = 0

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

# ========== Main Control Loop ==========
def control_loop():
    global received_number, encoder_position, target_position, status_data
    state = "forward"
    number = 0
    last_time = utime.ticks_ms()

    # ESP-NOW setup
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(WIFI_SSID, WIFI_PASS)
    while not sta.isconnected():
        time.sleep(0.1)
    print("WiFi connected:", sta.ifconfig()[0])
    
    e = espnow.ESPNow()
    e.active(True)
    e.irecv(True)  
    
    while True:
        current_time = utime.ticks_ms()
        # Global variables
        encoder_position = 0
        target_position = 0
        received_number = None  # Initialize here
        if state == "forward":
            number = random.randint(2, 15)
            move_to_angle(number)
            motor_stop()
            status_data['current_target'] = number * 6
            status_data['last_update'] = utime.ticks_ms()
            status_data['status_message'] = "🔄 Moving to target position"
            
            timeout_start = utime.ticks_ms()
            while utime.ticks_diff(utime.ticks_ms(), timeout_start) < 15000:
                host, msg = e.irecv(1000)
                if msg:
                    try:
                        decoded = msg.decode('utf-8').strip()
                        received_number = int(float(decoded))
                        status_data['received_value'] = received_number
                        status_data['last_update'] = utime.ticks_ms()
                        
                        if abs(received_number - (number * 6)) <= threshold:
                            status_data['status_message'] = "✅ Match confirmed!"
                            status_data['match_confirmed'] = True
                            led_13.value(1)
                            led_12.value(0)
                            break
                        else:
                            status_data['status_message'] = "❌ Match failed"
                            status_data['match_confirmed'] = False
                            led_13.value(0)
                            led_12.value(1)
                            
                    except Exception as e:
                        print("Decode error:", e)
            
            state = "backward"
            
        elif state == "backward":
            move_to_anglelol(number)
            motor_stop()
            utime.sleep(2)
            state = "forward"
            status_data['status_message'] = "🔙 Returning to start position"
            status_data['last_update'] = utime.ticks_ms()

# ========== Startup ==========
def start_system():
    # Start web server in background
    _thread.start_new_thread(app.run, ('0.0.0.0', 80))
    
    # Start control loop
    control_loop()

start_system()


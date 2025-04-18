import machine
import utime
import random

# User-defined settings
ELAPSED_TIME = 30  # Time interval in milliseconds for calculations and state changes
ENCODER_RESOLUTION = 700 # FOr DFRobot 12V DC motor it is 700. 

# Define motor control pins for the Cytron Maker Drive
MOTOR_M1A_PIN = machine.PWM(machine.Pin(27))
MOTOR_M1B_PIN = machine.PWM(machine.Pin(33))

# Define encoder pins
ENCODER_A_PIN = machine.Pin(25, machine.Pin.IN, machine.Pin.PULL_UP)
ENCODER_B_PIN = machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_UP)

# Motor speed
SPEED = 1023  # Set to maximum speed
POSITION_TOLERANCE = 5  

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
encoder_position = 0
target_position = 0

def move_to_angle(degrees):
    global target_position
    pulses_needed = int((degrees / 360) * ENCODER_RESOLUTION)
    target_position = encoder_position + pulses_needed
    print(f"Target: {degrees}° ({target_position} pulses)")
    
    # Simple P-control (proportional only) [2]
    while abs(encoder_position - target_position) > POSITION_TOLERANCE:
        error = target_position - encoder_position
        speed = SPEED  # Adjust multiplier as needed
        
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
    
def motor_stop():
    MOTOR_M1A_PIN.duty(0)
    MOTOR_M1B_PIN.duty(0)

def read_and_reset_encoder():
    global encoder_count
    irq_state = machine.disable_irq()  # Disable interrupts
    value = encoder_count
    encoder_count = 0
    machine.enable_irq(irq_state)      # Re-enable interrupts
    return value

# Main loop with user-defined elapsed time and labeled output
last_time = utime.ticks_ms()
last_encoder_time = last_time
state = "forward"
while True:
    current_time = utime.ticks_ms()
    time_difference = utime.ticks_diff(current_time, last_time)
    encoder_timer_difference = utime.ticks_diff(current_time, last_encoder_time)

    if encoder_timer_difference >= ELAPSED_TIME:
    # Calculate speed in encoder counts per second
        counts = read_and_reset_encoder()
#         if abs(counts) > 0:
        speed_cps = counts / (ELAPSED_TIME / 1000)
        speed_rev = speed_cps/ENCODER_RESOLUTION
        print(f"Speed: {speed_cps:.2f} counts/second, {speed_rev:.2f} revs/second")
        last_encoder_time = current_time

    if time_difference >= 2000:  # 2 seconds have passed
        if state == "forward":
            move_to_angle(random.randint(0, 359))
            last_time = current_time
            motor_stop()
            time.sleep(5)  
            state = "backward"
        elif state == "backward":
            move_to_angle(0)
            time.sleep(5) 
            state = "stop"
        elif state == "stop":
            state = "forward"


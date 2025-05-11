import network, espnow, machine, utime, random, time  # Import required modules for networking, ESP-NOW, hardware, timing, and randomness
from machine import Pin, PWM, Timer                    # Import Pin, PWM, Timer classes from machine module for hardware control
from microdot import Microdot                          # Import Microdot micro web framework
import _thread                                         # Import threading support

# WiFi credentials
WIFI_SSID = "Berkeley-IoT"                             # Set WiFi SSID
WIFI_PASS = "fG8jb-m*"                                 # Set WiFi password

# Connect to WiFi
sta = network.WLAN(network.STA_IF)                     # Create WLAN object in station mode
sta.active(True)                                       # Activate the WLAN interface
sta.connect(WIFI_SSID, WIFI_PASS)                      # Connect to WiFi using credentials

while not sta.isconnected():                           # Wait until WiFi is connected
    pass

print('Connected. IP:', sta.ifconfig()[0])             # Print the assigned IP address

e = espnow.ESPNow()                                    # Create ESPNow object for ESP-NOW communication
e.active(True)                                         # Activate ESP-NOW
e.irecv(True)                                          # Enable ESP-NOW message reception
while not sta.isconnected():                           # Ensure WiFi is connected before proceeding
    print("Connecting to WiFi...")
    time.sleep(0.5)
print("WiFi connected!")                               # Confirm WiFi connection
sta.disconnect()                                       # Disconnect WiFi (if needed for ESP-NOW)
sta.config(channel=4)                                  # Set WiFi channel to 4

# ========== Web Server Setup ==========
app = Microdot()                                       # Create Microdot web app instance
status_html = '''<!DOCTYPE html>
<html>
    <head>
        <title>Motor Control Status</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="2">
    </head>
    <body style="font-family: Arial; text-align: center;">
        <h1>🥁️ Motor Control Status</h1>...         <div style="border: 2px solid {color}; padding: 20px; margin: 20px auto; max-width: 500px;">
            <p style="font-size: 24px; color: {color};">{status}</p>
            <p>🎯 Target Angle: {target}°</p>
            <p>📡 Received Angle: {received}</p>
            <p>⏱ Last Update: {timestamp} seconds ago</p>
        </div>
    </body>
</html>
'''                                                     # HTML template for status page

status_data = {
    'match_confirmed': False,                           # Indicates if target and received values match
    'last_update': 0,                                   # Timestamp of last update
    'current_target': 0,                                # Current target angle
    'received_value': None,                             # Last received angle value
    'status_message': "Initializing..."                 # Status message for UI
}

@app.route('/')
def status(request):                                    # Define route for status page
    color = '#4CAF50' if status_data['match_confirmed'] else '#f44336'  # Set color based on match status
    elapsed = (utime.ticks_ms() - status_data['last_update']) // 1000   # Calculate seconds since last update
    return status_html.format(
        color=color,
        status=status_data['status_message'],
        target=status_data['current_target'],
        received=status_data['received_value'] or "Waiting...",
        timestamp=elapsed
    ), 200, {'Content-Type': 'text/html'}               # Render HTML with current status

target_number = None                                   # Placeholder for target number
received_number = None                                 # Placeholder for received number

# User-defined settings
ELAPSED_TIME = 30                                      # Time interval (ms) for calculations and state changes
ENCODER_RESOLUTION = 700                               # Encoder pulses per revolution for motor

# Define motor control pins for the Cytron Maker Drive
MOTOR_M1A_PIN = machine.PWM(machine.Pin(27))           # PWM object for motor pin M1A
MOTOR_M1B_PIN = machine.PWM(machine.Pin(33))           # PWM object for motor pin M1B

# Define encoder pins
ENCODER_A_PIN = machine.Pin(25, machine.Pin.IN, machine.Pin.PULL_UP)  # Encoder A input pin
ENCODER_B_PIN = machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_UP)  # Encoder B input pin
led_13 = Pin(13, Pin.OUT)                              # LED on pin 13 as output
led_12 = Pin(12, Pin.OUT)                              # LED on pin 12 as output

# Motor speed
SPEED = 1023                                           # Max PWM duty cycle (speed)
POSITION_TOLERANCE = 1                                 # Allowed error in encoder position

# Encoder counter
encoder_count = 0                                      # Encoder pulse count
encoder_position = 0                                   # Current encoder position

def encoder_handler(pin):                              # Interrupt handler for encoder pins
    global encoder_position
    a = ENCODER_A_PIN.value()                          # Read value from encoder A
    b = ENCODER_B_PIN.value()                          # Read value from encoder B
    
    # Check both edges for better accuracy
    if (a ^ b) if (pin == ENCODER_A_PIN) else (b ^ a): # Determine direction based on pin and values
        encoder_position += 1 if (a ^ b) else -1       # Increment or decrement encoder position

# Attach the interrupt handlers to the encoder pins
ENCODER_A_PIN.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)  # Attach IRQ to A
ENCODER_B_PIN.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=encoder_handler)  # Attach IRQ to B

def move_to_angle(degrees):                            # Move motor to specified angle
    global target_position
    global pulses_needed
    pulses_needed = int((degrees / 360) * ENCODER_RESOLUTION)   # Convert degrees to encoder pulses
    print(encoder_position)
    target_position = encoder_position + pulses_needed           # Set target position
    # Simple P-control (proportional only)
    while abs(encoder_position - target_position) > POSITION_TOLERANCE:  # Loop until within tolerance
        error = target_position - encoder_position               # Calculate error
        speed = SPEED                                           # Set speed (can be adjusted)
        print(encoder_position)
        print(f"Target: {degrees}° ({pulses_needed} pulses)")
        if error > 0:
            MOTOR_M1A_PIN.duty(speed)                           # Move forward
            MOTOR_M1B_PIN.duty(0)
        else:
            MOTOR_M1A_PIN.duty(0)
            MOTOR_M1B_PIN.duty(speed)                           # Move backward
    
    MOTOR_M1A_PIN.duty(0)                                       # Stop motor
    MOTOR_M1B_PIN.duty(0)
    current_angle = (encoder_position / ENCODER_RESOLUTION) * 360  # Calculate current angle
    print(f"Reached: {current_angle:.1f}°\n")
    read_and_reset_encoder()                                    # Reset encoder after movement
    
def move_to_anglelol(degrees):                                 # Move motor back to start position
    global target_position
    global pulses_needed
    #pulses_needed = int(degrees)
    pulses_needed = int((degrees / 360) * ENCODER_RESOLUTION)  # Convert degrees to encoder pulses
    target_position = encoder_position + pulses_needed

    # Simple P-control (proportional only)
    while abs(encoder_position - target_position) > POSITION_TOLERANCE:  # Loop until within tolerance
        error = target_position - encoder_position
        speed = SPEED
        if error > 0:
            MOTOR_M1B_PIN.duty(speed)                          # Move backward
            MOTOR_M1A_PIN.duty(0)
        else:
            MOTOR_M1B_PIN.duty(0)
            MOTOR_M1A_PIN.duty(speed)                          # Move forward
    
    MOTOR_M1A_PIN.duty(0)                                      # Stop motor
    MOTOR_M1B_PIN.duty(0)
    print(f"Target: 0° ({pulses_needed} pulses)")
    read_and_reset_encoder()                                   # Reset encoder after movement
    
def motor_stop():                                              # Stop the motor
    MOTOR_M1A_PIN.duty(0)
    MOTOR_M1B_PIN.duty(0)

def read_and_reset_encoder():                                  # Read and reset encoder counters
    global encoder_count
    global encoder_position
    irq_state = machine.disable_irq()                          # Disable interrupts for atomic operation
    value = encoder_count                                     # Store current count
    encoder_count = 0                                         # Reset encoder count
    encoder_position = 0                                      # Reset encoder position
    machine.enable_irq(irq_state)                             # Re-enable interrupts
    return value

# ========== Main Control Loop ==========
def control_loop():                                           # Main loop for motor and communication logic
    global received_number, encoder_position, target_position, status_data
    state = "forward"                                         # Initial state
    number = 0                                                # Placeholder for random number
    last_time = utime.ticks_ms()                              # Store last time for timing

    # ESP-NOW setup
    sta = network.WLAN(network.STA_IF)                        # Create WLAN object
    sta.active(True)                                          # Activate WLAN
    sta.connect(WIFI_SSID, WIFI_PASS)                         # Connect to WiFi
    while not sta.isconnected():                              # Wait for connection
        time.sleep(0.1)
    print("WiFi connected:", sta.ifconfig()[0])               # Print IP

    e = espnow.ESPNow()                                       # Create ESPNow object
    e.active(True)                                            # Activate ESP-NOW
    e.irecv(True)                                             # Enable ESP-NOW reception  
    
    while True:                                               # Main control loop
        current_time = utime.ticks_ms()                       # Get current time
        # Global variables
        encoder_position = 0                                  # Reset encoder position
        target_position = 0                                   # Reset target position
        received_number = None                                # Reset received number
        if state == "forward":                                # If moving forward
            number = random.randint(2, 15)                    # Pick random number for target
            move_to_angle(number)                             # Move to random angle
            motor_stop()                                      # Stop motor
            status_data['current_target'] = number * 6        # Update status with target angle
            status_data['last_update'] = utime.ticks_ms()     # Update last update time
            status_data['status_message'] = "🔄 Moving to target position"  # Update status message
            
            timeout_start = utime.ticks_ms()                  # Start timeout timer
            while utime.ticks_diff(utime.ticks_ms(), timeout_start) < 15000:  # Wait for up to 15 seconds
                host, msg = e.irecv(1000)                     # Receive ESP-NOW message (timeout 1s)
                if msg:                                       # If message received
                    try:
                        decoded = msg.decode('utf-8').strip() # Decode message
                        received_number = int(float(decoded)) # Convert to integer
                        status_data['received_value'] = received_number  # Update status
                        status_data['last_update'] = utime.ticks_ms()   # Update time
                        if abs(received_number - (number * 6)) <= threshold:  # Check if within threshold
                            status_data['status_message'] = "✅ Match confirmed!"
                            status_data['match_confirmed'] = True
                            led_13.value(1)                   # Turn on success LED
                            led_12.value(0)                   # Turn off failure LED
                            break
                        else:
                            status_data['status_message'] = "❌ Match failed"
                            status_data['match_confirmed'] = False
                            led_13.value(0)                   # Turn off success LED
                            led_12.value(1)                   # Turn on failure LED
                    except Exception as e:
                        print("Decode error:", e)             # Print decode errors
            
            state = "backward"                                # Switch state to backward
            
        elif state == "backward":                             # If moving backward
            move_to_anglelol(number)                          # Move back to start position
            motor_stop()                                      # Stop motor
            utime.sleep(2)                                    # Wait 2 seconds
            state = "forward"                                 # Switch state to forward
            status_data['status_message'] = "🔙 Returning to start position"  # Update status
            status_data['last_update'] = utime.ticks_ms()     # Update time

# ========== Startup ==========
def start_system():                                           # System startup function
    # Start web server in background
    _thread.start_new_thread(app.run, ('0.0.0.0', 80))        # Start web server in new thread
    
    # Start control loop
    control_loop()                                            # Run main control loop

start_system()                                                # Start the system

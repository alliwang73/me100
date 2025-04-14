import network
import espnow
import machine
import time
import random

# Initialize WiFi in Station mode
sta = network.WLAN(network.STA_IF)
sta.active(True)

# Initialize ESP-NOW
esp = espnow.ESPNow()
esp.active(True)

# Add peer (replace with sender's MAC address)
peer = b'xx\x00\x00\x00\x00'  # Example: b'\xaa\xbb\xcc\xdd\xee\xff'
esp.add_peer(peer)

# Servo configuration
servo_pin = machine.Pin(13)
pwm = machine.PWM(servo_pin, freq=50)

def set_angle(angle):
    duty = int(angle / 180 * 1023)  # MicroPython PWM uses 0-1023
    pwm.duty(duty)
    time.sleep(0.5)

while True:
    # Check for ESP-NOW messages
    host, msg = esp.recv(0)  # Non-blocking receive
    if msg:
        if msg == b'activate':
            new_angle = random.randint(0, 180)
            set_angle(new_angle)
            print("Moved to:", new_angle)
        else:
            print("Unknown command")
    time.sleep(30)

import machine
import time
import random
import math
# Servo configuration
SERVO_PIN = 13  # PWM-capable GPIO (e.g., 2,4,5,12-19,21-23,25-27,32-33)
pwm = machine.PWM(machine.Pin(SERVO_PIN))
pwm.freq(50)  # Standard 50Hz frequency for servos

# Duty cycle range (calibrate these for your servo)
MIN_DUTY = 26    # ~500μs pulse (0°)
MAX_DUTY = 128   # ~2500μs pulse (180°)

def set_angle(angle):
    duty = int((angle / 180) * (MAX_DUTY - MIN_DUTY) + MIN_DUTY)
    pwm.duty(duty)
    print(f"Moving to {angle}°")

while True:
    new_angle = random.randint(0, 180)
    set_angle(new_angle)
    time.sleep(30)  # Wait 30 seconds before next move


# Callback means that everytime the timer
# counts one, the corresponding function (in this case tcb)
# will be executed.
t1.init(period=500, mode=t1.PERIODIC, callback=tcb)

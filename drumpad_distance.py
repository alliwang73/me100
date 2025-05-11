#### ---- ME100 FINAL PROJECT - SMART DRUMSTICKS ---- ####

# This file includes the code for the ultrasonic sensor, speaker / metronome,
# and LED lights associated with both sensors.

# Import statements.
import network
import espnow
import time
from hcsr04 import HCSR04
from time import sleep
from machine import Pin
from machine import Pin, PWM, Timer

# Initialize WLAN interface for ESP-NOW.
sta = network.WLAN(network.STA_IF) 
sta.active(True)
sta.disconnect() 
sta.config(channel=4)

# Initialize ESP-NOW.
e = espnow.ESPNow()
e.active(True)
e.irecv(True) 

# Setup LEDs and buzzer/speaker
led_13 = Pin(13, Pin.OUT) # Green LED (drumpad distance) - ultrasonic
led_15 = Pin(15, Pin.OUT) # Red LED (drumpad distance) - ultrasonic
led_12 = Pin(12, Pin.OUT) # Green LED (timing using force data)
led_33 = Pin(33, Pin.OUT) # Yellow LED (timing using force data)
buzzer = PWM(Pin(27))

# Timers
beat_timer = Timer(0)
tone_timer = Timer(1)

# Initialize the HC-SR04 ultrasonic sensor.
sensor = HCSR04(trigger_pin=32, echo_pin=14, echo_timeout_us=10000)

# Declare timing configuration variables (for metronome).
BPM = 120  # change BPM as desired
target_bpm_single_hand = BPM / 2  # BPM for a single hand
target_interval = 60 / target_bpm_single_hand  # [sec] target interval between hits
timing_tolerance = 0.6  # [s] time tolerance between hits (can slightly adjust if needed)
cooldown_ms = 100  # [millisec] cooldown time between hits
metronome_ms = 60000 // BPM  # [ms] period between beeps
tone_duration_ms = 100  # [ms] duration of each beep
print(f"Target interval (one hand): {target_interval:.3f} seconds")

# Declare force threshold variable (for metronome).
HIT_FORCE_THRESHOLD = 0  # used to consider force readings above 0

# Intialize timing states (for metronome).
last_hit_time = None
last_valid_time = 0


#### ---- ULTRASONIC SENSOR CODE START ---- ####
def ultrasonic_sensor():
    dist_cm = sensor.distance_cm()  # Read the distance in cm from the sensor
    dist_inches = dist_cm / 2.54 # Convert distance reading to inches
        
    sleep(0.3)  # Wait for 0.3 second before the next reading

    if dist_inches < 2:
        led_15.value(1) # Turn on Red LED 15 if too left from center
        led_13.value(0)
    elif dist_inches > 7:
        led_15.value(1) # Turn on Red LED 15 if too right from center
        led_13.value(0)
    else:
        led_15.value(0)
        led_13.value(1) # Turn on Green LED 13 if close to center
#### ---- ULTRASONIC SENSOR CODE END ---- ####


#### ----- METRONOME CODE START ----- ####
def stop_beat(timer):
    buzzer.duty(0)

def play_beat(timer):
    buzzer.freq(1200)
    buzzer.duty(512)
    tone_timer.init(mode=Timer.ONE_SHOT,
                    period=tone_duration_ms,
                    callback=stop_beat)
def metronome(timer):
    beat_timer.init(mode=Timer.PERIODIC,
                    period=metronome_ms,
                    callback=play_beat)
#### ----- METRONOME CODE END ----- ####
      
      
print('Waiting for message...')  # print while waiting to receive message

beat_timer.init(mode=Timer.PERIODIC,
                period=metronome_ms,
                callback=play_beat)   # play metronome

while True:
    host, msg = e.irecv(1000) # wait for message w/timeout of 1000ms
    
    if msg:
        reading = int(msg.decode('utf-8')) # decode bytearray and cast to integer
        
        if reading > HIT_FORCE_THRESHOLD:
            current_time = time.ticks_ms() # 0.02 millisec in between readings
            last_hit_time = last_valid_time
        
            # Ignore hits that are too close together (debounce).
            if time.ticks_diff(current_time, last_valid_time) < cooldown_ms:
                continue  # ignore double trigger
 
            # Check if force reading is a valid value.
            if last_hit_time is not None:
                interval_ms = time.ticks_diff(current_time, last_hit_time)
                interval_sec = interval_ms / 1000  # Interval between current time and last time
                                                   # drum was hit.

                # Check if difference between drummer's time interval and
                # target interval is within timing tolerance.
                if abs(interval_sec - target_interval) <= timing_tolerance:
                    print(" On beat")
                    led_12.value(1)  # turn on Green LED if on beat
                    led_33.value(0)
                else:
                    print("Off beat")
                    led_12.value(0)
                    led_33.value(1)  # turn on Red LED if not on beat
                    
                last_valid_time = current_time  # update last_valid_time to current_time
                
        ultrasonic_sensor()  # call ultrasonic sensor function
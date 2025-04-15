import machine
import time

# Define parameters
buzzer_pin = machine.Pin(15)  # Change to the pin you are using
buzzer = machine.PWM(buzzer_pin)
A4_frequency = 440  # Frequency for A4 note in Hz

# Function to play a note for a specified duration
def play_note(frequency, duration):
    buzzer.freq(frequency)
    buzzer.duty(512)  # 50% duty cycle
    time.sleep(duration)
    buzzer.duty(0)    # Stop the sound
    time.sleep(0.1)   # Short pause between notes

# Play the A4 note in a loop for 30 seconds
start_time = time.time()
while time.time() - start_time < 30:
    play_note(A4_frequency, 1)

# After 30 seconds, play C5 for 1 second as a demonstration
play_note(C5_frequency, 1)

# Turn off the buzzer at the end
buzzer.deinit()

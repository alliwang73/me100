from machine import Pin
import utime

# === CONFIGURE THESE ===
ENCODER_A_PIN = 25
ENCODER_B_PIN = 26

# === GLOBALS ===
encoder_position = 0
last_encoded = 0
last_time = utime.ticks_us()

# === SETUP ===
pin_a = Pin(ENCODER_A_PIN, Pin.IN, Pin.PULL_UP)
pin_b = Pin(ENCODER_B_PIN, Pin.IN, Pin.PULL_UP)

def read_encoder():
    a = pin_a.value()
    b = pin_b.value()
    encoded = (a << 1) | b
    return encoded

def encoder_isr(pin):
    global encoder_position, last_encoded, last_time
    now = utime.ticks_us()
    # Simple debounce: ignore changes faster than 1000 us (1 ms)
    if utime.ticks_diff(now, last_time) < 1000:
        return
    last_time = now

    encoded = read_encoder()
    delta = ((last_encoded << 2) | encoded) & 0b1111
    # Gray code state table for quadrature decoding
    if delta in [0b0001, 0b0111, 0b1110, 0b1000]:
        encoder_position += 1
    elif delta in [0b0010, 0b0100, 0b1101, 0b1011]:
        encoder_position -= 1
    last_encoded = encoded

# Initialize last_encoded
last_encoded = read_encoder()

# Attach interrupts
pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=encoder_isr)
pin_b.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=encoder_isr)

print("Rotate the encoder! (CTRL+C to stop)")
try:
    while True:
        print("Encoder Position:", encoder_position)
        utime.sleep_ms(100)
except KeyboardInterrupt:
    print("Test stopped.")


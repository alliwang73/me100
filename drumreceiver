import network
import espnow
import time

# Set up ESP-NOW
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect()

e = espnow.ESPNow()
e.active(True)
e.recv_cb(None)  # Disable callbacks for manual polling

# Add peer if needed (only needed if this device will also send)
# e.add_peer(peer_mac)

# Force thresholds (0–1023 range from analog read)
FORCE_TOO_SOFT = 200  # e.g. 200 → Values below this are too soft
FORCE_TOO_HARD = 600  # e.g. 850 → Values above this are too hard

# Time thresholds in seconds (between valid hits)
TIME_TOO_FAST = 0.3   # e.g. 0.3 → Too fast if interval is less than this
TIME_TOO_SLOW = 1.5   # e.g. 1.5 → Too slow if interval is more than this

# ========== Logic Vars ==========
last_hit_time = None

print("Receiver ready and listening...")

while True:
    host, msg = e.recv()
    if msg:
        try:
            msg = msg.decode()
        except:
            continue  # Skip non-text messages

        if "Force reading:" in msg:
            try:
                reading = int(msg.split(":")[1].strip())
            except ValueError:
                print("Invalid reading received.")
                continue

            print(f"Received force: {reading}")

            if reading > 0:
                # Classify hit strength
                if reading < FORCE_TOO_SOFT:
                    print("Too soft!")
                elif reading > FORCE_TOO_HARD:
                    print("Too hard!")
                else:
                    print("Force OK!")

                # Handle timing between hits
                current_time = time.ticks_ms()

                if last_hit_time is not None:
                    dt = time.ticks_diff(current_time, last_hit_time) / 1000  # in seconds

                    if dt < TIME_TOO_FAST:
                        print("Too fast!")
                    elif dt > TIME_TOO_SLOW:
                        print("Too slow!")
                    else:
                        print("Timing OK!")

                # Update time of last valid hit
                last_hit_time = current_time

import network
import espnow

# Setup ESP-NOW
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect()

e = espnow.ESPNow()
e.active(True)

print("Receiver ready and listening for force readings...")

while True:
    host, msg = e.recv()
    if msg:
        try:
            msg = msg.decode()
            print(f"Received: {msg}")
        except:
            print("Received non-text message.")

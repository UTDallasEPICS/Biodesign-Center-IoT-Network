# receiver.py
# CircuitPython LoRa Ping Receiver
# For: Adafruit Feather RP2040 with RFM95 LoRa Radio - 915MHz
#
# Listens continuously for incoming "PING" packets and replies with "PONG".
# Flash this as code.py on the receiver board.

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# --- Radio Configuration ---
RADIO_FREQ_MHZ = 915.0       # Must match transmitter
RECEIVE_TIMEOUT = 1.0        # Seconds to wait per receive() call (kept short so
                              # the loop stays responsive; does NOT affect how often
                              # you receive — the radio listens in between calls too)

# --- Pin Setup (built-in to this Feather board) ---
CS    = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)

# --- Onboard LED (red, D13) ---
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# --- SPI Bus ---
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# --- Initialize Radio ---
print("Initializing RFM95 radio...")
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm9x.tx_power = 13          # dBm. Range: 5–23. Start low if USB disconnects.
print(f"Radio initialized at {RADIO_FREQ_MHZ} MHz, tx_power={rfm9x.tx_power} dBm")
print("Listening for PING packets...\n")

# --- Main Loop ---
packet_count = 0

while True:
    packet = rfm9x.receive(timeout=RECEIVE_TIMEOUT)

    if packet is not None:
        packet_count += 1
        timestamp = time.monotonic()

        try:
            packet_text = str(packet, "ascii")
        except UnicodeError:
            packet_text = repr(packet)

        rssi = rfm9x.last_rssi
        print(f"[{timestamp:.1f}s] Packet #{packet_count}: '{packet_text}' | RSSI: {rssi} dBm")

        # Flash LED to indicate reception
        led.value = True
        time.sleep(0.05)
        led.value = False

        # Send PONG reply
        reply = f"PONG {packet_count}"
        print(f"  Sending reply: '{reply}'")
        rfm9x.send(bytes(reply, "utf-8"))
        print("  Reply sent.\n")

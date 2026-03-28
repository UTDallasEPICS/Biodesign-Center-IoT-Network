# transmitter.py
# CircuitPython LoRa Ping Transmitter
# For: Adafruit Feather RP2040 with RFM95 LoRa Radio - 915MHz
#
# Sends a "PING" packet every 30 seconds and listens briefly for a "PONG" reply.
# Flash this as code.py on the transmitter board.

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# --- Radio Configuration ---
RADIO_FREQ_MHZ = 915.0       # Must match receiver
PING_INTERVAL  = 30          # Seconds between pings
PONG_TIMEOUT   = 5.0         # How long to wait for a pong reply (seconds)

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
print(f"Sending PING every {PING_INTERVAL} seconds...\n")

# --- Main Loop ---
ping_count = 0

while True:
    ping_count += 1
    timestamp = time.monotonic()
    message = f"PING {ping_count}"

    print(f"[{timestamp:.1f}s] Sending: {message}")
    led.value = True
    rfm9x.send(bytes(message, "utf-8"))
    led.value = False

    # Listen briefly for a PONG reply
    print(f"  Waiting up to {PONG_TIMEOUT}s for PONG...")
    reply = rfm9x.receive(timeout=PONG_TIMEOUT)

    if reply is not None:
        try:
            reply_text = str(reply, "ascii")
        except UnicodeError:
            reply_text = repr(reply)
        rssi = rfm9x.last_rssi
        print(f"  Got reply: '{reply_text}' | RSSI: {rssi} dBm")
        # Flash LED twice on successful round-trip
        for _ in range(2):
            led.value = True
            time.sleep(0.1)
            led.value = False
            time.sleep(0.1)
    else:
        print("  No reply received.")

    # Wait out the remainder of the 30-second interval
    elapsed = time.monotonic() - timestamp
    sleep_time = max(0, PING_INTERVAL - elapsed)
    print(f"  Sleeping {sleep_time:.1f}s until next ping.\n")
    time.sleep(sleep_time)

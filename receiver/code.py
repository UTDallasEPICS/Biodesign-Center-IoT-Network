# code.py — Receiver main loop
# Biodesign Center IoT Network
# Hardware: Adafruit Feather RP2040 + RFM95 LoRa 915 MHz (CircuitPython)
#
# Receives LoRa packets and prints raw hex strings per packet to USB serial.
# Each line is a space-separated hex string ready for decode_lora().

import time
import board
import busio
import digitalio
import adafruit_rfm9x

from config import RADIO_FREQ_MHZ, RECEIVE_TIMEOUT

# ---------------------------------------------------------------------------
# Hardware init
# ---------------------------------------------------------------------------

CS    = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)
led   = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
spi   = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

print("Initializing RFM95...")
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm9x.enable_crc = True
print("Receiver ready  freq={} MHz".format(RADIO_FREQ_MHZ))
print("-" * 72)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

while True:
    raw = rfm9x.receive(timeout=RECEIVE_TIMEOUT)
    if raw is None:
        continue

    led.value = True

    # Convert raw bytes to space-separated hex string
    hex_str = " ".join("{:02X}".format(b) for b in raw)
    print(hex_str)

    led.value = False

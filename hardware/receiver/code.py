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
import microcontroller
import adafruit_rfm9x
from watchdog import WatchDogMode

from config import RADIO_FREQ_MHZ, RECEIVE_TIMEOUT, RECEIVER_NODE

ALIVE_INTERVAL = 10.0
WATCHDOG_TIMEOUT = 8.0  # RP2040 hardware max is ~8.3s

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
rfm9x.node = RECEIVER_NODE
print("Receiver ready  freq={} MHz  node={:#04x}  ACK=on".format(RADIO_FREQ_MHZ, RECEIVER_NODE))
print("-" * 72)

# Hardware watchdog. Primary recovery mechanism: if any operation below
# (rfm9x.receive, print, etc.) blocks past WATCHDOG_TIMEOUT, the chip resets.
# The try/except below only catches Python-level exceptions and is the
# secondary path for catchable faults.
wdt = microcontroller.watchdog
wdt.timeout = WATCHDOG_TIMEOUT
wdt.mode = WatchDogMode.RESET
wdt.feed()

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

last_print = time.monotonic()

try:
    while True:
        wdt.feed()
        raw = rfm9x.receive(timeout=RECEIVE_TIMEOUT, with_ack=True)

        if raw is None:
            now = time.monotonic()
            if now - last_print >= ALIVE_INTERVAL:
                print("# alive")
                last_print = now
            continue

        led.value = True
        hex_str = " ".join("{:02X}".format(b) for b in raw)
        print(hex_str)
        last_print = time.monotonic()
        led.value = False

except Exception as e:
    # Catchable Python-level fault (SPI/radio/USB CDC raising an error).
    # Self-reset so the receiver recovers without manual intervention.
    # Non-catchable hangs (blocked print, infinite SPI wait) are handled
    # by the hardware watchdog, not this branch.
    wdt.feed()
    print("# RECEIVER FAULT: {}".format(e))
    time.sleep(1)
    microcontroller.reset()

# code.py — Transmitter main loop (generic)
# Biodesign Center IoT Network
# Hardware: Adafruit Feather RP2040 + RFM95 LoRa 915 MHz (CircuitPython)
#
# Behavior:
#   - Polls sensors every POLL_INTERVAL seconds.
#   - Sends a DATA packet immediately when an edge-type channel changes state.
#   - Sends a DATA packet with current readings if no event has fired within HEARTBEAT_INTERVAL seconds.
#
# This file is shared across all transmitter types. Sensor-specific behavior
# comes from READERS and TRIGGER_TYPE in each transmitter's sensors.py.

import time
import board
import busio
import digitalio
import adafruit_rfm9x

from config import LAB_ID, NODE_ID, RADIO_FREQ_MHZ, TX_POWER, HEARTBEAT_INTERVAL, POLL_INTERVAL, SENSORS
from packet import encode_packet, MSG_DATA
from sensors import READERS, TRIGGER_TYPE

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
rfm9x.tx_power = TX_POWER
rfm9x.enable_crc = True
print("Radio ready  freq={} MHz  lab={:#04x}  node={:#04x}  tx_power={} dBm".format(
    RADIO_FREQ_MHZ, LAB_ID, NODE_ID, TX_POWER
))
for s in SENSORS:
    print("  channel={}  threshold={}".format(s["channel"], s.get("threshold", "n/a")))

# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------
# last_sent  : monotonic time of last transmission (0 = never)
# last_value : dict of channel_name -> previous value, or None before first read

state = {
    "last_sent": 0.0,
    "last_value": {s["channel"]: None for s in SENSORS},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send(pkt):
    led.value = True
    rfm9x.send(bytes(pkt))
    led.value = False

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

while True:
    now = time.monotonic()
    readings = []
    trigger_reasons = []

    for sensor in SENSORS:
        ch = sensor["channel"]

        if ch not in READERS:
            print("WARNING: channel '{}' not found in READERS — skipping".format(ch))
            continue

        ch_val = READERS[ch]()
        readings.append((ch, ch_val))

        prev  = state["last_value"][ch]
        ttype = TRIGGER_TYPE.get(ch)

        if ttype == "edge":
            if prev is not None and ch_val != prev:
                trigger_reasons.append("{} -> {}".format(ch, ch_val))
        elif ttype is not None:
            print("WARNING: unknown trigger type '{}' for channel '{}'".format(ttype, ch))

        state["last_value"][ch] = ch_val

    # --- Send data packet if any trigger fired ---
    if trigger_reasons:
        reason_str = ", ".join(trigger_reasons)
        print("[{:.1f}s] EVENT  node={:#04x}  {}".format(now, NODE_ID, reason_str))
        pkt = encode_packet(LAB_ID, NODE_ID, MSG_DATA, readings)
        _send(pkt)
        state["last_sent"] = now

    # --- Periodic send: no event fired within the interval ---
    elif now - state["last_sent"] >= HEARTBEAT_INTERVAL:
        print("[{:.1f}s] PERIODIC  node={:#04x}".format(now, NODE_ID))
        pkt = encode_packet(LAB_ID, NODE_ID, MSG_DATA, readings)
        _send(pkt)
        state["last_sent"] = now

    time.sleep(POLL_INTERVAL)

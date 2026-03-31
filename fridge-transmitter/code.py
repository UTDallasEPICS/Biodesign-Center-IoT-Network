# code.py — Transmitter main loop
# Biodesign Center IoT Network
# Hardware: Adafruit Feather RP2040 + RFM95 LoRa 915 MHz (CircuitPython)
#
# Behavior:
#   - Polls sensors every POLL_INTERVAL seconds.
#   - Sends a DATA packet immediately on:
#       * door state change (any transition)
#       * temperature crossing the configured threshold (either direction)
#   - Sends a HEARTBEAT packet if no event has been sent in HEARTBEAT_INTERVAL seconds.
#   - Each sensor defined in config.py is tracked independently.

import time
import board
import busio
import digitalio
import adafruit_rfm9x

from config import LAB_ID, RADIO_FREQ_MHZ, TX_POWER, HEARTBEAT_INTERVAL, POLL_INTERVAL, SENSORS
from packet import encode_packet, MSG_DATA, MSG_HEARTBEAT
from sensors import read_temperature, read_door

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
print("Radio ready  freq={} MHz  lab={:#04x}  tx_power={} dBm".format(
    RADIO_FREQ_MHZ, LAB_ID, TX_POWER
))
for s in SENSORS:
    print("  node={:#04x}  channels={}  thresholds={}".format(
        s["node_id"], s["channels"], s.get("thresholds", {})
    ))

# ---------------------------------------------------------------------------
# Per-sensor state tracking
# ---------------------------------------------------------------------------
# last_sent   : monotonic time of last transmission (0 = never)
# last_door   : previous door bool, or None before first read
# last_temp   : previous temperature float, or None before first read

sensor_states = {}
for _s in SENSORS:
    sensor_states[_s["node_id"]] = {
        "last_sent": 0.0,
        "last_door": None,
        "last_temp": None,
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send(pkt):
    led.value = True
    rfm9x.send(bytes(pkt))
    led.value = False


def _read_channels(sensor_def):
    """Return list of (channel_name, value) for all channels in this sensor def."""
    readings = []
    for ch in sensor_def["channels"]:
        if ch == "temperature":
            readings.append(("temperature", read_temperature()))
        elif ch == "door":
            readings.append(("door", read_door()))
    return readings

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

while True:
    now = time.monotonic()

    for sensor_def in SENSORS:
        sid        = sensor_def["node_id"]
        state      = sensor_states[sid]
        thresholds = sensor_def.get("thresholds", {})
        readings   = _read_channels(sensor_def)

        trigger_reasons = []

        # --- Edge detection: door state change ---
        for ch_name, ch_val in readings:
            if ch_name == "door":
                prev = state["last_door"]
                if prev is not None and ch_val != prev:
                    trigger_reasons.append(
                        "door -> {}".format("open" if ch_val else "closed")
                    )
                state["last_door"] = ch_val

        # --- Threshold crossing: temperature ---
        for ch_name, ch_val in readings:
            if ch_name == "temperature":
                prev   = state["last_temp"]
                thresh = thresholds.get("temperature")
                if thresh is not None and prev is not None:
                    crossed = (prev < thresh <= ch_val) or (prev > thresh >= ch_val)
                    if crossed:
                        trigger_reasons.append(
                            "temp {:.2f}C crossed {:.2f}C".format(ch_val, thresh)
                        )
                state["last_temp"] = ch_val

        # --- Send data packet if any trigger fired ---
        if trigger_reasons:
            reason_str = ", ".join(trigger_reasons)
            print("[{:.1f}s] EVENT  sensor={:#04x}  {}".format(now, sid, reason_str))
            pkt = encode_packet(LAB_ID, sid, MSG_DATA, readings)
            _send(pkt)
            state["last_sent"] = now

        # --- Heartbeat: nothing sent within the interval ---
        elif now - state["last_sent"] >= HEARTBEAT_INTERVAL:
            print("[{:.1f}s] HEARTBEAT  sensor={:#04x}".format(now, sid))
            pkt = encode_packet(LAB_ID, sid, MSG_HEARTBEAT)
            _send(pkt)
            state["last_sent"] = now

    time.sleep(POLL_INTERVAL)

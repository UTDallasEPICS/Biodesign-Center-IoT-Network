# code.py — Receiver main loop
# Biodesign Center IoT Network
# Hardware: Adafruit Feather RP2040 + RFM95 LoRa 915 MHz (CircuitPython)
#
# Receives LoRa packets, decodes them, and prints one formatted line per packet
# to USB serial. Readable via: screen /dev/ttyACM0
#
# Output columns:
#   [timestamp]  MSG_TYPE  lab=NN node=NN  <channel readings>  RSSI=NdBm

import time
import board
import busio
import digitalio
import adafruit_rfm9x

from config import RADIO_FREQ_MHZ, RECEIVE_TIMEOUT
from packet import decode_packet, MSG_DATA, MSG_HEARTBEAT, MSG_ERROR

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
# Formatting helpers
# ---------------------------------------------------------------------------

_MSG_LABELS = {
    MSG_DATA:      "DATA     ",
    MSG_HEARTBEAT: "HEARTBEAT",
    MSG_ERROR:     "ERROR    ",
}


def _fmt_channel(name, value):
    if name == "temperature":
        return "temp={:+.2f}C".format(value)
    elif name == "door":
        return "door={}".format("open" if value else "closed")
    elif name == "light_level":
        return "light={}".format(value)
    elif name == "light_event":
        return "light_event={}".format("ring" if value else "none")
    elif name == "current_draw":
        return "current={}".format("on" if value else "off")
    elif name == "current_amps":
        return "current={}mA".format(value)
    else:
        return "{}={}".format(name, value)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

while True:
    raw = rfm9x.receive(timeout=RECEIVE_TIMEOUT)
    if raw is None:
        continue

    ts   = time.monotonic()
    rssi = rfm9x.last_rssi
    led.value = True

    try:
        pkt       = decode_packet(raw)
        label     = _MSG_LABELS.get(pkt["msg_type"], "UNKNOWN({:#04x})".format(pkt["msg_type"]))
        ch_parts  = [_fmt_channel(n, v) for n, v in pkt["channels"]]
        ch_str    = "  ".join(ch_parts) if ch_parts else "(no channels)"

        print("[{:8.1f}s] {}  lab={:02d} node={:02d}  {:<36s}  RSSI={:+d}dBm".format(
            ts,
            label,
            pkt["lab_id"],
            pkt["node_id"],
            ch_str,
            rssi,
        ))

    except ValueError as err:
        raw_hex = "".join("{:02x}".format(b) for b in raw)
        print("[{:8.1f}s] MALFORMED  raw={}  err={}  RSSI={:+d}dBm".format(
            ts, raw_hex, err, rssi
        ))

    led.value = False

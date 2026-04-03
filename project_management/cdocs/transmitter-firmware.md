# Transmitter Firmware Context: Biodesign Center IoT Network

CircuitPython on Adafruit Feather RP2040 + RFM95 LoRa 915 MHz. Files: `code.py`, `config.py`, `packet.py`, `sensors.py`.

---

## Event Logic (`code.py`)

The main loop runs every `POLL_INTERVAL` seconds. Per sensor in `SENSORS`:

1. Read the channel via `READERS[sensor["channel"]]()`.
2. **Edge-type** (e.g. door): trigger if value differs from previous.
3. **Threshold-type** (e.g. temperature): trigger if `prev < thresh <= current` or `prev > thresh >= current`.
4. If any trigger fired, send a DATA packet with all channel readings; update `last_sent`.
5. If no trigger has fired within `HEARTBEAT_INTERVAL` seconds since `last_sent`, send a HEARTBEAT.

A single `state` dict tracks the whole node: `last_sent` (monotonic time) and `last_value` (dict of channel → previous value, `None` before first read). No edge/threshold triggers fire on the first poll.

---

## Hardware (`code.py`)

Radio CS/RST: `board.RFM_CS`, `board.RFM_RST`. SPI: `board.SCK/MOSI/MISO`. LED: `board.LED` (blinks on transmit). `rfm9x.enable_crc = True`. TX power set from config.

`_send(pkt)`: sets LED True, calls `rfm9x.send(bytes(pkt))`, sets LED False.

---

## Sensors (`sensors.py`)

`read_temperature()` → `float` (°C). TMP36 on `board.A0`: `voltage = (raw * 3.3) / 65536`, then `(voltage - 0.5) * 100`.

`read_door()` → `bool` (True = open). Button on `board.D12` with `Pull.UP`. `True` when released (open), `False` when pressed (closed).

To adapt to different hardware: replace the function bodies. Signatures and return types must not change.

---

## Configuration (`config.py`)

Edit before flashing each board. No other files need to change between nodes.

| Field | Purpose |
|-------|---------|
| `LAB_ID` | Lab identifier (1–255, 0 reserved) |
| `NODE_ID` | Unique ID for this transmitter board (1–255). Edit before flashing each board |
| `RADIO_FREQ_MHZ` | Must match receiver (915.0) |
| `TX_POWER` | dBm (5–23). Keep low if USB disconnects during TX |
| `HEARTBEAT_INTERVAL` | Max seconds of silence before heartbeat (default 30) |
| `POLL_INTERVAL` | Seconds between sensor reads (default 1) |
| `SENSORS` | List of sensor defs: one entry per physical sensor on this board |

Each entry in `SENSORS`:
- `channel`: str — currently `"temperature"` and `"door"` are implemented
- `threshold`: float (optional) — threshold-crossing value for threshold-type channels

---

## Packet Protocol

Uses `encode_packet` and `encode_channel` from `packet.py`. See `cdocs/packet-protocol.md`.

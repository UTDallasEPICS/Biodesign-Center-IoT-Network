# Transmitter Firmware Context: Biodesign Center IoT Network

CircuitPython on Adafruit Feather RP2040 + RFM95 LoRa 915 MHz. Files: `code.py`, `config.py`, `packet.py`, `sensors.py`.

---

## Event Logic (`code.py`)

The main loop runs every `POLL_INTERVAL` seconds. Per sensor in `SENSORS`:

1. Read the channel via `READERS[sensor["channel"]]()`.
2. **Edge-type** (e.g. door): trigger if value differs from previous. No trigger fires on the first poll.
3. If any trigger fired, send a DATA packet with all channel readings; update `last_sent`.
4. If no trigger has fired within `HEARTBEAT_INTERVAL` seconds since `last_sent`, send a periodic DATA packet with current readings. This provides a continuous sensor log to the host.

Only `"edge"` is a supported trigger type. Threshold detection is not performed in firmware — it belongs exclusively in Grafana, which has the full time series.

A single `state` dict tracks the whole node: `last_sent` (monotonic time) and `last_value` (dict of channel → previous value, `None` before first read).

---

## Hardware (`code.py`)

Radio CS/RST: `board.RFM_CS`, `board.RFM_RST`. SPI: `board.SCK/MOSI/MISO`. LED: `board.LED` (blinks on transmit). `rfm9x.enable_crc = True`. TX power set from config. Addressed mode enabled: `rfm9x.node = NODE_ID`, `rfm9x.destination = RECEIVER_NODE`. ACK configured via `rfm9x.ack_retries` and `rfm9x.ack_wait`.

`_send(pkt)`: waits a random jitter (0 to `CSMA_DELAY_MAX` seconds) to reduce collision probability, sets LED True, calls `rfm9x.send_with_ack(bytes(pkt))`, sets LED False. Logs whether ACK was received or all retries were exhausted.

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
| `RECEIVER_NODE` | Radio address of the receiver node (default 0x01). Must match receiver config |
| `ACK_RETRIES` | Max retry attempts if no ACK received (default 3) |
| `ACK_WAIT` | Seconds to wait for ACK per attempt (default 0.5) |
| `CSMA_DELAY_MAX` | Max random jitter in seconds before first transmit (default 0.1) |
| `SENSORS` | List of sensor defs: one entry per physical sensor on this board |

Each entry in `SENSORS`:
- `channel`: str — currently `"temperature"` and `"door"` are implemented

---

## Packet Protocol

Uses `encode_packet` and `encode_channel` from `packet.py`. See `cdocs/packet-protocol.md`.

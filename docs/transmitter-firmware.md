# Transmitter Firmware

## Overview

CircuitPython firmware for Adafruit Feather RP2040 + RFM95 LoRa (915 MHz). Reads sensors, detects events, and sends LoRa packets.

## Files (flashed to board)

- `code.py` — Main loop. Initializes radio, polls sensors, applies event logic, transmits packets.
- `config.py` — Per-node configuration. Edit before flashing each board.
- `packet.py` — Packet encoder. Shared protocol implementation.
- `sensors.py` — Hardware read functions for TMP36 (analog, pin A0) and door button (digital, pin D12 with pull-up).

## Event Logic

The main loop runs every `POLL_INTERVAL` seconds (default 1s). For each sensor defined in `SENSORS`:

1. Read all configured channels.
2. **Door edge detection**: if door state differs from previous read, trigger.
3. **Temperature threshold crossing**: if temperature crossed the configured threshold since last read, trigger.
4. If any trigger fired, send a DATA packet with all channel readings.
5. If no trigger has fired within `HEARTBEAT_INTERVAL` (default 30s), send a HEARTBEAT.

Each sensor tracks its own `last_sent` timer, `last_door`, and `last_temp` independently.

## Configuration (`config.py`)

| Field                  | Purpose                                        |
|------------------------|-------------------------------------------------|
| `LAB_ID`               | Lab identifier (1–255)                          |
| `RADIO_FREQ_MHZ`       | Must match receiver (915.0)                     |
| `TX_POWER`             | Transmit power in dBm (5–23)                    |
| `HEARTBEAT_INTERVAL`   | Max seconds of silence before heartbeat         |
| `POLL_INTERVAL`        | Seconds between sensor reads                    |
| `SENSORS`              | List of sensor defs: node_id, channels, thresholds |

## Hardware Pins

- SPI: `board.SCK`, `board.MOSI`, `board.MISO` (radio)
- Radio CS/RST: `board.RFM_CS`, `board.RFM_RST`
- TMP36: `board.A0` (analog)
- Door button: `board.D12` (digital input, pull-up; pressed=closed)
- LED: `board.LED` (blinks on transmit)

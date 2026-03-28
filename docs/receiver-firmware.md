# Receiver Firmware

## Overview

CircuitPython firmware for the gateway Feather RP2040 + RFM95. Listens for LoRa packets and outputs raw hex to USB serial for the host PC to parse.

## Files (flashed to board)

- `code.py` — Main loop. Initializes radio, listens continuously, prints hex lines.
- `config.py` — Radio frequency and receive timeout.
- `packet.py` — Shared protocol implementation (present for potential future on-device decoding; not currently imported by `code.py`).

## Behavior

1. Initialize RFM95 at 915 MHz with CRC enabled.
2. Call `rfm9x.receive(timeout=1.0)` in a loop.
3. On packet receipt, convert raw bytes to space-separated uppercase hex (e.g., `01 01 01 01 02 01 00 01 C5 02 00 00 00`) and print to USB serial.
4. Blink LED on each received packet.

The receiver does no decoding, filtering, or acknowledgment. It is a transparent bridge from LoRa to USB serial.

## Configuration (`config.py`)

| Field             | Purpose                                      |
|-------------------|----------------------------------------------|
| `RADIO_FREQ_MHZ`  | Must match transmitters (915.0)              |
| `RECEIVE_TIMEOUT`  | Seconds per `receive()` call (default 1.0)  |

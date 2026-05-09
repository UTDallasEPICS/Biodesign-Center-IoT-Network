# Receiver Firmware Context: Biodesign Center IoT Network

CircuitPython on Adafruit Feather RP2040 + RFM95 LoRa 915 MHz. Files: `code.py`, `config.py`, `packet.py`. The receiver is a transparent bridge — it does no decoding or filtering. It sends hardware-level ACKs via the rfm9x library so transmitters know the packet was received.

---

## Behavior (`code.py`)

1. Initialize RFM95 at `RADIO_FREQ_MHZ` with `enable_crc = True`. Set `rfm9x.node = RECEIVER_NODE` for addressed mode.
2. Call `rfm9x.receive(timeout=RECEIVE_TIMEOUT, with_ack=True)` in a loop. The library automatically sends an ACK back to the transmitter.
3. On packet receipt, convert raw bytes to space-separated uppercase hex and print to USB serial.
4. Blink LED on each received packet.
5. On `None` (timeout), continue. If no line has been printed for `ALIVE_INTERVAL` seconds (default 10), print `"# alive"` so the host can distinguish "idle but healthy" from "receiver hung."
6. The main loop is wrapped in `try/except`. On any unhandled exception, the receiver prints `"# RECEIVER FAULT: <error>"` and calls `microcontroller.reset()` to recover without manual intervention.

Output format per packet: `"01 01 01 01 02 01 00 01 C5 02 00 00 00\r\n"` (uppercase, space-separated, newline-terminated). Lines beginning with `#` are out-of-band status (heartbeat, fault), not packet data.

---

## Hardware

Same board as transmitter (Feather RP2040 + RFM95). CS/RST/SPI pins identical. No TX power config needed.

---

## Configuration (`config.py`)

| Field | Purpose |
|-------|---------|
| `RADIO_FREQ_MHZ` | Must match all transmitters (915.0) |
| `RECEIVE_TIMEOUT` | Seconds per `receive()` call (default 1.0). Kept short for loop responsiveness; does not affect packet reception rate |
| `RECEIVER_NODE` | Radio address of this receiver (default 0x01). Must match transmitter configs |

---

## `packet.py`

The receiver uses `hardware/shared/packet.py` (the single canonical copy). Not currently imported by `code.py`. Present for potential future on-device decoding. See `cdocs/packet-protocol.md`.

# Architecture Conventions: Biodesign Center IoT Network

---

## System Layers

Data flows strictly left to right. No layer communicates backward.

```
[Sensors]  →nto1  [Transmitter Node]  →  [LoRa 915 MHz, nto1]  →  [Receiver Node]  →  [USB Serial, 1to1]  →  [Host App]  →nto1  [Grafana Cloud]
```

| Layer | Code | Responsibility |
|-------|------|----------------|
| Sensor read | `hardware/<type>-transmitter/sensors.py` | Hardware abstraction only. Returns typed values; no protocol awareness. Exports `READERS` and `TRIGGER_TYPE` dicts |
| Event logic | `hardware/shared/code.py` | Generic main loop. Dispatches triggers via `TRIGGER_TYPE`; builds channel lists; calls encoder |
| Packet encoding | `hardware/shared/packet.py` | Protocol v1 encoding. No hardware or event logic |
| Radio TX | `hardware/shared/code.py` (`_send`) | Wraps `rfm9x.send`; no encoding logic |
| Radio RX | `hardware/receiver/code.py` | Transparent bridge. No decoding, no filtering |
| Serial output | `hardware/receiver/code.py` | Prints raw hex lines. No interpretation |
| Decoding | `windows-exe/hex_parse.py` | Parses hex to structured dict. No I/O |
| Grafana push | `windows-exe/grafana.py` | Formats and posts metrics. No decoding logic |
| Serial I/O | `windows-exe/serial_reader.py` | Port discovery and serial read loop. Puts decoded packets onto a queue. No Grafana logic |
| Orchestration | `windows-exe/app.py` | Tabbed GUI, thread lifecycle, packet consumer, receiver pairing. Owns `node_last_seen`, `discovered_nodes`, `listened_nodes`, and `packet_queue`. No I/O logic |

---

## Module Responsibilities

**`sensors.py`** — hardware reads only. Each transmitter type has its own `sensors.py` exporting `READERS` (channel name → read function) and `TRIGGER_TYPE` (channel name → "edge" or "threshold").

**`packet.py`** — protocol implementation. No CircuitPython hardware imports. Single canonical copy in `hardware/shared/`.

**`hex_parse.py`** — decoding only. No network I/O, no GUI, no serial. Called from `serial_reader.py` as a pure function.

**`grafana.py`** — Grafana Cloud I/O only. Formats and posts metrics and status. No serial, no GUI, no decoding logic.

**`serial_reader.py`** — serial I/O only. Discovers COM ports and reads the receiver. Decodes packets via `decode_lora()` and puts results onto a `queue.Queue`. No Grafana imports.

**`app.py`** — orchestration only. Owns `node_last_seen`, `discovered_nodes`, `listened_nodes`, and `packet_queue`. Manages thread lifecycle (reader, consumer, status). `consume_packets` drains the queue, tracks discovered transmitters, and calls `grafana_push` only for listened transmitters. Tabbed UI: `DataStreamTab` (log view), `ReceiverPairingTab` (transmitter discovery and listen toggles). No inline I/O logic.

---

## Forbidden Patterns

**F3 — `config.py` must be assignment-only.**
No functions, classes, imports, or logic in either `config.py`. Values must be literals or simple arithmetic.

**F4 — `packet.py` is a single shared file.**
`hardware/shared/packet.py` is the only copy. All transmitters and the receiver use it.

**F5 — Alert thresholds belong only in Grafana. Sensor calibration thresholds belong only in `sensors.py`.**
Two distinct threshold concepts must not be confused:
- **Sensor calibration threshold**: converts a raw analog reading to a bool (e.g. ADC > 1200 → "light is on"). This is hardware-specific and belongs in `sensors.py` as a constant. The main loop never sees it — `read_*()` returns the already-digitized bool.
- **Alert threshold**: a value at which someone should be notified (e.g. temperature ≥ 10 °C). This belongs exclusively in Grafana. Firmware must not make send decisions based on alert thresholds.

Sensor calibration thresholds enable edge detection on analog sensors (same pattern as digital door sensor). Alert thresholds are analysis and belong downstream.

**F6 — All transmissions use `MSG_DATA` with channel readings.**
There is no dedicated heartbeat or keep-alive message type. Periodic sends (when no event has fired) use `MSG_DATA` with current readings, ensuring a continuous sensor time series reaches Grafana.

---

## Adding a New Channel Type

1. Add a constant `CH_<NAME> = 0xNN` to `hardware/shared/packet.py`.
2. Add to `_CHANNEL_NAMES` and `_CHANNEL_CODES` dicts in `hardware/shared/packet.py`.
3. Add encode branch in `encode_channel()`.
4. Add decode branch in `decode_packet()`.
5. Add decode branch in `hex_parse.py` (`decode_lora`).
6. Add a read function in the relevant `sensors.py` and update its `READERS` and `TRIGGER_TYPE` dicts.
7. Update `cdocs/packet-protocol.md` channel table.

---

## Adding a New Transmitter Node

Only `config.py` needs to change (new `LAB_ID`, `SENSORS` entry). No code changes.

---

## Adding a New Transmitter Type

Create a new `hardware/<name>-transmitter/` directory with:
1. `sensors.py` — read functions, `READERS` dict, and `TRIGGER_TYPE` dict.
2. `config.py` — per-node configuration (same structure as existing).

No shared files need to change. `flash.sh` auto-discovers the new directory.

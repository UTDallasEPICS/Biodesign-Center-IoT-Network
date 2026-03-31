# Architecture Conventions: Biodesign Center IoT Network

---

## System Layers

Data flows strictly left to right. No layer communicates backward.

```
[Sensors]  →  [Transmitter Node]  →  [LoRa 915 MHz]  →  [Receiver Node]  →  [USB Serial]  →  [Host App]  →  [Grafana Cloud]
```

| Layer | Code | Responsibility |
|-------|------|----------------|
| Sensor read | `transmitter/sensors.py` | Hardware abstraction only. Returns typed values; no protocol awareness |
| Event logic | `transmitter/code.py` | Decides when to send; builds channel lists; calls encoder |
| Packet encoding | `transmitter/packet.py` | Protocol v1 encoding. No hardware or event logic |
| Radio TX | `transmitter/code.py` (`_send`) | Wraps `rfm9x.send`; no encoding logic |
| Radio RX | `receiver/code.py` | Transparent bridge. No decoding, no filtering |
| Serial output | `receiver/code.py` | Prints raw hex lines. No interpretation |
| Decoding | `windows-exe/hex_parse.py` | Parses hex to structured dict. No I/O |
| Grafana push | `windows-exe/app.py` | Formats and posts metrics. No decoding logic |

---

## Module Responsibilities

**`sensors.py`** — hardware reads only. Swap function bodies to change hardware; never change signatures (`read_temperature() → float`, `read_door() → bool`).

**`packet.py`** — protocol implementation. No CircuitPython hardware imports. Must work identically in transmitter and receiver contexts.

**`hex_parse.py`** — decoding only. No network I/O, no GUI, no serial. Called from `app.py` as a pure function.

**`app.py`** — orchestration: GUI, serial thread, status thread, Grafana push. No decoding logic inline — delegates to `decode_lora()`.

---

## Forbidden Patterns

**F3 — `config.py` must be assignment-only.**
No functions, classes, imports, or logic in either `config.py`. Values must be literals or simple arithmetic.

**F4 — `packet.py` must be identical in both directories.**
Any protocol change requires updating both copies simultaneously.

---

## Adding a New Channel Type

1. Add a constant `CH_<NAME> = 0xNN` to `packet.py` (both copies).
2. Add to `_CHANNEL_NAMES` and `_CHANNEL_CODES` dicts in `packet.py` (both copies).
3. Add encode branch in `encode_channel()`.
4. Add decode branch in `decode_packet()`.
5. Add decode branch in `hex_parse.py` (`decode_lora`).
6. Add a read function in `sensors.py` if new hardware is needed.
7. Update `cdocs/packet-protocol.md` channel table.

---

## Adding a New Transmitter Node

Only `config.py` needs to change (new `LAB_ID`, `SENSORS` entry). No code changes.

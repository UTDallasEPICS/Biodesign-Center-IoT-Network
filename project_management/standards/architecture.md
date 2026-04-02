# Architecture Conventions: Biodesign Center IoT Network

---

## System Layers

Data flows strictly left to right. No layer communicates backward.

```
[Sensors]  →  [Transmitter Node]  →  [LoRa 915 MHz]  →  [Receiver Node]  →  [USB Serial]  →  [Host App]  →  [Grafana Cloud]
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
| Grafana push | `windows-exe/app.py` | Formats and posts metrics. No decoding logic |

---

## Module Responsibilities

**`sensors.py`** — hardware reads only. Each transmitter type has its own `sensors.py` exporting `READERS` (channel name → read function) and `TRIGGER_TYPE` (channel name → "edge" or "threshold").

**`packet.py`** — protocol implementation. No CircuitPython hardware imports. Single canonical copy in `hardware/shared/`.

**`hex_parse.py`** — decoding only. No network I/O, no GUI, no serial. Called from `app.py` as a pure function.

**`app.py`** — orchestration: GUI, serial thread, status thread, Grafana push. No decoding logic inline — delegates to `decode_lora()`.

---

## Forbidden Patterns

**F3 — `config.py` must be assignment-only.**
No functions, classes, imports, or logic in either `config.py`. Values must be literals or simple arithmetic.

**F4 — `packet.py` is a single shared file.**
`hardware/shared/packet.py` is the only copy. All transmitters and the receiver use it.

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

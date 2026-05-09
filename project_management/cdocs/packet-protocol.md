# Packet Protocol Context: Biodesign Center IoT Network

Protocol v1. All multi-byte integers are big-endian. Implemented in `hardware/shared/packet.py` (single canonical copy). `hex_parse.py` in the host app is a parallel implementation used for decoding only — it does not share code with `packet.py`.

---

## Wire Format

```
Offset  Size  Field
0       1     protocol_version (0x01)
1       1     lab_id (1–255)
2       1     node_id (1–255)
3       1     msg_type
4       1     channel_count (N)
5..     4×N   channel blocks
```

Each channel block is 4 bytes: `[channel_type:1][value:3]`. Value is 3 big-endian bytes interpreted per channel type.

---

## Message Types

| Code | Name  | Meaning                     |
|------|-------|-----------------------------|
| 0x01 | DATA  | Contains N channel readings |
| 0xFF | ERROR | Reserved                    |

Constants in `packet.py`: `MSG_DATA`, `MSG_ERROR`.

All transmissions use `MSG_DATA`. Periodic keep-alive sends are also `MSG_DATA` packets carrying current readings — there is no dedicated heartbeat message type.

---

## Channel Types

| Code | Constant        | Value Encoding                         | Implemented |
|------|-----------------|----------------------------------------|-------------|
| 0x01 | `CH_TEMPERATURE` | Signed int24, °C × 100                | Yes         |
| 0x02 | `CH_DOOR`        | 0x000001 = open, 0x000000 = closed     | Yes         |
| 0x03 | `CH_LIGHT_LEVEL` | Unsigned int24, raw ADC count          | No          |
| 0x04 | `CH_LIGHT_EVENT` | Bool (0/1), light detection event      | Yes         |
| 0x05 | `CH_CURRENT_DRAW`| Bool (0/1), drawing power             | No          |
| 0x06 | `CH_CURRENT_AMPS`| Unsigned int24, milliamps             | Yes         |

---

## Encoding (`packet.py`)

`encode_channel(channel_name, value)` returns 4 bytes. Temperature: `int(round(value * 100))` packed as signed int24. Door/bool channels: `0x000001` if true else `0x000000`. Unsigned int channels: raw int packed as unsigned int24.

`encode_packet(lab_id, node_id, msg_type, channels=None)` returns a `bytearray`. `channels` is a list of `(channel_name, value)` tuples; `None` or `[]` for heartbeat.

`decode_packet(data)` raises `ValueError` on malformed input. Returns dict with `version`, `lab_id`, `node_id`, `msg_type` (int), `channels` (list of `(name, value)` tuples).

---

## Decoding (`hex_parse.py` — host app only)

`decode_lora(hex_string)` parses a space-separated or compact hex string. Returns a dict with `version`, `lab_id`, `node_id`, `msg_type` (string: `"data_report"`, `"error"`, `"unknown"`), `channel_count`, `channels`. Each channel has `channel_type` (int), `metric` (string), `value` (float or bool). On error returns `{"error": "..."}` rather than raising.

**Warning — metric name divergence:** `hex_parse.py` uses different metric names than `packet.py` channel names. Notable differences: channel 0x04 is `"doorbell"` in hex_parse.py vs `"light_event"` in packet.py; 0x03 is `"light"` vs `"light_level"`; 0x05 is `"power"` vs `"current_draw"`. These names flow into Grafana metric labels (e.g. `biodesign_doorbell`). If you need the canonical name, use `packet.py`.

---

## Example

Data packet: lab=1, node=1, temp=4.53°C, door=closed:
```
01 01 01 01 02  01 00 01 C5  02 00 00 00
```

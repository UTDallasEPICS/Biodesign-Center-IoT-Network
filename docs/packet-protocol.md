# Packet Protocol v1

## Wire Format

All multi-byte integers are big-endian.

```
Offset  Size  Field
0       1     protocol_version (0x01)
1       1     lab_id (1–255)
2       1     node_id (1–255)
3       1     msg_type
4       1     channel_count (N)
5..     4×N   channel blocks
```

## Message Types

| Code | Name      | Description                        |
|------|-----------|------------------------------------|
| 0x01 | DATA      | Contains sensor readings           |
| 0x02 | HEARTBEAT | No channels; "I'm alive" signal    |
| 0xFF | ERROR     | Reserved for future error reporting|

## Channel Block (4 bytes each)

```
[channel_type:1][value:3]
```

| Code | Channel       | Value encoding                          |
|------|---------------|-----------------------------------------|
| 0x01 | temperature   | Signed int24, °C × 100                  |
| 0x02 | door          | 0x000000 = closed, 0x000001 = open      |
| 0x03 | light_level   | Unsigned int24, raw ADC                  |
| 0x04 | light_event   | Bool (0/1), doorbell ring detected       |
| 0x05 | current_draw  | Bool (0/1), drawing power                |
| 0x06 | current_amps  | Unsigned int24, milliamps                |

Only temperature and door are currently implemented end-to-end.

## Example

Data packet: lab=1, node=1, temp=4.53°C, door=closed:

```
01 01 01 01 02  01 00 01 C5  02 00 00 00
│  │  │  │  │   │  └─────┘   │  └─────┘
│  │  │  │  │   │  453=4.53   │  0=closed
│  │  │  │  │   ch_type=temp  ch_type=door
│  │  │  │  channel_count=2
│  │  │  msg_type=DATA
│  │  node_id=1
│  lab_id=1
version=1
```

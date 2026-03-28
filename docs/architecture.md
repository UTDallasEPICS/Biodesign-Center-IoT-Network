# Biodesign Center IoT Network — Architecture

## Purpose

Wireless sensor monitoring for ASU Biodesign Center labs. Sensor nodes in lab enclosures transmit readings over LoRa radio to a receiver node connected via USB to a host PC, which pushes metrics to Grafana Cloud.

## System Layers

```
[Sensor Nodes]  --LoRa 915 MHz-->  [Receiver Node]  --USB Serial-->  [Host PC App]  --HTTP-->  [Grafana Cloud]
 (transmitter/)                      (receiver/)                      (windows-exe/)             Prometheus remote-write
```

### 1. Transmitter Nodes (CircuitPython, Adafruit Feather RP2040 + RFM95)

Each node monitors one or more sensor channels (temperature, door state). The main loop polls sensors at a configurable interval and sends a LoRa packet when:
- A door state changes (edge detection).
- Temperature crosses a configured threshold.
- No event has fired within the heartbeat interval (heartbeat packet).

Each node is configured by editing `config.py` before flashing. Nodes are identified by `lab_id` + `node_id`.

### 2. Receiver Node (CircuitPython, same hardware)

Listens continuously on 915 MHz. On packet receipt, outputs the raw bytes as a space-separated hex string to USB serial. No decoding or processing happens on-device — the host PC handles that.

### 3. Host PC Application (`windows-exe/`)

A Tkinter GUI (`app.py`) that:
1. Auto-detects the receiver's COM port.
2. Reads hex lines from USB serial.
3. Decodes packets via `hex_parse.py`.
4. Pushes each reading to Grafana Cloud as Prometheus remote-write (InfluxDB line protocol over HTTP).

`backend.py` is a standalone/testing version of the Grafana push logic. `main.ipynb` is a notebook for batch-testing with simulated hex data.

### 4. Grafana Cloud

Receives metrics in InfluxDB line protocol at the Prometheus remote-write endpoint. Credentials are stored in `.env`. Metric name: `biodesign_sensors`, labels: `lab`, `node_id`, `metric`.

## Packet Protocol (v1)

Binary, big-endian. Header is 5 bytes, followed by N channel blocks of 4 bytes each.

```
[version:1][lab_id:1][node_id:1][msg_type:1][channel_count:1] [ch_type:1][value:3] ...
```

- `msg_type`: 0x01 = data, 0x02 = heartbeat, 0xFF = error.
- Channel types: temperature (int24, value*100), door (bool), light_level, light_event, current_draw, current_amps. Only temperature and door are implemented.
- `packet.py` is duplicated identically in `transmitter/` and `receiver/` (receiver copy exists for future on-device decoding).

## Flashing

`flash.sh` copies the appropriate firmware files to the CircuitPython USB mass-storage mount. It auto-detects the board's current role and supports Linux, WSL, and Windows (Git Bash).

## Legacy Files

`transmitter.py` and `receiver.py` in the repo root are the original PING/PONG test scripts used to validate LoRa connectivity before the protocol was designed. They are not part of the current system.

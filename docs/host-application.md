# Host PC Application (`windows-exe/`)

## Overview

Windows desktop app that reads decoded LoRa data from the receiver's USB serial port and pushes metrics to Grafana Cloud. Built with Tkinter, packaged as a standalone `.exe` via PyInstaller.

## Files

- `app.py` — Tkinter GUI. Auto-detects receiver COM port, reads hex lines from serial, decodes packets, pushes to Grafana. Start/Stop buttons control the streaming thread.
- `hex_parse.py` — `decode_lora(hex_string)` function. Parses the v1 packet protocol from a hex string into a Python dict with `lab_id`, `node_id`, `msg_type`, `channels` (each with `metric` name and `value`).
- `app.spec` / `exec.spec` — PyInstaller spec files for building the `.exe`.
- `requirements.txt` — Python dependencies: `pyinstaller`, `python-dotenv`, `pyserial`, `requests`.

## Serial Protocol

The host reads lines from USB serial at 115200 baud. Each line from the receiver is a space-separated hex string. Lines starting with `[` (debug output) are skipped.

## Grafana Push

Uses Prometheus remote-write (InfluxDB line protocol). Each channel becomes a line:

```
biodesign_sensors,lab=Lab_1,node_id=Node_1,metric=temperature_celsius reading=4.53 1234567890000000000
```

Credentials are loaded from `.env` via `python-dotenv`:
- `GRAFANA_CLOUD_URL` — Prometheus push endpoint
- `GRAFANA_CLOUD_USERNAME` — Grafana Cloud user ID
- `GRAFANA_CLOUD_API_TOKEN` — API key

## COM Port Detection

`find_receiver_port()` in `app.py` scans available COM ports for devices with "RP2040", "CircuitPython", or "Adafruit" in their description/manufacturer. Falls back to trying COM3–COM8.

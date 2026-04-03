# Project Manifest

---

## Project Context

| File | Description |
|------|-------------|
| [project_management/manifest.md](manifest.md) | This file — full project file listing with descriptions |
| [project_management/status.md](status.md) | Active work, open items, and closed items tracking |
| [project_management/cdoc.md](cdoc.md) | Template instructions for generating context documents |
| [project_management/cdocs/packet-protocol.md](cdocs/packet-protocol.md) | v1 binary packet format, channel types, encode/decode logic |
| [project_management/cdocs/transmitter-firmware.md](cdocs/transmitter-firmware.md) | Event logic, sensor polling, heartbeat, per-node configuration |
| [project_management/cdocs/receiver-firmware.md](cdocs/receiver-firmware.md) | Transparent bridge behavior, serial output format, radio config |
| [project_management/cdocs/host-app.md](cdocs/host-app.md) | Tkinter GUI, serial reading, Grafana push, node status tracking |
| [project_management/standards/style.md](standards/style.md) | Coding conventions: Python/CircuitPython naming, formatting, config patterns |
| [project_management/standards/architecture.md](standards/architecture.md) | System architecture conventions: data flow layers, sync rules, forbidden patterns |

---

## Root

| File | Description |
|------|-------------|
| [readme.txt](../readme.txt) | One-line project description |
| [status.txt](../status.txt) | Legacy project status tracker (superseded by project_management/status.md) |
| [.env](../.env) | Grafana Cloud credentials (URL, username, API token). Not committed. |
| [.gitignore](../.gitignore) | Ignores `.env` and `venv/` |
| [flash.sh](../flash.sh) | Interactive shell script to flash receiver or transmitter firmware. Auto-discovers transmitter types from `hardware/*-transmitter/` directories |
| [flash.bat](../flash.bat) | Windows wrapper for `flash.sh`. Finds Git Bash or WSL and delegates to `flash.sh` |

---

## `hardware/shared/` — Shared Firmware Files

| File | Description |
|------|-------------|
| [hardware/shared/packet.py](../hardware/shared/packet.py) | Protocol v1 packet encoder/decoder. Single canonical copy used by all transmitters and the receiver |
| [hardware/shared/code.py](../hardware/shared/code.py) | Generic transmitter main loop. Imports READERS and TRIGGER_TYPE from each transmitter's sensors.py to drive event detection |

---

## `hardware/fridge-transmitter/` — Fridge Transmitter Node Firmware (CircuitPython)

| File | Description |
|------|-------------|
| [hardware/fridge-transmitter/sensors.py](../hardware/fridge-transmitter/sensors.py) | Hardware sensor read functions (TMP36 temperature on A0, door button on D12). Exports READERS and TRIGGER_TYPE dicts for the generic main loop |
| [hardware/fridge-transmitter/config.py](../hardware/fridge-transmitter/config.py) | Per-node configuration: lab ID, node IDs, radio settings, sensor channel definitions, and thresholds. Edit before flashing each board |

---

## `hardware/receiver/` — Receiver Node Firmware (CircuitPython)

| File | Description |
|------|-------------|
| [hardware/receiver/code.py](../hardware/receiver/code.py) | Main loop. Listens for LoRa packets and prints raw bytes as space-separated hex strings to USB serial |
| [hardware/receiver/config.py](../hardware/receiver/config.py) | Receiver configuration: radio frequency and receive timeout |

---

## `windows-exe/` — Host PC Application

| File | Description |
|------|-------------|
| [windows-exe/app.py](../windows-exe/app.py) | Tkinter GUI application. Auto-detects receiver COM port, reads hex from USB serial, decodes packets, pushes metrics to Grafana Cloud, tracks node status |
| [windows-exe/hex_parse.py](../windows-exe/hex_parse.py) | `decode_lora()` function. Parses a hex string into a structured dict following the v1 packet protocol |
| [windows-exe/requirements.txt](../windows-exe/requirements.txt) | Python dependencies: pyinstaller, python-dotenv, pyserial, requests |
| [windows-exe/app.spec](../windows-exe/app.spec) | PyInstaller spec file for building `app.exe`. Bundles `hex_parse.py` as a data file |
| [windows-exe/exec.spec](../windows-exe/exec.spec) | Alternate PyInstaller spec file (older build configuration) |
| [windows-exe/package-lock.json](../windows-exe/package-lock.json) | npm lock file (legacy artifact, not actively used) |
| [windows-exe/dist/app.exe](../windows-exe/dist/app.exe) | Built Windows executable (output of PyInstaller) |

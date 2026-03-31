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
| [flash.sh](../flash.sh) | Interactive shell script to flash receiver or transmitter firmware to a Feather RP2040 |

---

## `transmitter/` — Transmitter Node Firmware (CircuitPython)

| File | Description |
|------|-------------|
| [transmitter/code.py](../transmitter/code.py) | Main loop. Polls sensors, detects events (door edge, temp threshold crossing), sends DATA or HEARTBEAT packets over LoRa |
| [transmitter/config.py](../transmitter/config.py) | Per-node configuration: lab ID, node IDs, radio settings, sensor channel definitions, and thresholds. Edit before flashing each board |
| [transmitter/packet.py](../transmitter/packet.py) | Protocol v1 packet encoder/decoder. Must stay identical to `receiver/packet.py` |
| [transmitter/sensors.py](../transmitter/sensors.py) | Hardware sensor read functions. Reads TMP36 temperature (analog, pin A0) and door button state (digital, pin D12) |

---

## `receiver/` — Receiver Node Firmware (CircuitPython)

| File | Description |
|------|-------------|
| [receiver/code.py](../receiver/code.py) | Main loop. Listens for LoRa packets and prints raw bytes as space-separated hex strings to USB serial |
| [receiver/config.py](../receiver/config.py) | Receiver configuration: radio frequency and receive timeout |
| [receiver/packet.py](../receiver/packet.py) | Protocol v1 packet encoder/decoder. Identical copy of `transmitter/packet.py`; present for potential future on-device decoding |

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


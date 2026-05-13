# Project Manifest

---

## Project Context

| File | Description |
|------|-------------|
| [documentation/manifest.md](manifest.md) | This file — full project file listing with descriptions |
| [documentation/status.md](status.md) | Active work, open items, and closed items tracking |
| [documentation/cdocs/packet-protocol.md](cdocs/packet-protocol.md) | v1 binary packet format, channel types, encode/decode logic |
| [documentation/cdocs/transmitter-firmware.md](cdocs/transmitter-firmware.md) | Event logic, sensor polling, heartbeat, per-node configuration |
| [documentation/cdocs/receiver-firmware.md](cdocs/receiver-firmware.md) | Transparent bridge behavior, serial output format, radio config |
| [documentation/cdocs/host-app.md](cdocs/host-app.md) | Tkinter GUI, serial reading, Grafana push, node status tracking |
| [documentation/cdocs/flash-tool.md](cdocs/flash-tool.md) | Flash Device tab, sensor template format, library management, shell flash scripts |

---

## Root

| File | Description |
|------|-------------|
| [README.md](../README.md) | Full project documentation: overview, roles, functional requirements, tech stack, setup instructions |
| [todo.md](../todo.md) | Codebase review — open issues grouped by file with severity labels |
| [.gitignore](../.gitignore) | Ignores `.env` and `venv/` |

---

## `hardware/sensor_templates/` — Sensor Template Files

| File | Description |
|------|-------------|
| [hardware/sensor_templates/temperature_ds18b20.py](../hardware/sensor_templates/temperature_ds18b20.py) | DS18B20 OneWire temperature sensor. Param: pin |
| [hardware/sensor_templates/door_button.py](../hardware/sensor_templates/door_button.py) | Digital push-button door sensor (Pull.UP). Param: pin |
| [hardware/sensor_templates/light_event_tsl2591.py](../hardware/sensor_templates/light_event_tsl2591.py) | TSL2591 I2C light event sensor. Param: threshold 0-100% |
| [hardware/sensor_templates/current_amps_cts-cs-cax-04.py](../hardware/sensor_templates/current_amps_cts-cs-cax-04.py) | CTS-CS-CAX-04 current transformer RMS amp sensor. Supports calibration mode. Params: pin, VBase |

---

## `hardware/libraries/` — CircuitPython Libraries

| File | Description |
|------|-------------|
| [hardware/libraries/adafruit_rfm9x.mpy](../hardware/libraries/adafruit_rfm9x.mpy) | Adafruit RFM9x LoRa radio driver |
| [hardware/libraries/adafruit_ds18x20.mpy](../hardware/libraries/adafruit_ds18x20.mpy) | Adafruit DS18x20 OneWire temperature sensor driver |
| [hardware/libraries/adafruit_tsl2591.mpy](../hardware/libraries/adafruit_tsl2591.mpy) | Adafruit TSL2591 I2C light sensor driver |
| [hardware/libraries/adafruit_onewire/bus.mpy](../hardware/libraries/adafruit_onewire/bus.mpy) | Adafruit OneWire bus implementation |
| [hardware/libraries/adafruit_onewire/device.mpy](../hardware/libraries/adafruit_onewire/device.mpy) | Adafruit OneWire device base class |
| [hardware/libraries/adafruit_onewire/__init__.py](../hardware/libraries/adafruit_onewire/__init__.py) | Adafruit OneWire package init |

---

## `hardware/shared/` — Shared Firmware Files

| File | Description |
|------|-------------|
| [hardware/shared/packet.py](../hardware/shared/packet.py) | Protocol v1 packet encoder/decoder. Single canonical copy used by all transmitters and the receiver |
| [hardware/shared/code.py](../hardware/shared/code.py) | Generic transmitter main loop. Imports READERS and TRIGGER_TYPE from each transmitter's sensors.py to drive event detection |

---

## `hardware/receiver/` — Receiver Node Firmware (CircuitPython)

| File | Description |
|------|-------------|
| [hardware/receiver/code.py](../hardware/receiver/code.py) | Main loop. Listens for LoRa packets and prints raw bytes as space-separated hex strings to USB serial. Feeds hardware watchdog each iteration |
| [hardware/receiver/config.py](../hardware/receiver/config.py) | Receiver configuration: radio frequency and receive timeout |
| [hardware/receiver/boot.py](../hardware/receiver/boot.py) | Startup-only: bounds `usb_cdc.console.write_timeout` so a stalled host CDC endpoint cannot block `print()` indefinitely |

---

## `windows-exe/` — Host PC Application

| File | Description |
|------|-------------|
| [windows-exe/app.py](../windows-exe/app.py) | Tabbed Tkinter GUI and orchestration. Four tabs: Data Stream (log, start/stop), Node Pairing (discover transmitters, toggle listen), Known Flashes, and Flash Device. Manages thread lifecycle, owns `node_last_seen`, `discovered_nodes`, `listened_nodes`, `remembered_nodes`, `flashed_nodes`, and `packet_queue`. Only pushes to Grafana for listened transmitters |
| [windows-exe/flash_tab.py](../windows-exe/flash_tab.py) | Flash Device tab: `FlashTab` GUI class. Builds the widget tree, owns sensor list state, dispatches flash actions on a worker thread. Pure UI/orchestration — delegates parsing, composing, drive I/O, and dialogs to the modules below |
| [windows-exe/flash_paths.py](../windows-exe/flash_paths.py) | Shared paths and constants for the flash modules: `BOARD_PINS` and resolved `TEMPLATES_DIR` / `SHARED_DIR` / `RECEIVER_DIR` / `LIBRARIES_DIR` (handles PyInstaller `sys._MEIPASS`) |
| [windows-exe/flash_templates.py](../windows-exe/flash_templates.py) | Sensor template parser: `parse_template`, `discover_templates`, and `match_sensor_records` for resolving saved flash records back to live templates |
| [windows-exe/flash_compose.py](../windows-exe/flash_compose.py) | Code composer: `compose_sensors_py` and `compose_config_py` build the strings written to the board. Pure functions, no I/O |
| [windows-exe/flash_actions.py](../windows-exe/flash_actions.py) | Drive scanning, file copying, and flash sequences: `scan_drives`, `flash_transmitter`, `flash_receiver`, plus `check_transmitter_id_status` for the pre-flash uniqueness classification |
| [windows-exe/flash_dialogs.py](../windows-exe/flash_dialogs.py) | Tk dialog helpers: `open_add_sensor_dialog`, `open_name_dialog`, `open_code_preview`, plus `confirm_reflash` and `show_id_blocked` messageboxes |
| [windows-exe/storage.py](../windows-exe/storage.py) | Persistent state I/O. Reads and writes `%LOCALAPPDATA%\biosensing\state.json` (listened nodes, remembered nodes with names, flash history). No GUI, no serial, no Grafana |
| [windows-exe/grafana.py](../windows-exe/grafana.py) | Grafana Cloud I/O. Loads credentials from `.env`, formats InfluxDB line protocol, pushes data and node status metrics |
| [windows-exe/serial_reader.py](../windows-exe/serial_reader.py) | Serial port discovery (`scan_ports`) and receiver read loop (`read_from_receiver`). Puts decoded packets onto a queue. No Grafana logic |
| [windows-exe/hex_parse.py](../windows-exe/hex_parse.py) | `decode_lora()` function. Parses a hex string into a structured dict following the v1 packet protocol |
| [windows-exe/requirements.txt](../windows-exe/requirements.txt) | Python dependencies: pyinstaller, python-dotenv, pyserial, requests |
| [windows-exe/app.spec](../windows-exe/app.spec) | PyInstaller spec file for building `app.exe`. Bundles `hex_parse.py` as a data file |
| [windows-exe/exec.spec](../windows-exe/exec.spec) | Alternate PyInstaller spec file (older build configuration) |
| [windows-exe/package-lock.json](../windows-exe/package-lock.json) | npm lock file (legacy artifact, not actively used) |
| [windows-exe/.env](../windows-exe/.env) | Grafana Cloud credentials (URL, username, API token). Not committed. |
| [windows-exe/.env.example](../windows-exe/.env.example) | Example env file showing required credential keys. Committed. |
| [windows-exe/dist/app.exe](../windows-exe/dist/app.exe) | Built Windows executable (output of PyInstaller) |

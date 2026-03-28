# File Manifest

Every file in the repository (excluding `venv/`, `.git/`, `__pycache__/`, `.ruby-lsp/`, and build artifacts).

## Root

| Path | Description |
|------|-------------|
| `readme.txt` | One-line project description. |
| `status.txt` | Project status tracker: completed work, in-progress items, and TODO list. |
| `.env` | Grafana Cloud credentials (URL, username, API token). Not committed to public repos. |
| `.gitignore` | Ignores `.env` and `venv/`. |
| `flash.sh` | Interactive shell script to flash receiver or transmitter firmware to a Feather RP2040 board. |

## `transmitter/` — Transmitter Node Firmware (CircuitPython)

| Path | Description |
|------|-------------|
| `transmitter/code.py` | Main loop. Polls sensors, detects events (door edge, temp threshold crossing), sends DATA or HEARTBEAT packets over LoRa. |
| `transmitter/config.py` | Per-node configuration: lab ID, node IDs, radio settings, sensor channel definitions, and thresholds. Edit before flashing each board. |
| `transmitter/packet.py` | Protocol v1 packet encoder. Builds binary packets from header fields and channel readings. Kept identical to `receiver/packet.py`. |
| `transmitter/sensors.py` | Hardware sensor read functions. Reads TMP36 temperature (analog, pin A0) and door button state (digital, pin D12). |

## `receiver/` — Receiver Node Firmware (CircuitPython)

| Path | Description |
|------|-------------|
| `receiver/code.py` | Main loop. Listens for LoRa packets and prints raw bytes as space-separated hex strings to USB serial. |
| `receiver/config.py` | Receiver configuration: radio frequency and receive timeout. |
| `receiver/packet.py` | Protocol v1 packet encoder/decoder. Identical copy of `transmitter/packet.py`. Present for potential future on-device decoding. |

## `windows-exe/` — Host PC Application

| Path | Description |
|------|-------------|
| `windows-exe/app.py` | Tkinter GUI application. Auto-detects receiver COM port, reads hex from USB serial, decodes packets, and pushes metrics to Grafana Cloud. |
| `windows-exe/backend.py` | Standalone Grafana push module with test harness. Decodes hex data and sends to Grafana Cloud via Prometheus remote-write. |
| `windows-exe/hex_parse.py` | `decode_lora()` function. Parses a hex string into a structured dict following the v1 packet protocol. |
| `windows-exe/main.ipynb` | Jupyter notebook for batch-testing. Loops over sample hex strings, decodes and pushes to Grafana. |
| `windows-exe/requirements.txt` | Python dependencies: pyinstaller, python-dotenv, pyserial, requests. |
| `windows-exe/app.spec` | PyInstaller spec file for building `app.exe`. Bundles `hex_parse.py` as a data file. |
| `windows-exe/exec.spec` | Alternate PyInstaller spec file (older build configuration). |
| `windows-exe/dist/app.exe` | Built Windows executable (output of PyInstaller). |

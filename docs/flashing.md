# Flashing Firmware (`flash.sh`)

## Overview

Shell script that copies CircuitPython firmware files to a Feather RP2040 board's USB mass-storage mount.

## Usage

```bash
./flash.sh
```

The script prompts for:
1. **Mount point** — drive letter (Windows) or path (Linux/WSL) where the board appears.
2. **Role** — receiver or transmitter. Auto-detected if the board already has firmware files.

## OS Detection

Supports three environments:
- **Linux**: expects mount at `/media/$USER/CIRCUITPY`.
- **WSL**: expects mount under `/mnt/` (e.g., `/mnt/d`).
- **Windows (Git Bash/MSYS)**: expects a drive letter (e.g., `D`).

## Files Copied

| Role        | Files                                  |
|-------------|----------------------------------------|
| Receiver    | `code.py`, `config.py`, `packet.py`   |
| Transmitter | `code.py`, `config.py`, `packet.py`, `sensors.py` |

## Auto-Detection

If `sensors.py` exists on the board, it was previously flashed as a transmitter. If only `code.py` exists, it's treated as a receiver. The user can override the detection.

import os
import sys


# Board pin options for Adafruit Feather RP2040
BOARD_PINS = [
    "D0", "D1", "D4", "D5", "D6", "D9", "D10", "D11", "D12", "D13",
    "D24", "D25", "A0", "A1", "A2", "A3",
]

# Paths: when frozen by PyInstaller, bundled data lives under sys._MEIPASS;
# otherwise resolve relative to the repo root (one level up from windows-exe/).
if getattr(sys, "frozen", False):
    _DATA_ROOT = sys._MEIPASS
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))

TEMPLATES_DIR = os.path.join(_DATA_ROOT, "hardware", "sensor_templates")
SHARED_DIR = os.path.join(_DATA_ROOT, "hardware", "shared")
RECEIVER_DIR = os.path.join(_DATA_ROOT, "hardware", "receiver")
LIBRARIES_DIR = os.path.join(_DATA_ROOT, "hardware", "libraries")

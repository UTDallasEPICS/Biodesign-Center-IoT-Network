# sensors.py
# Mock sensor implementations for testing without hardware.
#
# To connect real sensors: replace the body of each read_* function.
# The function signatures and return types must stay the same.
#
#   read_temperature() -> float   degrees Celsius
#   read_door()        -> bool    False=closed, True=open

import board
import analogio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20

# ---------------------------------------------------------------------------
# Pin setup
# ---------------------------------------------------------------------------

# Temperature: DS18B20 on D13
# Initialize one-wire bus on board pin D13.
ow_bus = OneWireBus(board.D13)

# Scan for sensors and grab the first one found.
ds18 = DS18X20(ow_bus, ow_bus.scan()[0])

# Door: push button on D12 (pressed = closed, released = open)
btn = DigitalInOut(board.D12)
btn.direction = Direction.INPUT
btn.pull = Pull.UP


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_temperature():
    """Returns current temperature in degrees Celsius (float)."""
    
    return ds18.temperature


def read_door():
    """Returns door state as bool (False=closed, True=open).

    Pull.UP means btn.value is True when released (open) and False when pressed (closed).
    """
    return btn.value  # True = not pressed = door open


# ---------------------------------------------------------------------------
# Generic interface for shared/code.py
# ---------------------------------------------------------------------------

READERS = {
    "temperature": read_temperature,   # () -> float
    "door":        read_door,          # () -> bool
}

TRIGGER_TYPE = {
    "door": "edge",   # fires on any state change
}

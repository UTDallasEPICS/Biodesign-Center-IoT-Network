# sensors.py
# Door transmitter: light event sensor on A0.
#
#   read_light_event() -> bool    False=no light, True=light detected

import board
import analogio

# ---------------------------------------------------------------------------
# Pin setup
# ---------------------------------------------------------------------------

# Light sensor on A0
light_sensor = analogio.AnalogIn(board.A0)

# Threshold for light detection (raw 16-bit ADC count, 0–65535).
# Set above half-scale as a starting point; tune per deployment.
LIGHT_THRESHOLD = 32768


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_light_event():
    """Returns True when light level exceeds LIGHT_THRESHOLD, False otherwise."""
    return light_sensor.value < LIGHT_THRESHOLD


# ---------------------------------------------------------------------------
# Generic interface for shared/code.py
# ---------------------------------------------------------------------------

READERS = {
    "light_event": read_light_event,   # () -> bool
}

TRIGGER_TYPE = {
    "light_event": "edge",   # fires on any state change
}

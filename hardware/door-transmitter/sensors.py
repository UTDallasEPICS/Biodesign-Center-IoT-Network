# sensors.py
# Door transmitter: light event sensor on A0.
#
#   read_light_event() -> bool    False=no light, True=light detected

import board
import analogio
import adafruit_tsl2591

# ---------------------------------------------------------------------------
# Pin setup
# ---------------------------------------------------------------------------

# Light sensor on I2C (SCL and SDA)
i2c = board.I2C()
sensor = adafruit_tsl2591.TSL2591(i2c)

# Threshold for light detection (raw 32-bit count, 0–2147483647).
# Set above half-scale as a starting point; tune per deployment.
LIGHT_THRESHOLD = 15000


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_light_event():
    """Returns True when light level exceeds LIGHT_THRESHOLD, False otherwise."""
    
    return sensor.visible > LIGHT_THRESHOLD


# ---------------------------------------------------------------------------
# Generic interface for shared/code.py
# ---------------------------------------------------------------------------

READERS = {
    "light_event": read_light_event,   # () -> bool
}

TRIGGER_TYPE = {
    "light_event": "edge",   # fires on any state change
}

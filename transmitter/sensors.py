# sensors.py
# Mock sensor implementations for testing without hardware.
#
# To connect real sensors: replace the body of each read_* function.
# The function signatures and return types must stay the same.
#
#   read_temperature() -> float   degrees Celsius
#   read_door()        -> bool    False=closed, True=open

import random

# ---------------------------------------------------------------------------
# Mock state
# ---------------------------------------------------------------------------

# Temperature: biased random walk oscillating between _TEMP_MIN and _TEMP_MAX.
# With the default config threshold of 5.0 C, this produces a threshold
# crossing roughly every 15 seconds at a 1-second poll interval.
_TEMP_MIN   = 3.5
_TEMP_MAX   = 6.0
_mock_temp  = 4.5
_temp_trend = 0.15   # positive = warming; flips at bounds

# Door: probabilistic state flip.
# P(flip) = 0.067 per poll => mean ~15 s between state changes at 1 s polling.
_DOOR_FLIP_PROB = 0.067
_mock_door_open = False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def read_temperature():
    """
    Returns current temperature reading in degrees Celsius (float).

    Real hardware: replace with ADC read + calibration formula.
    """
    global _mock_temp, _temp_trend

    _mock_temp += _temp_trend + random.uniform(-0.10, 0.10)

    if _mock_temp >= _TEMP_MAX:
        _temp_trend = -0.15
        _mock_temp  = _TEMP_MAX
    elif _mock_temp <= _TEMP_MIN:
        _temp_trend = 0.15
        _mock_temp  = _TEMP_MIN

    return round(_mock_temp, 2)


def read_door():
    """
    Returns door state as bool (False=closed, True=open).

    Real hardware: replace with GPIO read on a magnetic reed switch.
    """
    global _mock_door_open

    if random.random() < _DOOR_FLIP_PROB:
        _mock_door_open = not _mock_door_open

    return _mock_door_open

# --- Sensor Template ---
# name: Current (Analog)
# channel: current_amps
# trigger: none
# libraries:
#
# param: pin | A0

# --- imports ---
from analogio import AnalogIn

# --- setup ---
power_pin = AnalogIn(board.A0)


# --- read ---
def read_current():
    voltage = (power_pin.value * 5.0) / 65535
    current = (voltage - 0.5) * (75 / 4.0) 
    return current

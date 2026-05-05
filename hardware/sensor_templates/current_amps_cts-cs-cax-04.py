# --- Sensor Template ---
# name: Current (Analog)
# channel: current_amps
# trigger: none
# libraries:
#
# param: pin | Analog Pin | pin | A0

# --- imports ---
import time
from analogio import AnalogIn

# --- setup ---
power_pin = AnalogIn(board.{pin})
VBase = 2.521263
Sensitivity = 2/75.0
MCUVoltage = 3.3

# --- read ---
def read_current_amps():
    total = 0
    samples = 300
    interval = 3.0 / samples
    for _ in range(samples):
        # Vout = (power_pin.value / 65535.0) * MCUVoltage
        # Amps = (Vout - VBase) / Sensitivity
        # total += Amps
        total += power_pin.value
        time.sleep(interval)
    return (total / samples)

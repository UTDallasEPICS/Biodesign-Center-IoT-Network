# --- Sensor Template ---
# name: Current (Analog)
# channel: current_amps
# trigger: none
# libraries:
#
# param: pin | Analog Pin | pin | A0
# param: sensitivity | Sensor sensitivity | number | 0.026667
# param: VBase | Sensor Voltage Offset | number | 2.5167315
# param: MCUVoltage | Voltage of Microcontroller | number | 3.3

# --- imports ---
import time
import math
from analogio import AnalogIn

# --- setup ---
power_pin = AnalogIn(board.{pin})

# --- read ---
def read_current_amps():
    total = 0
    samples = 300
    interval = 3.0 / samples
    for _ in range(samples):
        Vout = (power_pin.value / 65535.0) * {MCUVoltage}
        Amps = (Vout - {VBase}) / {sensitivity}
        total += Amps * Amps
        time.sleep(interval)
    return math.sqrt(total / samples)*1000

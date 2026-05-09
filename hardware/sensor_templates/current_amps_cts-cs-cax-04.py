# --- Sensor Template ---
# name: Current (Analog)
# channel: current_amps
# trigger: none
# libraries:
#
# param: pin | Analog Pin | pin | A0
# param: sensitivity | Sensor sensitivity | number | 0.026667
# param: VBase | Sensor Voltage Offset | number | 2.53
# param: MCUVoltage | Voltage of Microcontroller | number | 3.3
# param: calibrating | Calibrating Mode | boolean | False

# --- imports ---
import time
import math
from analogio import AnalogIn

# --- setup ---
power_pin = AnalogIn(board.{pin})

# --- read ---
def read_current_amps():
    total = 0
    vout_total = 0
    samples = 300
    interval = 3.0 / samples
    for _ in range(samples):
        Vout = (power_pin.value / 65535.0) * {MCUVoltage}
        Amps = (Vout - {VBase}) / {sensitivity}
        total += Amps * Amps
        vout_total += Vout
        time.sleep(interval)
    if {calibrating}:
        return vout_total / samples * 1000000
    return math.sqrt(total / samples) * 1000

# --- Sensor Template ---
# name: Door / Button (Digital)
# channel: door
# trigger: edge
# libraries:
#
# param: pin | Button Pin (Pull.UP) | pin | D12

# --- imports ---
from digitalio import DigitalInOut, Pull

# --- setup ---
door_sensor = DigitalInOut(board.{pin})
door_sensor.switch_to_input(pull=Pull.UP)

# --- read ---
def read_door():
    return door_sensor.value

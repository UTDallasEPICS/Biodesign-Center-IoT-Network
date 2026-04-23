# --- Sensor Template ---
# name: Door / Button (Digital)
# channel: door
# trigger: edge
# libraries:
#
# param: pin | Button Pin (Pull.UP) | pin | D12

# --- imports ---
from digitalio import DigitalInOut, Direction, Pull

# --- setup ---
door_btn = DigitalInOut(board.{pin})
door_btn.direction = Direction.INPUT
door_btn.pull = Pull.UP

# --- read ---
def read_door():
    return door_btn.value

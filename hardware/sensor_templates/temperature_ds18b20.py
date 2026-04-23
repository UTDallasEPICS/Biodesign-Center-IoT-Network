# --- Sensor Template ---
# name: Temperature (DS18B20, OneWire)
# channel: temperature
# trigger: none
# libraries: adafruit_onewire/, adafruit_ds18x20.mpy
#
# param: pin | OneWire Pin | pin | D11

# --- imports ---
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20

# --- setup ---
ow_bus = OneWireBus(board.{pin})
ds18_sensor = DS18X20(ow_bus, ow_bus.scan()[0])

# --- read ---
def read_temperature():
    return ds18_sensor.temperature

# --- Sensor Template ---
# name: Light Event (TSL2591, I2C)
# channel: light_event
# trigger: edge
# libraries: adafruit_tsl2591.mpy
#
# param: threshold_pct | Light Threshold (0-100%) | percent | 50

# --- imports ---
import adafruit_tsl2591

# --- setup ---
_i2c = board.I2C()
tsl_sensor = adafruit_tsl2591.TSL2591(_i2c)
LIGHT_THRESHOLD = int({threshold_pct} / 100.0 * 10000)

# --- read ---
def read_light_event():
    return tsl_sensor.visible > LIGHT_THRESHOLD

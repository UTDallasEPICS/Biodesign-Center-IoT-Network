# sensor_defs.py
# Channel type registry for the sensor flashing view.
# Each entry defines UI fields and code templates for generating
# config.py and sensors.py firmware files.

# --- Pin options for Adafruit Feather RP2040 ---

ANALOG_PINS = ["A0", "A1", "A2", "A3"]
DIGITAL_PINS = ["D4", "D5", "D6", "D9", "D10", "D11", "D12", "D13", "D24", "D25"]

# --- Channel definitions ---
#
# Each key matches a channel name in packet.py.
# Fields:
#   label          : Human-readable name shown in the UI
#   pin_type       : "analog" or "digital"
#   trigger_type   : "edge" or None (None = no trigger, heartbeat only)
#   fields         : list of UI field defs for the flasher view
#   imports        : list of import lines the generated sensors.py needs
#   pin_setup      : template string for pin/hardware init code
#   constants      : template string for module-level constants (or "")
#   read_fn_name   : name of the generated read function
#   read_fn_body   : template string for the read function body
#   read_fn_doc    : docstring for the read function
#   read_fn_return : return type annotation comment (for the READERS dict)

CHANNEL_DEFS = {
    "temperature": {
        "label": "Temperature (TMP36)",
        "pin_type": "analog",
        "trigger_type": None,
        "fields": [
            {
                "name": "pin",
                "label": "Analog Pin",
                "type": "choice",
                "options": ANALOG_PINS,
                "default": "A0",
            },
            {
                "name": "unit",
                "label": "Unit",
                "type": "choice",
                "options": ["C", "F"],
                "default": "C",
                "note_on": {
                    "F": "Note: Grafana dashboards expect Celsius. You will need to "
                         "adjust your Grafana queries if this node sends Fahrenheit.",
                },
            },
        ],
        "imports": ["import board", "import analogio"],
        "pin_setup": "tmp36 = analogio.AnalogIn(board.{pin})",
        "constants": "",
        "read_fn_name": "read_temperature",
        "read_fn_doc": "Returns current temperature in degrees {unit_long} (float).",
        "read_fn_body_C": (
            "    voltage = (tmp36.value * 3.3) / 65536\n"
            "    return (voltage - 0.5) * 100"
        ),
        "read_fn_body_F": (
            "    voltage = (tmp36.value * 3.3) / 65536\n"
            "    celsius = (voltage - 0.5) * 100\n"
            "    return celsius * 9.0 / 5.0 + 32.0"
        ),
        "read_fn_return": "float",
    },
    "door": {
        "label": "Door (Digital Switch)",
        "pin_type": "digital",
        "trigger_type": "edge",
        "fields": [
            {
                "name": "pin",
                "label": "Digital Pin",
                "type": "choice",
                "options": DIGITAL_PINS,
                "default": "D12",
            },
            {
                "name": "pull",
                "label": "Pull Resistor",
                "type": "choice",
                "options": ["UP", "DOWN"],
                "default": "UP",
            },
            {
                "name": "closed_when_pressed",
                "label": "Closed When Pressed",
                "type": "bool",
                "default": True,
            },
        ],
        "imports": ["import board", "from digitalio import DigitalInOut, Direction, Pull"],
        "pin_setup": (
            "btn = DigitalInOut(board.{pin})\n"
            "btn.direction = Direction.INPUT\n"
            "btn.pull = Pull.{pull}"
        ),
        "constants": "",
        "read_fn_name": "read_door",
        "read_fn_doc": "Returns door state as bool (False=closed, True=open).",
        "read_fn_return": "bool",
        # read_fn_body is built dynamically based on closed_when_pressed + pull
    },
    "light_event": {
        "label": "Light Event (Analog Threshold)",
        "pin_type": "analog",
        "trigger_type": "edge",
        "fields": [
            {
                "name": "pin",
                "label": "Analog Pin",
                "type": "choice",
                "options": ANALOG_PINS,
                "default": "A0",
            },
            {
                "name": "threshold_pct",
                "label": "Light Threshold (%)",
                "type": "scale",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        ],
        "imports": ["import board", "import analogio"],
        "pin_setup": "light_sensor = analogio.AnalogIn(board.{pin})",
        "constants": "LIGHT_THRESHOLD = {threshold_raw}",
        "read_fn_name": "read_light_event",
        "read_fn_doc": "Returns True when light level exceeds threshold, False otherwise.",
        "read_fn_body": "    return light_sensor.value < LIGHT_THRESHOLD",
        "read_fn_return": "bool",
    },
    "current_draw": {
        "label": "Current Draw (Analog Threshold)",
        "pin_type": "analog",
        "trigger_type": "edge",
        "fields": [
            {
                "name": "pin",
                "label": "Analog Pin",
                "type": "choice",
                "options": ANALOG_PINS,
                "default": "A1",
            },
            {
                "name": "threshold_pct",
                "label": "Current Threshold (%)",
                "type": "scale",
                "min": 0,
                "max": 100,
                "default": 50,
            },
        ],
        "imports": ["import board", "import analogio"],
        "pin_setup": "current_sensor = analogio.AnalogIn(board.{pin})",
        "constants": "CURRENT_THRESHOLD = {threshold_raw}",
        "read_fn_name": "read_current_draw",
        "read_fn_doc": "Returns True when current draw exceeds threshold, False otherwise.",
        "read_fn_body": "    return current_sensor.value > CURRENT_THRESHOLD",
        "read_fn_return": "bool",
    },
}


def pct_to_adc(pct):
    """Convert a 0-100 percentage to a 16-bit ADC value (0-65535)."""
    return int(round(pct / 100.0 * 65535))


def build_read_fn_body(channel, params):
    """Return the read function body string for a channel given its parameters."""
    defn = CHANNEL_DEFS[channel]

    if channel == "temperature":
        unit = params.get("unit", "C")
        if unit == "F":
            return defn["read_fn_body_F"]
        return defn["read_fn_body_C"]

    if channel == "door":
        closed_when_pressed = params.get("closed_when_pressed", True)
        # With Pull.UP: btn.value is True when released, False when pressed.
        # With Pull.DOWN: btn.value is False when released, True when pressed.
        pull = params.get("pull", "UP")
        if pull == "UP":
            # btn.value: True = released, False = pressed
            if closed_when_pressed:
                # pressed = closed -> btn.value True = open
                return "    return btn.value"
            else:
                # pressed = open -> btn.value True = closed
                return "    return not btn.value"
        else:
            # Pull.DOWN: btn.value: False = released, True = pressed
            if closed_when_pressed:
                # pressed = closed -> btn.value False = open
                return "    return not btn.value"
            else:
                # pressed = open -> btn.value False = closed
                return "    return btn.value"

    # light_event and current_draw have static bodies in the definition
    return defn["read_fn_body"]

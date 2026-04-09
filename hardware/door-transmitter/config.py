# =============================================================
# Transmitter Node Configuration
# Flash this file to each node and edit values to match the
# physical setup. No other files should need to change between nodes.
# =============================================================

# --- Network Identity ---
LAB_ID  = 0x02   # Physical lab this node belongs to (1-255, 0 reserved)
NODE_ID = 0x02   # Unique ID matching the physical label on this enclosure (1-255)

# --- Radio ---
RADIO_FREQ_MHZ = 915.0  # Hz. Must match receiver exactly.
TX_POWER       = 5      # dBm (5-23). Keep low if USB disconnects during TX.

# --- Timing ---
HEARTBEAT_INTERVAL = 30   # Seconds. Heartbeat sent if no event in this window.
POLL_INTERVAL      = 1    # Seconds between sensor reads.

# --- Sensor Definitions ---
# Each entry describes one sensor on this transmitter board.
#
# Fields:
#   channel  : str    Which channel type this sensor reports.
#                     Supported now : "temperature", "door", "light_event"
#                     Reserved      : "light_level", "current_draw", "current_amps"
#   threshold: float  (optional) Value that triggers an immediate send on crossing.
#                     Applies to threshold-type channels (e.g. temperature).
#                     Edge-type channels (e.g. door, light_event) fire on any state change.

SENSORS = [
    {"channel": "light_event"},
]

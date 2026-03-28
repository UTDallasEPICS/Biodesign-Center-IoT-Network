# =============================================================
# Transmitter Node Configuration
# Flash this file to each node and edit values to match the
# physical setup. No other files should need to change between nodes.
# =============================================================

# --- Network Identity ---
LAB_ID = 0x01           # Physical lab this node belongs to (1-255, 0 reserved)

# --- Radio ---
RADIO_FREQ_MHZ = 915.0  # Hz. Must match receiver exactly.
TX_POWER       = 5     # dBm (5-23). Keep low if USB disconnects during TX.

# --- Timing ---
HEARTBEAT_INTERVAL    = 30    # Seconds. Heartbeat sent if no event in this window.
POLL_INTERVAL         = 1     # Seconds between sensor reads.
PERIODIC_SEND_INTERVAL = 15   # TEMPORARY: send all readings every N seconds regardless of events.

# --- Sensor Definitions ---
# Each entry describes one physical sensor enclosure monitored by this node.
#
# Fields:
#   sensor_id : int  (1-255)  Unique ID matching the physical label on the enclosure.
#   channels  : list[str]     Which channel types this sensor reports.
#                             Supported now : "temperature", "door"
#                             Reserved      : "light_level", "light_event",
#                                            "current_draw", "current_amps"
#   thresholds: dict          Channel type -> value that triggers an immediate send.
#                             temperature : float °C, fires on threshold crossing.
#                             door        : not applicable (fires on any state change).
#
# Threshold note (mock data): temperature mock oscillates ~3.5-6.0 C.
# A threshold of 5.0 produces crossings roughly every 15 seconds for testing.
# Adjust this value when real sensors are connected.

SENSORS = [
    {
        "sensor_id": 0x01,
        "channels": ["temperature", "door"],
        "thresholds": {
            "temperature": 10.0,   # °C — crossing triggers an immediate data send
        },
    },
]

# =============================================================
# Receiver Node Configuration
# =============================================================

RADIO_FREQ_MHZ  = 915.0   # Must match transmitters exactly.
RECEIVE_TIMEOUT = 1.0     # Seconds per receive() call. Kept short so the loop
                          # stays responsive; does not affect how often packets
                          # are received (radio listens continuously between calls).

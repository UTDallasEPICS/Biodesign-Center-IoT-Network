#!/usr/bin/env bash
# flash.sh — Copy firmware files to CircuitPython boards.
#
# CircuitPython boards mount as USB mass storage (separate from ttyACM*).
# Find mount points with:  lsblk -o NAME,LABEL,MOUNTPOINT | grep CIRCUITPY
# or check: ls /media/$USER/

RECEIVER_MOUNT="/media/$USER/CIRCUITPY"
TRANSMITTER_MOUNT="/media/$USER/CIRCUITPY1"

# --- Verify mounts are present ---
if [ ! -d "$RECEIVER_MOUNT" ]; then
    echo "ERROR: Receiver not mounted at $RECEIVER_MOUNT"
    exit 1
fi
if [ ! -d "$TRANSMITTER_MOUNT" ]; then
    echo "ERROR: Transmitter not mounted at $TRANSMITTER_MOUNT"
    exit 1
fi

# --- Flash receiver ---
echo "Flashing receiver -> $RECEIVER_MOUNT"
cp receiver/code.py   "$RECEIVER_MOUNT/code.py"
cp receiver/config.py "$RECEIVER_MOUNT/config.py"
cp receiver/packet.py "$RECEIVER_MOUNT/packet.py"
echo "  code.py  config.py  packet.py"

# --- Flash transmitter ---
echo "Flashing transmitter -> $TRANSMITTER_MOUNT"
cp transmitter/code.py   "$TRANSMITTER_MOUNT/code.py"
cp transmitter/config.py "$TRANSMITTER_MOUNT/config.py"
cp transmitter/packet.py "$TRANSMITTER_MOUNT/packet.py"
cp transmitter/sensors.py "$TRANSMITTER_MOUNT/sensors.py"
echo "  code.py  config.py  packet.py  sensors.py"

echo "Done."

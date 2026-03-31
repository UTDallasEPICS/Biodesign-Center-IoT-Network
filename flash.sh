#!/usr/bin/env bash
# flash.sh — Flash firmware to a single CircuitPython board.
#
# Usage: run once per microcontroller.
# Detects OS (Linux/Windows via Git Bash/WSL) and asks:
#   1. What mount point / drive letter is the board at?
#   2. Flash receiver or fridge-transmitter? (auto-detected if board was previously flashed)

set -euo pipefail

# --- Detect OS / environment ---
detect_os() {
    case "$(uname -s)" in
        Linux*)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        MINGW*|CYGWIN*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

OS=$(detect_os)

# --- Ask for mount point ---
echo ""
if [ "$OS" = "windows" ]; then
    echo "Windows detected."
    echo "CircuitPython boards appear as a drive (e.g. D:, E:, F:)."
    read -rp "Enter the drive letter of the board (e.g. D): " DRIVE
    # Normalize: strip trailing colon/slash, uppercase
    DRIVE="${DRIVE%%[:\\/]*}"
    DRIVE="${DRIVE^^}"
    MOUNT="${DRIVE}:/"
elif [ "$OS" = "wsl" ]; then
    echo "WSL detected."
    echo "CircuitPython boards are typically auto-mounted under /mnt/ (e.g. /mnt/d)."
    read -rp "Enter mount path of the board (e.g. /mnt/d or /media/\$USER/CIRCUITPY): " MOUNT
else
    echo "Linux detected."
    echo "CircuitPython boards mount under /media/\$USER/ (e.g. /media/\$USER/CIRCUITPY)."
    read -rp "Enter mount path of the board (e.g. /media/$USER/CIRCUITPY): " MOUNT
fi

# Strip trailing slash for consistency, then add it back
MOUNT="${MOUNT%/}/"

# --- Verify mount exists ---
if [ ! -d "$MOUNT" ]; then
    echo "ERROR: '$MOUNT' is not accessible or does not exist."
    exit 1
fi

# --- Auto-detect role from existing files on board ---
echo ""
if [ -f "${MOUNT}sensors.py" ]; then
    DETECTED="fridge-transmitter"
elif [ -f "${MOUNT}code.py" ]; then
    DETECTED="receiver"
else
    DETECTED=""
fi

if [ -n "$DETECTED" ]; then
    echo "Detected existing firmware: $DETECTED"
    read -rp "Flash as $DETECTED? [Y/n]: " CONFIRM
    CONFIRM="${CONFIRM:-Y}"
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
        ROLE="$DETECTED"
    else
        DETECTED=""  # fall through to manual selection
    fi
fi

if [ -z "$DETECTED" ]; then
    echo "What would you like to flash to '$MOUNT'?"
    echo "  1) Receiver"
    echo "  2) Transmitter"
    read -rp "Enter 1 or 2: " CHOICE
    case "$CHOICE" in
        1) ROLE="receiver"     ;;
        2) ROLE="fridge-transmitter"  ;;
        *)
            echo "ERROR: Invalid choice '$CHOICE'. Enter 1 or 2."
            exit 1
            ;;
    esac
fi

case "$ROLE" in
    receiver)    FILES=("code.py" "config.py" "packet.py") ;;
    fridge-transmitter) FILES=("code.py" "config.py" "packet.py" "sensors.py") ;;
esac

# --- Flash ---
echo ""
echo "Flashing $ROLE -> $MOUNT"
for FILE in "${FILES[@]}"; do
    SRC="$ROLE/$FILE"
    if [ ! -f "$SRC" ]; then
        echo "  WARNING: source file '$SRC' not found — skipping."
        continue
    fi
    cp "$SRC" "${MOUNT}${FILE}"
    echo "  $FILE"
done

echo ""
echo "Done."

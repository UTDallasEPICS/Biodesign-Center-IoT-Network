#!/usr/bin/env bash
# flash.sh — Flash firmware to a single CircuitPython board.
#
# Usage: run once per microcontroller from the repo root.
# Detects OS (Linux/Windows via Git Bash/WSL) and asks:
#   1. What mount point / drive letter is the board at?
#   2. Flash receiver or which transmitter? (auto-detected if board was previously flashed)

set -euo pipefail

HARDWARE_DIR="hardware"

# --- Verify shared files exist ---
for f in "$HARDWARE_DIR/shared/packet.py" "$HARDWARE_DIR/shared/code.py"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: required file '$f' not found. Run from repo root."
        exit 1
    fi
done

# --- Discover transmitter types ---
TX_DIRS=()
for d in "$HARDWARE_DIR"/*-transmitter/; do
    [ -d "$d" ] && TX_DIRS+=("$d")
done
if [ ${#TX_DIRS[@]} -eq 0 ]; then
    echo "ERROR: no *-transmitter/ directories found under $HARDWARE_DIR/."
    exit 1
fi

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
DETECTED=""
if [ -f "${MOUNT}sensors.py" ]; then
    # sensors.py only lives in transmitter dirs — figure out which one
    for d in "${TX_DIRS[@]}"; do
        tx_name=$(basename "$d")
        DETECTED="$tx_name"
        break  # pick the first match; user confirms below
    done
elif [ -f "${MOUNT}code.py" ]; then
    DETECTED="receiver"
fi

ROLE=""
if [ -n "$DETECTED" ]; then
    echo "Detected existing firmware: $DETECTED"
    read -rp "Flash as $DETECTED? [Y/n]: " CONFIRM
    CONFIRM="${CONFIRM:-Y}"
    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
        ROLE="$DETECTED"
    fi
fi

if [ -z "$ROLE" ]; then
    echo "What would you like to flash to '$MOUNT'?"
    echo "  1) Receiver"
    i=2
    for d in "${TX_DIRS[@]}"; do
        tx_name=$(basename "$d")
        echo "  $i) $tx_name"
        i=$((i + 1))
    done
    read -rp "Enter choice (1-$((i - 1))): " CHOICE
    if [ "$CHOICE" = "1" ]; then
        ROLE="receiver"
    elif [ "$CHOICE" -ge 2 ] 2>/dev/null && [ "$CHOICE" -lt "$i" ]; then
        idx=$((CHOICE - 2))
        ROLE=$(basename "${TX_DIRS[$idx]}")
    else
        echo "ERROR: Invalid choice '$CHOICE'."
        exit 1
    fi
fi

# --- Build file list ---
if [ "$ROLE" = "receiver" ]; then
    SRC_DIR="$HARDWARE_DIR/receiver"
    FILES=("code.py" "config.py")
    SHARED_FILES=("packet.py")
else
    SRC_DIR="$HARDWARE_DIR/$ROLE"
    FILES=("sensors.py" "config.py")
    SHARED_FILES=("packet.py" "code.py")
fi

# --- Flash ---
echo ""
echo "Flashing $ROLE -> $MOUNT"
for FILE in "${FILES[@]}"; do
    SRC="$SRC_DIR/$FILE"
    if [ ! -f "$SRC" ]; then
        echo "  WARNING: source file '$SRC' not found — skipping."
        continue
    fi
    cp "$SRC" "${MOUNT}${FILE}"
    echo "  $FILE"
done
for FILE in "${SHARED_FILES[@]}"; do
    SRC="$HARDWARE_DIR/shared/$FILE"
    if [ ! -f "$SRC" ]; then
        echo "  WARNING: source file '$SRC' not found — skipping."
        continue
    fi
    cp "$SRC" "${MOUNT}${FILE}"
    echo "  $FILE (shared)"
done

echo ""
echo "Done."

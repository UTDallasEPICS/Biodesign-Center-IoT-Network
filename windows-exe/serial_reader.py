import time

import serial
import serial.tools.list_ports

from hex_parse import decode_lora


def scan_ports(log_fn):
    """Scan COM ports. Returns (confident_device, candidates) where confident_device is a
    string if an RP2040/CircuitPython/Adafruit device is found, else None, and candidates
    is a list of non-Bluetooth port objects when no confident match exists."""
    ports = serial.tools.list_ports.comports()
    log_fn(f"Found {len(ports)} COM port(s)")
    for port in ports:
        log_fn(f"  {port.device}: {port.description} (mfr: {port.manufacturer})")
        if "RP2040" in (port.description or "") or "CircuitPython" in (port.description or "") or "Adafruit" in (port.manufacturer or ""):
            log_fn(f"  -> {port.device} matched as receiver")
            return port.device, []
    candidates = [p for p in ports if "Bluetooth" not in (p.description or "")]
    return None, candidates


def read_from_receiver(log_fn, stop_event, port, packet_queue):
    """Read LoRa packets from the receiver via USB serial. Decoded packets are put onto packet_queue."""

    if not port:
        log_fn("Receiver not found. Check USB connection.")
        return

    ser = None
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        log_fn(f"Connected to {port}")

        while not stop_event.is_set() and ser.is_open:
            try:
                if ser.in_waiting:
                    raw = ser.readline()
                    line = raw.decode('utf-8', errors='ignore').strip()

                    if not line:
                        continue

                    if line.startswith("["):
                        log_fn(f"Serial: {line}")
                        continue

                    log_fn(f"Raw hex: {line}")

                    hex_str = line.replace(" ", "").upper()

                    try:
                        decoded = decode_lora(hex_str)
                        log_fn(f"Decoded: {decoded}")
                        packet_queue.put(decoded)
                    except Exception as e:
                        log_fn(f"Decode exception: {e}")
                else:
                    time.sleep(0.1)

            except Exception as e:
                log_fn(f"Read error: {e}")
                time.sleep(1)

    except serial.SerialException as e:
        log_fn(f"Connection failed: {e}")
    finally:
        if ser:
            ser.close()
        log_fn("Stopped")

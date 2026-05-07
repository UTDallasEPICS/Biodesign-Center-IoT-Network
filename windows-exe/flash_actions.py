import os
import shutil

from flash_compose import compose_config_py, compose_sensors_py
from flash_paths import LIBRARIES_DIR, RECEIVER_DIR, SHARED_DIR
from storage import id_in_use


def scan_drives():
    """Check A:-Z: for boot_out.txt (CircuitPython board marker). Returns list of letters."""
    found = []
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZABC":
        path = "{}:/".format(letter)
        try:
            if os.path.isfile(os.path.join(path, "boot_out.txt")):
                found.append(letter)
        except OSError:
            pass
    return found


def _copy_libraries(mount, lib_names, log_fn):
    """Copy named libraries from hardware/libraries/ to {mount}lib/."""
    if not lib_names:
        return

    lib_dest = os.path.join(mount, "lib")
    os.makedirs(lib_dest, exist_ok=True)

    for lib_name in sorted(lib_names):
        src = os.path.join(LIBRARIES_DIR, lib_name)
        dst = os.path.join(lib_dest, lib_name)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            log_fn("  lib/{} (library dir)".format(lib_name))
        elif os.path.isfile(src):
            shutil.copy2(src, dst)
            log_fn("  lib/{} (library)".format(lib_name))
        else:
            log_fn("  WARNING: library '{}' not found in hardware/libraries/ — skipped".format(lib_name))


def flash_transmitter(mount, lab_id, node_id, sensors, log_fn, on_success=None):
    """Generate and copy all transmitter files to the board.

    on_success is called with no arguments after a successful flash (from the
    calling thread). The caller is responsible for marshalling to the GUI thread
    if needed.
    """
    try:
        config_code = compose_config_py(lab_id, node_id, sensors)
        sensors_code = compose_sensors_py(sensors)

        config_path = os.path.join(mount, "config.py")
        with open(config_path, "w", newline="\n") as f:
            f.write(config_code)
        log_fn("  config.py (generated)")

        sensors_path = os.path.join(mount, "sensors.py")
        with open(sensors_path, "w", newline="\n") as f:
            f.write(sensors_code)
        log_fn("  sensors.py (generated)")

        for fname in ("packet.py", "code.py"):
            src = os.path.join(SHARED_DIR, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(mount, fname))
                log_fn("  {} (shared)".format(fname))
            else:
                log_fn("  WARNING: {} not found — skipped".format(src))

        # Collect all required libraries: base radio lib + sensor-specific
        needed = {"adafruit_rfm9x.mpy"}
        for sensor in sensors:
            for lib in sensor["template"]["libraries"]:
                needed.add(lib)
        _copy_libraries(mount, needed, log_fn)

        log_fn("")
        log_fn("Flash complete.")
        if on_success:
            on_success()
    except Exception as e:
        log_fn("ERROR: {}".format(e))


def flash_receiver(mount, log_fn):
    """Copy receiver firmware files to the board."""
    try:
        for fname in ("code.py", "config.py"):
            src = os.path.join(RECEIVER_DIR, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(mount, fname))
                log_fn("  {}".format(fname))
            else:
                log_fn("  WARNING: {} not found — skipped".format(src))

        src = os.path.join(SHARED_DIR, "packet.py")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(mount, "packet.py"))
            log_fn("  packet.py (shared)")
        else:
            log_fn("  WARNING: packet.py not found — skipped")

        _copy_libraries(mount, {"adafruit_rfm9x.mpy"}, log_fn)

        log_fn("")
        log_fn("Flash complete.")
    except Exception as e:
        log_fn("ERROR: {}".format(e))


def check_transmitter_id_status(remembered, flashed, lab_id, node_id):
    """Classify a (lab_id, node_id) for the pre-flash uniqueness check.

    Returns (status, existing_name):
      "free"     — id is unused; proceed and prompt for a name after flash
      "reflash"  — id is known and has flash history; caller should confirm
      "blocked"  — id is known but has no flash history; caller should error

    existing_name is the remembered name (or None) for display in either case.
    """
    existing_name = remembered.get("{},{}".format(lab_id, node_id), {}).get("name")

    if not id_in_use(remembered, lab_id, node_id):
        return "free", existing_name

    has_history = any(
        r.get("lab_id") == lab_id and r.get("node_id") == node_id
        for r in flashed
    )
    return ("reflash" if has_history else "blocked"), existing_name

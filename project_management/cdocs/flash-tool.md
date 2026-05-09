# Flash Tool Context: Biodesign Center IoT Network

The Flash Device tab (`windows-exe/flash_tab.py`) in the Tkinter GUI and the shell scripts (`flash.sh` / `flash.bat`) flash firmware onto CircuitPython boards via file copy. The GUI version adds sensor composition and library management on top of what the shell scripts do.

---

## File Layout

| File | Responsibility |
|------|---------------|
| `flash_tab.py` | Template parser, code composer, drive scanner, flash logic, and `FlashTab` GUI class. |
| `flash.sh` | Interactive shell script. Detects OS, asks for mount point and role, copies firmware files. No sensor composition or library copying. |
| `flash.bat` | Windows wrapper. Finds Git Bash or WSL and delegates to `flash.sh`. |

---

## Sensor Templates (`hardware/sensor_templates/`)

Human-readable code files that define individual sensor types. Each file contains structured comment headers (name, channel, trigger, libraries, params) and three code sections (imports, setup, read). The Flash Device tab auto-discovers all `.py` files in this directory and composes them into a complete `sensors.py` when flashing a transmitter.

### File Format

A template has two parts: **structured comment headers** and **code sections** separated by `# --- <section> ---` markers.

```
# --- Sensor Template ---
# name: Display Name
# channel: channel_name
# trigger: edge|none
# libraries: lib1.mpy, lib2/
#
# param: key | Label | pin|percent | default

# --- imports ---
<import lines, excluding `import board` which is always added>

# --- setup ---
<hardware init: pin objects, bus init, constants>

# --- read ---
def read_<channel>():
    return <value>
```

### Header Fields

| Field | Purpose |
|-------|---------|
| `name` | Display label in the GUI sensor picker |
| `channel` | Channel key used in `READERS`, `TRIGGER_TYPE`, and `config.py` SENSORS list |
| `trigger` | `edge` (added to TRIGGER_TYPE) or `none` (omitted) |
| `libraries` | Comma-separated entries from `hardware/libraries/` to copy to the board |
| `param` | One line per configurable parameter: `key | Label | type | default` |

### Param Types

- `pin` — dropdown of board pins (D0–D25, A0–A3)
- `percent` — spinbox 0–100, substituted as an integer
- `number` — free-entry text field, substituted as-is (supports integers and floats)
- `boolean` — checkbox, substituted as `True` or `False`

### Composition Rules

When multiple sensors are selected, the composer:

1. Collects all `# --- imports ---` blocks and deduplicates identical lines.
2. Always prepends `import board`.
3. Concatenates `# --- setup ---` blocks, deduplicating identical lines (handles shared `_i2c = board.I2C()` when multiple I2C sensors are present).
4. Concatenates `# --- read ---` blocks.
5. Generates `READERS` dict mapping each channel to its `read_<channel>` function.
6. Generates `TRIGGER_TYPE` dict for channels with `trigger: edge`.

### Conventions for Template Authors

- Use unique variable names per sensor (e.g. `ds18_sensor`, `tsl_sensor`, not `sensor`).
- I2C sensors use `_i2c = board.I2C()` as the shared init line — the composer deduplicates it.
- The read function must be named `read_<channel>()`.
- Code must be valid CircuitPython (no f-strings, use `.format()`).
- `{param_key}` placeholders in setup/read are substituted with user-chosen values.

---

## CircuitPython Libraries (`hardware/libraries/`)

Pre-downloaded `.mpy` library files and directories from the [CircuitPython bundle](https://circuitpython.org/libraries). The Flash Device tab copies required libraries to the board's `lib/` folder based on which sensors are configured. `adafruit_rfm9x.mpy` is always copied for both transmitters and receivers (required by the radio driver in `code.py`).

---

## Flash Process

### Transmitter (GUI)

1. **Pre-flash uniqueness check.** If `(lab_id, node_id)` is already in `remembered_nodes`:
   - With prior flash history → confirm "Re-flash existing node 'X' (Lab L, Node N)?" and proceed only on Yes.
   - With no flash history → block with an error pointing at Forget in the Node Pairing tab.
2. Generate `config.py` from Lab ID, Node ID, and sensor channel list.
3. Generate `sensors.py` by composing selected sensor templates with user-chosen parameters.
4. Copy `hardware/shared/packet.py` and `hardware/shared/code.py` to the board.
5. Copy `adafruit_rfm9x.mpy` plus each sensor's declared libraries from `hardware/libraries/` to `{mount}lib/`.
6. On success, show a name dialog. **Name is required and must be unique** across `flashed_nodes` (case-insensitive). Re-flashes pre-fill the existing name and exempt that `(lab_id, node_id)` from the uniqueness check so the prior name can be kept. Save calls `ReceiverApp.record_flash(lab_id, node_id, name, sensors)`, which appends a record to `flashed_nodes` containing: `lab_id`, `node_id`, `name`, `flashed_at` (ISO timestamp), and `sensors` (list of `{channel, template_name, params}`). The full sensor config is stored so the node can be re-flashed identically.

### Re-flash (from Known Flashes tab)

`KnownFlashesTab` lists every saved flash record. The Re-flash button calls `FlashTab.load_from_flash_record(record)`, which:
- switches the role to transmitter,
- sets `lab_id_var` and `node_id_var`,
- rebuilds the sensor list by matching each `template_name` back to a parsed template (missing templates are skipped with a warning),
- focuses the Flash Device tab so the user can pick a drive and click Flash.

The Delete button on the same tab removes only the saved record (the node remains in `remembered_nodes` if it was ever discovered).

### Receiver (GUI)

1. Copy `hardware/receiver/code.py` and `hardware/receiver/config.py` to the board.
2. Copy `hardware/shared/packet.py` to the board.
3. Copy `adafruit_rfm9x.mpy` from `hardware/libraries/` to `{mount}lib/`.

### Shell Script (`flash.sh`)

1. Detect OS and ask for mount point.
2. Auto-detect role from existing files on the board, or ask user.
3. Copy role-specific files plus shared files. No library copying or code generation.

---

## Drive Detection

`scan_drives()` checks drive letters D–Z (then A–C) for a `boot_out.txt` file, which CircuitPython boards write on mount. The first match is auto-filled in the drive entry field. The user can override manually.

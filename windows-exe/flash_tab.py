import os
import re
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime


# Board pin options for Adafruit Feather RP2040
BOARD_PINS = [
    "D0", "D1", "D4", "D5", "D6", "D9", "D10", "D11", "D12", "D13",
    "D24", "D25", "A0", "A1", "A2", "A3",
]

# Paths: when frozen by PyInstaller, bundled data lives under sys._MEIPASS;
# otherwise resolve relative to the repo root (one level up from windows-exe/).
if getattr(sys, "frozen", False):
    _DATA_ROOT = sys._MEIPASS
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))

_TEMPLATES_DIR = os.path.join(_DATA_ROOT, "hardware", "sensor_templates")
_SHARED_DIR = os.path.join(_DATA_ROOT, "hardware", "shared")
_RECEIVER_DIR = os.path.join(_DATA_ROOT, "hardware", "receiver")
_LIBRARIES_DIR = os.path.join(_DATA_ROOT, "hardware", "libraries")


# ---------------------------------------------------------------------------
# Template parser
# ---------------------------------------------------------------------------

def parse_template(filepath):
    """Parse a sensor template file into metadata and code sections."""
    with open(filepath, "r") as f:
        text = f.read()

    meta = {
        "filepath": filepath,
        "name": "",
        "channel": "",
        "trigger": "none",
        "libraries": [],
        "params": [],
    }

    # Parse structured comment headers
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "# --- imports ---":
            break
        m = re.match(r"#\s*name:\s*(.+)", stripped)
        if m:
            meta["name"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*channel:\s*(.+)", stripped)
        if m:
            meta["channel"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*trigger:\s*(.+)", stripped)
        if m:
            meta["trigger"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*libraries:\s*(.*)", stripped)
        if m:
            libs = m.group(1).strip()
            meta["libraries"] = [l.strip() for l in libs.split(",") if l.strip()] if libs else []
            continue
        m = re.match(r"#\s*param:\s*(.+)", stripped)
        if m:
            parts = [p.strip() for p in m.group(1).split("|")]
            if len(parts) == 4:
                meta["params"].append({
                    "key": parts[0],
                    "label": parts[1],
                    "type": parts[2],
                    "default": parts[3],
                })

    # Parse code sections delimited by "# --- <name> ---"
    sections = {"imports": "", "setup": "", "read": ""}
    current = None
    lines_buf = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "# --- imports ---":
            current = "imports"
            lines_buf = []
            continue
        elif stripped == "# --- setup ---":
            if current is not None:
                sections[current] = "\n".join(lines_buf).strip()
            current = "setup"
            lines_buf = []
            continue
        elif stripped == "# --- read ---":
            if current is not None:
                sections[current] = "\n".join(lines_buf).strip()
            current = "read"
            lines_buf = []
            continue

        if current is not None:
            lines_buf.append(line)

    if current is not None:
        sections[current] = "\n".join(lines_buf).strip()

    meta["sections"] = sections
    return meta


def discover_templates():
    """Scan hardware/sensor_templates/ and return a list of parsed templates."""
    if not os.path.isdir(_TEMPLATES_DIR):
        return []
    templates = []
    for fname in sorted(os.listdir(_TEMPLATES_DIR)):
        if fname.endswith(".py"):
            try:
                templates.append(parse_template(os.path.join(_TEMPLATES_DIR, fname)))
            except Exception:
                pass
    return templates


# ---------------------------------------------------------------------------
# Code composer
# ---------------------------------------------------------------------------

def compose_sensors_py(sensors):
    """Build a complete sensors.py from a list of configured sensors.

    Each entry: {"template": parsed_template, "param_values": {key: value}}
    """
    all_imports = []
    seen_imports = set()
    setup_lines = []
    seen_setup = set()
    read_blocks = []
    channels = []
    trigger_types = {}

    for sensor in sensors:
        tmpl = sensor["template"]
        params = sensor["param_values"]
        channel = tmpl["channel"]
        channels.append(channel)

        # Substitute {param} placeholders in each section
        imports_text = tmpl["sections"]["imports"]
        setup_text = tmpl["sections"]["setup"]
        read_text = tmpl["sections"]["read"]

        for key, val in params.items():
            placeholder = "{" + key + "}"
            imports_text = imports_text.replace(placeholder, str(val))
            setup_text = setup_text.replace(placeholder, str(val))
            read_text = read_text.replace(placeholder, str(val))

        # Collect imports (deduplicate, preserve order)
        for line in imports_text.splitlines():
            stripped = line.strip()
            if stripped and stripped not in seen_imports:
                all_imports.append(stripped)
                seen_imports.add(stripped)

        # Collect setup lines (deduplicate identical lines for shared resources)
        for line in setup_text.splitlines():
            stripped = line.strip()
            if stripped and stripped not in seen_setup:
                setup_lines.append(line)
                seen_setup.add(stripped)

        read_blocks.append(read_text)

        if tmpl["trigger"] == "edge":
            trigger_types[channel] = "edge"

    # Assemble the file
    parts = []
    parts.append("# sensors.py")
    parts.append("# Generated by Flash Device tab")
    parts.append("#")
    for ch in channels:
        parts.append("#   read_{}()".format(ch))

    parts.append("")
    parts.append("import board")
    for imp in all_imports:
        parts.append(imp)

    parts.append("")
    parts.append("# " + "-" * 75)
    parts.append("# Pin setup")
    parts.append("# " + "-" * 75)
    parts.append("")
    parts.extend(setup_lines)

    parts.append("")
    parts.append("")
    parts.append("# " + "-" * 75)
    parts.append("# Public interface")
    parts.append("# " + "-" * 75)
    parts.append("")
    parts.append("\n\n".join(read_blocks))

    parts.append("")
    parts.append("")
    parts.append("# " + "-" * 75)
    parts.append("# Generic interface for shared/code.py")
    parts.append("# " + "-" * 75)
    parts.append("")
    parts.append("READERS = {")
    for ch in channels:
        parts.append("    \"{}\": read_{},".format(ch, ch))
    parts.append("}")
    parts.append("")
    parts.append("TRIGGER_TYPE = {")
    for ch in channels:
        if ch in trigger_types:
            parts.append("    \"{}\": \"{}\",".format(ch, trigger_types[ch]))
    parts.append("}")
    parts.append("")

    return "\n".join(parts)


def compose_config_py(lab_id, node_id, sensors):
    """Build a config.py from node identity and sensor list."""
    channels = [s["template"]["channel"] for s in sensors]
    sensor_entries = "\n".join(
        "    {{\"channel\": \"{}\"}},".format(ch) for ch in channels
    )

    return (
        "# =============================================================\n"
        "# Transmitter Node Configuration\n"
        "# Generated by Flash Device tab\n"
        "# =============================================================\n"
        "\n"
        "# --- Network Identity ---\n"
        "LAB_ID  = {lab:#04x}   # Physical lab this node belongs to (1-255, 0 reserved)\n"
        "NODE_ID = {node:#04x}   # Unique ID for this transmitter board (1-255)\n"
        "\n"
        "# --- Radio ---\n"
        "RADIO_FREQ_MHZ = 915.0\n"
        "TX_POWER       = 5\n"
        "RECEIVER_NODE  = 0x01\n"
        "ACK_RETRIES    = 3\n"
        "ACK_WAIT       = 0.5\n"
        "CSMA_DELAY_MAX = 0.1\n"
        "\n"
        "# --- Timing ---\n"
        "HEARTBEAT_INTERVAL = 30\n"
        "POLL_INTERVAL      = 1\n"
        "\n"
        "# --- Sensor Definitions ---\n"
        "SENSORS = [\n"
        "{entries}\n"
        "]\n"
    ).format(lab=lab_id, node=node_id, entries=sensor_entries)


# ---------------------------------------------------------------------------
# Drive scanning and flash logic
# ---------------------------------------------------------------------------

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
        src = os.path.join(_LIBRARIES_DIR, lib_name)
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
            src = os.path.join(_SHARED_DIR, fname)
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
            src = os.path.join(_RECEIVER_DIR, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(mount, fname))
                log_fn("  {}".format(fname))
            else:
                log_fn("  WARNING: {} not found — skipped".format(src))

        src = os.path.join(_SHARED_DIR, "packet.py")
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


# ---------------------------------------------------------------------------
# GUI — Flash Tab
# ---------------------------------------------------------------------------

class FlashTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.templates = discover_templates()
        self.sensors = []  # [{"template": ..., "param_values": {key: value}}, ...]

        # --- Role selection ---
        self.role_frame = tk.LabelFrame(self.frame, text="Role", font=("Arial", 10, "bold"))
        self.role_frame.pack(fill="x", padx=10, pady=(10, 4))

        self.role_var = tk.StringVar(value="transmitter")
        tk.Radiobutton(self.role_frame, text="Transmitter", variable=self.role_var,
                       value="transmitter", command=self._on_role_change).pack(side="left", padx=10)
        tk.Radiobutton(self.role_frame, text="Receiver", variable=self.role_var,
                       value="receiver", command=self._on_role_change).pack(side="left", padx=10)

        # --- Transmitter config ---
        self.tx_frame = tk.LabelFrame(self.frame, text="Transmitter Configuration",
                                      font=("Arial", 10, "bold"))
        self.tx_frame.pack(fill="both", expand=True, padx=10, pady=4)

        id_frame = tk.Frame(self.tx_frame)
        id_frame.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(id_frame, text="Lab ID (1-255):", font=("Arial", 9)).pack(side="left")
        self.lab_id_var = tk.IntVar(value=1)
        tk.Spinbox(id_frame, from_=1, to=255, textvariable=self.lab_id_var,
                   width=5, font=("Arial", 9)).pack(side="left", padx=(4, 16))

        tk.Label(id_frame, text="Node ID (1-255):", font=("Arial", 9)).pack(side="left")
        self.node_id_var = tk.IntVar(value=1)
        tk.Spinbox(id_frame, from_=1, to=255, textvariable=self.node_id_var,
                   width=5, font=("Arial", 9)).pack(side="left", padx=4)

        sensor_header = tk.Frame(self.tx_frame)
        sensor_header.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(sensor_header, text="Sensors", font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(sensor_header, text="+ Add Sensor", command=self._add_sensor_dialog,
                  bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(side="right")

        sensor_container = tk.Frame(self.tx_frame)
        sensor_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.sensor_canvas = tk.Canvas(sensor_container, bg="#f5f5f5",
                                       highlightthickness=0, height=100)
        sensor_sb = tk.Scrollbar(sensor_container, orient="vertical",
                                 command=self.sensor_canvas.yview)
        self.sensor_list_frame = tk.Frame(self.sensor_canvas, bg="#f5f5f5")

        self.sensor_list_frame.bind(
            "<Configure>",
            lambda e: self.sensor_canvas.configure(scrollregion=self.sensor_canvas.bbox("all")),
        )
        self.sensor_canvas.create_window((0, 0), window=self.sensor_list_frame, anchor="nw")
        self.sensor_canvas.configure(yscrollcommand=sensor_sb.set)

        sensor_sb.pack(side="right", fill="y")
        self.sensor_canvas.pack(side="left", fill="both", expand=True)

        self.sensor_rows = []

        # --- Drive / actions ---
        self.drive_frame = tk.LabelFrame(self.frame, text="Target Drive",
                                         font=("Arial", 10, "bold"))
        self.drive_frame.pack(fill="x", padx=10, pady=4)

        drive_inner = tk.Frame(self.drive_frame)
        drive_inner.pack(fill="x", padx=8, pady=8)

        tk.Label(drive_inner, text="Drive letter:", font=("Arial", 9)).pack(side="left")
        self.drive_var = tk.StringVar(value="")
        tk.Entry(drive_inner, textvariable=self.drive_var, width=4,
                 font=("Consolas", 10)).pack(side="left", padx=4)
        tk.Button(drive_inner, text="Scan", command=self._scan_drives,
                  font=("Arial", 9)).pack(side="left", padx=4)

        tk.Button(drive_inner, text="Preview Code", command=self._preview_code,
                  font=("Arial", 9, "bold")).pack(side="right", padx=4)
        tk.Button(drive_inner, text="Flash", command=self._flash,
                  bg="#2196F3", fg="white", font=("Arial", 10, "bold"),
                  width=10).pack(side="right", padx=4)

        # --- Status log ---
        self.log_frame = tk.LabelFrame(self.frame, text="Status", font=("Arial", 10, "bold"))
        self.log_frame.pack(fill="x", padx=10, pady=(4, 10))

        self.log_text = tk.Text(self.log_frame, font=("Consolas", 9), state="disabled",
                                wrap="word", bg="#1e1e1e", fg="#cccccc", height=6)
        log_sb = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True, padx=4, pady=4)

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", "[{}] {}\n".format(timestamp, msg))
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.app.root.after(0, _append)

    def _on_role_change(self):
        if self.role_var.get() == "receiver":
            self.tx_frame.pack_forget()
        else:
            self.tx_frame.pack(fill="both", expand=True, padx=10, pady=4,
                               after=self.role_frame)

    def _refresh_sensor_list(self):
        """Rebuild the visible sensor rows from self.sensors."""
        for row_info in self.sensor_rows:
            row_info["frame"].destroy()
        self.sensor_rows.clear()

        for i, sensor in enumerate(self.sensors):
            tmpl = sensor["template"]
            params = sensor["param_values"]

            row = tk.Frame(self.sensor_list_frame, bg="#ffffff", relief="groove", bd=1)
            row.pack(fill="x", padx=2, pady=2)

            param_parts = []
            for p in tmpl["params"]:
                val = params.get(p["key"], p["default"])
                if p["type"] == "percent":
                    param_parts.append("{}: {}%".format(p["label"], val))
                else:
                    param_parts.append("{}: {}".format(p["label"], val))

            label_text = tmpl["name"]
            if param_parts:
                label_text += "  ({})".format(", ".join(param_parts))

            tk.Label(row, text=label_text, font=("Consolas", 9),
                     bg="#ffffff", anchor="w").pack(side="left", padx=(8, 4), fill="x", expand=True)

            tk.Button(row, text="Remove", fg="#f44336", font=("Arial", 8),
                      command=lambda idx=i: self._remove_sensor(idx)).pack(
                side="right", padx=4, pady=2)

            self.sensor_rows.append({"frame": row})

    def _remove_sensor(self, idx):
        del self.sensors[idx]
        self._refresh_sensor_list()

    # -------------------------------------------------------------------
    # Add Sensor dialog
    # -------------------------------------------------------------------

    def _add_sensor_dialog(self):
        if not self.templates:
            self.log("No sensor templates found in hardware/sensor_templates/")
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title("Add Sensor")
        dialog.geometry("420x360")
        dialog.grab_set()

        tk.Label(dialog, text="Select sensor type:",
                 font=("Arial", 10, "bold")).pack(pady=(12, 4))

        listbox = tk.Listbox(dialog, font=("Consolas", 10), selectmode="single",
                             height=min(len(self.templates), 6))
        for tmpl in self.templates:
            listbox.insert("end", tmpl["name"])
        listbox.select_set(0)
        listbox.pack(padx=16, fill="x")

        param_frame = tk.LabelFrame(dialog, text="Parameters", font=("Arial", 9, "bold"))
        param_frame.pack(fill="x", padx=16, pady=(8, 4))

        param_widgets = {}

        def on_type_select(event=None):
            for w in param_frame.winfo_children():
                w.destroy()
            param_widgets.clear()

            sel = listbox.curselection()
            if not sel:
                return
            tmpl = self.templates[sel[0]]

            if not tmpl["params"]:
                tk.Label(param_frame, text="No configurable parameters",
                         font=("Arial", 9), fg="#888888").pack(pady=4)
                return

            for p in tmpl["params"]:
                row = tk.Frame(param_frame)
                row.pack(fill="x", padx=8, pady=2)
                tk.Label(row, text="{}:".format(p["label"]),
                         font=("Arial", 9)).pack(side="left")

                if p["type"] == "pin":
                    var = tk.StringVar(value=p["default"])
                    ttk.Combobox(row, textvariable=var, values=BOARD_PINS,
                                 width=6, font=("Consolas", 9),
                                 state="readonly").pack(side="right", padx=4)
                    param_widgets[p["key"]] = var
                elif p["type"] == "percent":
                    var = tk.IntVar(value=int(p["default"]))
                    tk.Spinbox(row, from_=0, to=100, textvariable=var,
                               width=5, font=("Arial", 9)).pack(side="right", padx=4)
                    param_widgets[p["key"]] = var

        listbox.bind("<<ListboxSelect>>", on_type_select)
        on_type_select()

        error_var = tk.StringVar(value="")
        tk.Label(dialog, textvariable=error_var, fg="red",
                 font=("Arial", 9)).pack(pady=(0, 2))

        def on_add():
            sel = listbox.curselection()
            if not sel:
                return
            tmpl = self.templates[sel[0]]

            for existing in self.sensors:
                if existing["template"]["channel"] == tmpl["channel"]:
                    error_var.set("Channel '{}' is already added.".format(tmpl["channel"]))
                    return

            values = {key: var.get() for key, var in param_widgets.items()}
            self.sensors.append({"template": tmpl, "param_values": values})
            self._refresh_sensor_list()
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Add", command=on_add, bg="#4CAF50", fg="white",
                  font=("Arial", 9, "bold"), width=8).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                  font=("Arial", 9), width=8).pack(side="left", padx=6)

        dialog.wait_window()

    # -------------------------------------------------------------------
    # Drive scan
    # -------------------------------------------------------------------

    def _scan_drives(self):
        self.log("Scanning for CircuitPython boards...")
        found = scan_drives()
        if found:
            self.drive_var.set(found[0])
            self.log("Found board(s): {}".format(
                ", ".join("{}:".format(d) for d in found)))
        else:
            self.log("No CircuitPython boards found (no boot_out.txt detected).")

    # -------------------------------------------------------------------
    # Code preview
    # -------------------------------------------------------------------

    def _preview_code(self):
        if self.role_var.get() == "receiver":
            self.log("Receiver uses existing firmware files — nothing to preview.")
            return

        if not self.sensors:
            self.log("Add at least one sensor to preview generated code.")
            return

        lab_id = self.lab_id_var.get()
        node_id = self.node_id_var.get()
        config_code = compose_config_py(lab_id, node_id, self.sensors)
        sensors_code = compose_sensors_py(self.sensors)

        preview = tk.Toplevel(self.app.root)
        preview.title("Code Preview")
        preview.geometry("600x500")

        nb = ttk.Notebook(preview)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        for title, code in [("config.py", config_code), ("sensors.py", sensors_code)]:
            tab = ttk.Frame(nb)
            nb.add(tab, text="  {}  ".format(title))

            text_w = tk.Text(tab, font=("Consolas", 9), wrap="none",
                             bg="#1e1e1e", fg="#cccccc")
            text_w.insert("1.0", code)
            text_w.config(state="disabled")

            ysb = tk.Scrollbar(tab, orient="vertical", command=text_w.yview)
            xsb = tk.Scrollbar(tab, orient="horizontal", command=text_w.xview)
            text_w.config(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

            ysb.pack(side="right", fill="y")
            xsb.pack(side="bottom", fill="x")
            text_w.pack(fill="both", expand=True)

    # -------------------------------------------------------------------
    # Post-flash name dialog
    # -------------------------------------------------------------------

    def _show_name_dialog(self, lab_id, node_id, sensors):
        """Prompt the user to name the freshly flashed node. Always records the flash."""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Name This Node")
        dialog.geometry("360x160")
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Flash complete — Lab {}, Node {}".format(lab_id, node_id),
            font=("Arial", 10, "bold"),
        ).pack(pady=(14, 4))
        tk.Label(dialog, text="Give this node a name? (optional)", font=("Arial", 9)).pack()

        name_var = tk.StringVar()
        name_entry = tk.Entry(dialog, textvariable=name_var, font=("Arial", 10), width=26)
        name_entry.pack(pady=(6, 10))
        name_entry.focus_set()

        def commit(name):
            dialog.destroy()
            self.app.record_flash(lab_id, node_id, name or None, sensors)

        name_entry.bind("<Return>", lambda _e: commit(name_var.get().strip()))

        btn_frame = tk.Frame(dialog)
        btn_frame.pack()
        tk.Button(
            btn_frame, text="Save", font=("Arial", 9, "bold"), bg="#4CAF50", fg="white", width=8,
            command=lambda: commit(name_var.get().strip()),
        ).pack(side="left", padx=6)
        tk.Button(
            btn_frame, text="Skip", font=("Arial", 9), width=8,
            command=lambda: commit(None),
        ).pack(side="left", padx=6)

        dialog.wait_window()

    # -------------------------------------------------------------------
    # Flash
    # -------------------------------------------------------------------

    def _flash(self):
        drive = self.drive_var.get().strip().upper()
        if not drive:
            self.log("Enter a drive letter first.")
            return

        drive = drive.rstrip(":\\/")
        mount = "{}:/".format(drive)

        if not os.path.isdir(mount):
            self.log("Drive {}: is not accessible.".format(drive))
            return

        role = self.role_var.get()

        if role == "transmitter":
            if not self.sensors:
                self.log("Add at least one sensor before flashing.")
                return
            lab_id = self.lab_id_var.get()
            node_id = self.node_id_var.get()
            sensors_snapshot = list(self.sensors)
            self.log("Flashing transmitter (Lab {}, Node {}) -> {}".format(
                lab_id, node_id, mount))

            def on_success():
                self.app.root.after(0, lambda: self._show_name_dialog(lab_id, node_id, sensors_snapshot))

            threading.Thread(
                target=flash_transmitter,
                args=(mount, lab_id, node_id, sensors_snapshot, self.log, on_success),
                daemon=True,
            ).start()
        else:
            self.log("Flashing receiver -> {}".format(mount))
            threading.Thread(
                target=flash_receiver,
                args=(mount, self.log),
                daemon=True,
            ).start()

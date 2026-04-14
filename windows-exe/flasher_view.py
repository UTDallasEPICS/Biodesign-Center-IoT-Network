# flasher_view.py
# Sensor Flasher tab for the Biodesign IoT Network host application.
# Lets the user configure a transmitter node (lab/node ID, sensors with
# per-channel parameters) and flash the generated firmware to a mounted
# CircuitPython board, saving to the repo as well.

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from sensor_defs import CHANNEL_DEFS
from firmware_gen import (
    generate_config,
    generate_sensors,
    flash_to_board,
    save_to_repo,
    list_transmitter_types,
    load_transmitter_config,
)


class FlasherView(tk.Frame):
    """Sensor flashing tab — configure and flash transmitter firmware."""

    def __init__(self, parent):
        super().__init__(parent)
        self.sensor_cards = []  # list of _SensorCard instances

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Outer container with scrollbar
        outer = tk.Frame(self)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Bind mousewheel to scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._canvas = canvas

        container = self._scroll_frame

        # --- Load existing transmitter ---
        load_frame = tk.LabelFrame(container, text="Load Existing", padx=10, pady=6)
        load_frame.pack(fill="x", padx=10, pady=(10, 4))

        self._tx_types = list_transmitter_types()
        self._load_var = tk.StringVar(value="(new)")
        choices = ["(new)"] + self._tx_types
        tk.Label(load_frame, text="Transmitter:").pack(side="left")
        self._load_menu = ttk.Combobox(
            load_frame, textvariable=self._load_var, values=choices,
            state="readonly", width=28,
        )
        self._load_menu.pack(side="left", padx=(6, 8))
        tk.Button(load_frame, text="Load", command=self._load_existing).pack(side="left")

        # --- Node configuration ---
        node_frame = tk.LabelFrame(container, text="Node Configuration", padx=10, pady=6)
        node_frame.pack(fill="x", padx=10, pady=4)

        row = tk.Frame(node_frame)
        row.pack(fill="x", pady=2)
        tk.Label(row, text="Lab ID (1-255):").pack(side="left")
        self._lab_id_var = tk.IntVar(value=1)
        tk.Spinbox(row, from_=1, to=255, textvariable=self._lab_id_var, width=6).pack(side="left", padx=(4, 16))
        tk.Label(row, text="Node ID (1-255):").pack(side="left")
        self._node_id_var = tk.IntVar(value=1)
        tk.Spinbox(row, from_=1, to=255, textvariable=self._node_id_var, width=6).pack(side="left", padx=4)

        # --- Sensors ---
        sensor_header = tk.Frame(container)
        sensor_header.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(sensor_header, text="Sensors", font=("Arial", 10, "bold")).pack(side="left")

        # Add sensor dropdown
        self._add_sensor_var = tk.StringVar()
        channel_labels = [CHANNEL_DEFS[ch]["label"] for ch in CHANNEL_DEFS]
        self._channel_keys = list(CHANNEL_DEFS.keys())
        self._add_combo = ttk.Combobox(
            sensor_header, textvariable=self._add_sensor_var,
            values=channel_labels, state="readonly", width=30,
        )
        self._add_combo.pack(side="right", padx=(4, 0))
        tk.Button(sensor_header, text="+ Add Sensor", command=self._add_sensor).pack(side="right")

        # Container for sensor cards
        self._cards_frame = tk.Frame(container)
        self._cards_frame.pack(fill="x", padx=10, pady=4)

        # --- Transmitter name (for saving to repo) ---
        name_frame = tk.LabelFrame(container, text="Transmitter Name (for repo save)", padx=10, pady=6)
        name_frame.pack(fill="x", padx=10, pady=4)
        self._tx_name_var = tk.StringVar(value="my-transmitter")
        tk.Label(name_frame, text="hardware/").pack(side="left")
        tk.Entry(name_frame, textvariable=self._tx_name_var, width=24).pack(side="left")
        tk.Label(name_frame, text="/").pack(side="left")

        # --- Flash target ---
        flash_frame = tk.LabelFrame(container, text="Flash Target", padx=10, pady=6)
        flash_frame.pack(fill="x", padx=10, pady=4)

        mount_row = tk.Frame(flash_frame)
        mount_row.pack(fill="x", pady=2)
        tk.Label(mount_row, text="Drive letter:").pack(side="left")
        self._drive_var = tk.StringVar(value="D")
        tk.Entry(mount_row, textvariable=self._drive_var, width=4).pack(side="left", padx=4)
        tk.Label(mount_row, text="(e.g. D, E, F \u2014 the CircuitPython board drive)").pack(side="left", padx=4)

        # --- Action buttons ---
        btn_frame = tk.Frame(container)
        btn_frame.pack(fill="x", padx=10, pady=(8, 4))

        self._save_btn = tk.Button(
            btn_frame, text="Save to Repo", command=self._do_save,
            bg="#2196F3", fg="white", font=("Arial", 10, "bold"), width=16, padx=8,
        )
        self._save_btn.pack(side="left", padx=(0, 8))

        self._flash_btn = tk.Button(
            btn_frame, text="Flash to Board", command=self._do_flash,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=16, padx=8,
        )
        self._flash_btn.pack(side="left", padx=(0, 8))

        self._save_and_flash_btn = tk.Button(
            btn_frame, text="Save + Flash", command=self._do_save_and_flash,
            bg="#FF9800", fg="white", font=("Arial", 10, "bold"), width=16, padx=8,
        )
        self._save_and_flash_btn.pack(side="left")

        # --- Log area ---
        log_frame = tk.LabelFrame(container, text="Log", padx=4, pady=4)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self._log_text = tk.Text(
            log_frame, font=("Consolas", 9), state="disabled", wrap="word",
            bg="#1e1e1e", fg="#cccccc", height=8,
        )
        log_scroll = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"[{timestamp}] {msg}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    # ------------------------------------------------------------------
    # Sensor card management
    # ------------------------------------------------------------------

    def _add_sensor(self, channel=None, params=None):
        """Add a sensor card. If channel is None, reads from the dropdown."""
        if channel is None:
            idx = self._add_combo.current()
            if idx < 0:
                self._log("Select a sensor type from the dropdown first.")
                return
            channel = self._channel_keys[idx]

        card = _SensorCard(self._cards_frame, channel, self._remove_sensor, params)
        card.frame.pack(fill="x", pady=2)
        self.sensor_cards.append(card)

    def _remove_sensor(self, card):
        card.frame.destroy()
        self.sensor_cards.remove(card)

    def _clear_sensors(self):
        for card in list(self.sensor_cards):
            card.frame.destroy()
        self.sensor_cards.clear()

    # ------------------------------------------------------------------
    # Load existing transmitter
    # ------------------------------------------------------------------

    def _load_existing(self):
        selected = self._load_var.get()
        if selected == "(new)":
            self._clear_sensors()
            self._lab_id_var.set(1)
            self._node_id_var.set(1)
            self._tx_name_var.set("my-transmitter")
            self._log("Cleared form for new transmitter.")
            return

        config = load_transmitter_config(selected)
        if config is None:
            self._log(f"Failed to load config from {selected}.")
            return

        self._lab_id_var.set(config["lab_id"])
        self._node_id_var.set(config["node_id"])
        self._tx_name_var.set(selected)

        self._clear_sensors()
        for sensor_entry in config["sensors"]:
            ch = sensor_entry.get("channel")
            if ch in CHANNEL_DEFS:
                self._add_sensor(channel=ch)
            else:
                self._log(f"Skipped unknown channel '{ch}' from {selected}/config.py")

        self._log(f"Loaded {selected}: lab={config['lab_id']}, node={config['node_id']}, "
                  f"{len(config['sensors'])} sensor(s).")

    # ------------------------------------------------------------------
    # Collect form data
    # ------------------------------------------------------------------

    def _collect(self):
        """Collect all form data. Returns (lab_id, node_id, sensors, tx_name) or None on error."""
        try:
            lab_id = self._lab_id_var.get()
            node_id = self._node_id_var.get()
        except (tk.TclError, ValueError):
            self._log("ERROR: Lab ID and Node ID must be integers 1-255.")
            return None

        if not (1 <= lab_id <= 255 and 1 <= node_id <= 255):
            self._log("ERROR: Lab ID and Node ID must be in range 1-255.")
            return None

        if not self.sensor_cards:
            self._log("ERROR: Add at least one sensor.")
            return None

        sensors = []
        for card in self.sensor_cards:
            sensors.append({
                "channel": card.channel,
                "params": card.get_params(),
            })

        tx_name = self._tx_name_var.get().strip()
        if not tx_name:
            self._log("ERROR: Transmitter name is required.")
            return None
        # Ensure it ends with -transmitter
        if not tx_name.endswith("-transmitter"):
            tx_name = tx_name + "-transmitter"

        return lab_id, node_id, sensors, tx_name

    def _generate(self):
        """Generate config and sensors content. Returns (config_str, sensors_str) or None."""
        result = self._collect()
        if result is None:
            return None
        lab_id, node_id, sensors, _ = result

        config_sensors = [{"channel": s["channel"]} for s in sensors]
        config_str = generate_config(lab_id, node_id, config_sensors)
        sensors_str = generate_sensors(sensors)
        return config_str, sensors_str

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_save(self):
        result = self._collect()
        if result is None:
            return
        lab_id, node_id, sensors, tx_name = result

        gen = self._generate()
        if gen is None:
            return
        config_str, sensors_str = gen

        ok, msg = save_to_repo(tx_name, config_str, sensors_str)
        self._log(msg)

    def _do_flash(self):
        gen = self._generate()
        if gen is None:
            return
        config_str, sensors_str = gen

        drive = self._drive_var.get().strip().upper()
        if not drive:
            self._log("ERROR: Enter a drive letter.")
            return
        drive = drive[0]
        mount = f"{drive}:/"

        ok, msg = flash_to_board(mount, config_str, sensors_str)
        self._log(msg)

    def _do_save_and_flash(self):
        result = self._collect()
        if result is None:
            return
        lab_id, node_id, sensors, tx_name = result

        gen = self._generate()
        if gen is None:
            return
        config_str, sensors_str = gen

        ok, msg = save_to_repo(tx_name, config_str, sensors_str)
        self._log(msg)
        if not ok:
            return

        drive = self._drive_var.get().strip().upper()
        if not drive:
            self._log("ERROR: Enter a drive letter.")
            return
        drive = drive[0]
        mount = f"{drive}:/"

        ok, msg = flash_to_board(mount, config_str, sensors_str)
        self._log(msg)


# ======================================================================
# Sensor card widget
# ======================================================================

class _SensorCard:
    """A UI card for one sensor, with channel-specific parameter fields."""

    def __init__(self, parent, channel, remove_callback, initial_params=None):
        self.channel = channel
        self._remove_callback = remove_callback
        self._widgets = {}  # field name -> tk variable

        defn = CHANNEL_DEFS[channel]
        initial_params = initial_params or {}

        self.frame = tk.LabelFrame(
            parent, text=defn["label"], padx=8, pady=6, relief="groove",
        )

        # Remove button
        tk.Button(
            self.frame, text="\u2715", command=lambda: self._remove_callback(self),
            fg="red", font=("Arial", 9, "bold"), bd=0, padx=4,
        ).pack(anchor="ne")

        # Build a row for each field
        for field in defn["fields"]:
            row = tk.Frame(self.frame)
            row.pack(fill="x", pady=1)

            tk.Label(row, text=field["label"] + ":", width=22, anchor="w").pack(side="left")

            if field["type"] == "choice":
                var = tk.StringVar(value=initial_params.get(field["name"], field["default"]))
                combo = ttk.Combobox(
                    row, textvariable=var, values=field["options"],
                    state="readonly", width=12,
                )
                combo.pack(side="left")
                self._widgets[field["name"]] = var

                # Show note when specific value selected
                if "note_on" in field:
                    note_label = tk.Label(row, text="", fg="#cc6600", font=("Arial", 8))
                    note_label.pack(side="left", padx=(8, 0))
                    notes = field["note_on"]

                    def _update_note(var=var, label=note_label, notes=notes):
                        val = var.get()
                        label.config(text=notes.get(val, ""))

                    var.trace_add("write", lambda *_a, fn=_update_note: fn())
                    _update_note()  # set initial state

            elif field["type"] == "bool":
                var = tk.BooleanVar(value=initial_params.get(field["name"], field["default"]))
                tk.Checkbutton(row, variable=var).pack(side="left")
                self._widgets[field["name"]] = var

            elif field["type"] == "scale":
                var = tk.IntVar(value=initial_params.get(field["name"], field["default"]))
                scale = tk.Scale(
                    row, variable=var, from_=field["min"], to=field["max"],
                    orient="horizontal", length=180,
                )
                scale.pack(side="left")
                self._widgets[field["name"]] = var

    def get_params(self):
        """Return a dict of field name -> current value."""
        result = {}
        for name, var in self._widgets.items():
            result[name] = var.get()
        return result

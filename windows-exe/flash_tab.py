import os
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from flash_actions import check_transmitter_id_status, flash_receiver, flash_transmitter, scan_drives
from flash_compose import compose_config_py, compose_sensors_py
from flash_dialogs import (
    confirm_reflash, open_add_sensor_dialog, open_code_preview, open_name_dialog, show_id_blocked,
)
from flash_templates import discover_templates, match_sensor_records


class FlashTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.templates = discover_templates()
        self.sensors = []  # [{"template": ..., "param_values": {key: value}}, ...]
        self.sensor_rows = []
        self._flashing = False

        self.role_frame = tk.LabelFrame(self.frame, text="Role", font=("Arial", 10, "bold"))
        self.role_frame.pack(fill="x", padx=10, pady=(10, 4))

        self.role_var = tk.StringVar(value="transmitter")
        tk.Radiobutton(self.role_frame, text="Transmitter", variable=self.role_var,
                       value="transmitter", command=self._on_role_change).pack(side="left", padx=10)
        tk.Radiobutton(self.role_frame, text="Receiver", variable=self.role_var,
                       value="receiver", command=self._on_role_change).pack(side="left", padx=10)

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

        self.log_frame = tk.LabelFrame(self.frame, text="Status", font=("Arial", 10, "bold"))
        self.log_frame.pack(fill="x", padx=10, pady=(4, 10))

        self.log_text = tk.Text(self.log_frame, font=("Consolas", 9), state="disabled",
                                wrap="word", bg="#1e1e1e", fg="#cccccc", height=6)
        log_sb = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True, padx=4, pady=4)

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

    def _add_sensor_dialog(self):
        if not self.templates:
            self.log("No sensor templates found in hardware/sensor_templates/")
            return

        def on_add(sensor):
            self.sensors.append(sensor)
            self._refresh_sensor_list()

        open_add_sensor_dialog(self.app.root, self.templates, self.sensors, on_add)

    def load_from_flash_record(self, record):
        """Populate the form from a `flashed_nodes` record. Returns True on success."""
        self.role_var.set("transmitter")
        self._on_role_change()

        self.lab_id_var.set(int(record.get("lab_id", 1)))
        self.node_id_var.set(int(record.get("node_id", 1)))

        self.sensors, missing = match_sensor_records(record.get("sensors", []), self.templates)
        self._refresh_sensor_list()

        label = record.get("name") or "Lab {}, Node {}".format(
            record.get("lab_id"), record.get("node_id")
        )
        if missing:
            self.log("Loaded '{}' — missing templates skipped: {}".format(
                label, ", ".join(missing)))
        else:
            self.log("Loaded '{}' from flash history. Set drive and click Flash.".format(label))
        return True

    def _scan_drives(self):
        self.log("Scanning for CircuitPython boards...")
        found = scan_drives()
        if found:
            self.drive_var.set(found[0])
            self.log("Found board(s): {}".format(
                ", ".join("{}:".format(d) for d in found)))
        else:
            self.log("No CircuitPython boards found (no boot_out.txt detected).")

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
        open_code_preview(self.app.root, config_code, sensors_code)

    def _flash(self):
        if self._flashing:
            self.log("Flash already in progress.")
            return

        drive = self.drive_var.get().strip().upper().rstrip(":\\/")
        if not drive:
            self.log("Enter a drive letter first.")
            return

        mount = "{}:/".format(drive)
        if not os.path.isdir(mount):
            self.log("Drive {}: is not accessible.".format(drive))
            return

        if self.role_var.get() == "transmitter":
            self._flash_transmitter(mount)
        else:
            self.log("Flashing receiver -> {}".format(mount))
            self._run_flash(lambda: flash_receiver(mount, self.log))

    def _flash_transmitter(self, mount):
        if not self.sensors:
            self.log("Add at least one sensor before flashing.")
            return

        lab_id = self.lab_id_var.get()
        node_id = self.node_id_var.get()
        remembered = self.app.remembered_nodes_ref()
        flashed = self.app.flashed_nodes_ref()

        status, existing_name = check_transmitter_id_status(
            remembered, flashed, lab_id, node_id
        )

        is_reflash = False
        if status == "reflash":
            if not confirm_reflash(self.app.root, lab_id, node_id, existing_name):
                self.log("Flash cancelled.")
                return
            is_reflash = True
        elif status == "blocked":
            show_id_blocked(self.app.root, lab_id, node_id, existing_name)
            self.log("Flash blocked: Lab {}, Node {} already in use.".format(lab_id, node_id))
            return

        sensors_snapshot = list(self.sensors)
        self.log("Flashing transmitter (Lab {}, Node {}) -> {}".format(
            lab_id, node_id, mount))

        def on_success():
            if is_reflash:
                self.app.root.after(
                    0,
                    lambda: self.app.record_flash(lab_id, node_id, existing_name, sensors_snapshot),
                )
            else:
                self.app.root.after(
                    0,
                    lambda: open_name_dialog(
                        self.app.root, lab_id, node_id, self.app.flashed_nodes_ref(),
                        lambda name: self.app.record_flash(lab_id, node_id, name, sensors_snapshot),
                    ),
                )

        self._run_flash(lambda: flash_transmitter(
            mount, lab_id, node_id, sensors_snapshot, self.log, on_success
        ))

    def _run_flash(self, target):
        self._flashing = True

        def _runner():
            try:
                target()
            finally:
                self._flashing = False

        threading.Thread(target=_runner, daemon=True).start()

import queue
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from grafana import GRAFANA_CLOUD_URL, GRAFANA_CLOUD_API_TOKEN, grafana_push, push_status
from serial_reader import scan_ports, read_from_receiver
from flash_tab import FlashTab
from storage import (
    load_state,
    save_state,
    forget_node as storage_forget_node,
    delete_flash as storage_delete_flash,
    id_in_use,
    name_in_use,
)

node_last_seen = {}  # (lab_id, node_id) -> time.time()
discovered_nodes = {}  # (lab_id, node_id) -> {"last_seen": float|None}
listened_nodes = set()  # set of (lab_id, node_id)
remembered_nodes = {}   # "lab_id,node_id" -> {"last_seen": float|None, "name": str|None}
flashed_nodes = []      # list of flash record dicts


def _load_initial_state():
    state = load_state()
    for pair in state["listened_nodes"]:
        listened_nodes.add(tuple(pair))
    for key_str, info in state["remembered_nodes"].items():
        lab_s, node_s = key_str.split(",")
        key = (int(lab_s), int(node_s))
        discovered_nodes[key] = {"last_seen": info.get("last_seen")}
        remembered_nodes[key_str] = info
    flashed_nodes.extend(state["flashed_nodes"])


_load_initial_state()


def _save():
    save_state(listened_nodes, remembered_nodes, flashed_nodes)


def node_display_name(lab_id, node_id):
    """Return 'Name (Lab X/Node Y)' if named, else 'Lab X, Node Y'."""
    info = remembered_nodes.get(f"{lab_id},{node_id}", {})
    name = info.get("name")
    if name:
        return f"{name} (Lab {lab_id}/Node {node_id})"
    return f"Lab {lab_id}, Node {node_id}"


def consume_packets(log_fn, stop_event, packet_queue):
    """Drain packet_queue, update discovered_nodes, and push to Grafana for listened nodes."""
    packet_count = 0
    while not stop_event.is_set():
        try:
            decoded = packet_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if "error" not in decoded:
            key = (decoded['lab_id'], decoded['node_id'])
            is_new = key not in discovered_nodes or discovered_nodes[key]["last_seen"] is None
            discovered_nodes[key] = {"last_seen": time.time()}

            key_str = f"{key[0]},{key[1]}"
            if key_str not in remembered_nodes:
                # Carry over any name from a prior flash record for this node
                name = None
                for record in reversed(flashed_nodes):
                    if record["lab_id"] == key[0] and record["node_id"] == key[1]:
                        name = record.get("name")
                        break
                remembered_nodes[key_str] = {"last_seen": time.time(), "name": name}
                _save()
            elif is_new:
                remembered_nodes[key_str]["last_seen"] = time.time()
                _save()

            msg_type = decoded.get("msg_type", "unknown")

            if key in listened_nodes:
                node_last_seen[key] = time.time()
                push_result = grafana_push(decoded)
                packet_count += 1
                log_fn(f"Packet #{packet_count}: {msg_type.upper()} | Lab {decoded['lab_id']}, Node {decoded['node_id']} | Push: {push_result}")
            else:
                log_fn(f"Ignored (not paired): {msg_type.upper()} | Lab {decoded['lab_id']}, Node {decoded['node_id']}")
        else:
            log_fn(f"Decode error: {decoded['error']}")


def status_loop(log_fn, stop_event, node_last_seen):
    while not stop_event.is_set():
        push_status(log_fn, node_last_seen)
        # Persist current last_seen timestamps for all known nodes
        for key, ts in list(discovered_nodes.items()):
            if ts["last_seen"] is not None:
                key_str = f"{key[0]},{key[1]}"
                if key_str in remembered_nodes:
                    remembered_nodes[key_str]["last_seen"] = ts["last_seen"]
        _save()
        stop_event.wait(30)


class DataStreamTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)

        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=5)

        self.start_btn = tk.Button(button_frame, text="Start Stream", command=self.app.start_stream,
                                   bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=18, padx=10)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(button_frame, text="Stop Stream", command=self.app.stop_stream,
                                  bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=18, padx=10, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        broadcast_frame = tk.Frame(self.frame, relief="groove", bd=1, bg="#f0f4ff")
        broadcast_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.broadcast_label = tk.Label(
            broadcast_frame,
            text="",
            font=("Arial", 9),
            bg="#f0f4ff",
            fg="#333333",
            anchor="w",
            padx=8,
            pady=4,
        )
        self.broadcast_label.pack(fill="x")
        self._refresh_broadcast_panel()

        log_frame = tk.Frame(self.frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log_text = tk.Text(log_frame, font=("Consolas", 9), state="disabled", wrap="word", bg="#1e1e1e", fg="#cccccc")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    def _refresh_broadcast_panel(self):
        if listened_nodes:
            names = "  |  ".join(node_display_name(lab, node) for lab, node in sorted(listened_nodes))
            text = f"Broadcasting nodes: {names}"
            self.broadcast_label.config(text=text, fg="#333333", font=("Arial", 9))
        else:
            text = "Broadcasting nodes: None \u2014 View Node Pairing to choose nodes to broadcast"
            self.broadcast_label.config(text=text, fg="#cc0000", font=("Arial", 9, "bold"))
        self.app.root.after(2000, self._refresh_broadcast_panel)

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{timestamp}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.app.root.after(0, _append)


class ReceiverPairingTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.node_rows = {}  # (lab_id, node_id) -> dict of widgets

        header = tk.Label(self.frame, text="Discovered Transmitters", font=("Arial", 11, "bold"))
        header.pack(pady=(10, 2))

        hint = tk.Label(self.frame, text="Transmitters appear here as packets arrive. Toggle 'Listen' to push data to Grafana.",
                        font=("Arial", 9), fg="#666666")
        hint.pack(pady=(0, 8))

        # Scrollable area
        container = tk.Frame(self.frame)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(container, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#f5f5f5")

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Column headers
        header_frame = tk.Frame(self.scroll_frame, bg="#e0e0e0")
        header_frame.pack(fill="x", padx=2, pady=(2, 4))
        tk.Label(header_frame, text="Transmitter", font=("Arial", 9, "bold"), bg="#e0e0e0", width=18, anchor="w").pack(side="left", padx=(8, 0))
        tk.Label(header_frame, text="Name", font=("Arial", 9, "bold"), bg="#e0e0e0", width=14, anchor="w").pack(side="left")
        tk.Label(header_frame, text="Last Seen", font=("Arial", 9, "bold"), bg="#e0e0e0", width=14, anchor="w").pack(side="left")
        tk.Label(header_frame, text="Status", font=("Arial", 9, "bold"), bg="#e0e0e0", width=12, anchor="w").pack(side="left")

        self._refresh()

    def _refresh(self):
        """Periodically update the transmitter list."""
        now = time.time()

        for key, info in discovered_nodes.items():
            if key not in self.node_rows:
                self._add_row(key)
            self._update_row(key, info, now)

        self.app.root.after(2000, self._refresh)

    def _add_row(self, key):
        lab_id, node_id = key

        row = tk.Frame(self.scroll_frame, bg="#ffffff", relief="groove", bd=1)
        row.pack(fill="x", padx=2, pady=2)

        id_label = tk.Label(row, text=f"Lab {lab_id} / Node {node_id}", font=("Consolas", 10),
                            bg="#ffffff", width=18, anchor="w")
        id_label.pack(side="left", padx=(8, 0))

        stored_name = remembered_nodes.get(f"{lab_id},{node_id}", {}).get("name") or ""
        name_label = tk.Label(row, text=stored_name, font=("Arial", 9, "italic"),
                              bg="#ffffff", fg="#555555", width=14, anchor="w")
        name_label.pack(side="left")

        seen_label = tk.Label(row, text="--", font=("Consolas", 9), bg="#ffffff", width=14, anchor="w")
        seen_label.pack(side="left")

        is_listened = key in listened_nodes
        btn_var = tk.BooleanVar(value=is_listened)
        toggle_btn = tk.Button(
            row,
            text="Listening" if is_listened else "Off",
            bg="#4CAF50" if is_listened else "#cccccc",
            fg="white" if is_listened else "#333333",
            font=("Arial", 9, "bold"), width=8,
            command=lambda k=key, v=btn_var: self._toggle(k, v),
        )
        toggle_btn.pack(side="left", padx=4, pady=4)

        forget_btn = tk.Button(
            row,
            text="Forget",
            fg="#b71c1c",
            font=("Arial", 9),
            width=7,
            command=lambda k=key: self._forget(k),
        )
        forget_btn.pack(side="left", padx=4, pady=4)

        self.node_rows[key] = {
            "row": row,
            "name_label": name_label,
            "seen_label": seen_label,
            "toggle_btn": toggle_btn,
            "btn_var": btn_var,
            "forget_btn": forget_btn,
        }

    def _update_row(self, key, info, now):
        widgets = self.node_rows[key]
        last_seen = info.get("last_seen")

        if last_seen is None:
            seen_text = "never seen"
        else:
            elapsed = now - last_seen
            if elapsed < 10:
                seen_text = "just now"
            elif elapsed < 60:
                seen_text = f"{int(elapsed)}s ago"
            elif elapsed < 3600:
                seen_text = f"{int(elapsed // 60)}m ago"
            elif elapsed < 86400:
                seen_text = f"{int(elapsed // 3600)}h ago"
            else:
                seen_text = f"{int(elapsed // 86400)}d ago"

        widgets["seen_label"].config(text=seen_text)

    def _toggle(self, key, btn_var):
        widgets = self.node_rows[key]
        if key in listened_nodes:
            listened_nodes.discard(key)
            btn_var.set(False)
            widgets["toggle_btn"].config(text="Off", bg="#cccccc", fg="#333333")
        else:
            listened_nodes.add(key)
            btn_var.set(True)
            widgets["toggle_btn"].config(text="Listening", bg="#4CAF50", fg="white")
        _save()

    def _forget(self, key):
        lab_id, node_id = key
        label = node_display_name(lab_id, node_id)
        if not messagebox.askyesno(
            "Forget node",
            f"Forget {label}?\n\nThis removes it from listened/remembered nodes and deletes\n"
            "any flash history for this Lab/Node ID.",
            parent=self.app.root,
        ):
            return
        self.app.forget_node(key)

    def _remove_row(self, key):
        widgets = self.node_rows.pop(key, None)
        if widgets:
            widgets["row"].destroy()


class KnownFlashesTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.row_widgets = []

        header = tk.Label(self.frame, text="Known Flashes", font=("Arial", 11, "bold"))
        header.pack(pady=(10, 2))

        hint = tk.Label(
            self.frame,
            text="Every successful flash is recorded here. Re-flash reproduces the exact "
                 "sensor config; Delete removes only the saved record.",
            font=("Arial", 9), fg="#666666", wraplength=600, justify="left",
        )
        hint.pack(pady=(0, 8), padx=10)

        container = tk.Frame(self.frame)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(container, bg="#f5f5f5", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#f5f5f5")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Column headers
        header_frame = tk.Frame(self.scroll_frame, bg="#e0e0e0")
        header_frame.pack(fill="x", padx=2, pady=(2, 4))
        tk.Label(header_frame, text="Name", font=("Arial", 9, "bold"), bg="#e0e0e0", width=18, anchor="w").pack(side="left", padx=(8, 0))
        tk.Label(header_frame, text="Lab/Node", font=("Arial", 9, "bold"), bg="#e0e0e0", width=12, anchor="w").pack(side="left")
        tk.Label(header_frame, text="Flashed", font=("Arial", 9, "bold"), bg="#e0e0e0", width=18, anchor="w").pack(side="left")
        tk.Label(header_frame, text="Sensors", font=("Arial", 9, "bold"), bg="#e0e0e0", anchor="w").pack(side="left", fill="x", expand=True)

        self.empty_label = None
        self.refresh()

    def refresh(self):
        for w in self.row_widgets:
            w.destroy()
        self.row_widgets.clear()
        if self.empty_label is not None:
            self.empty_label.destroy()
            self.empty_label = None

        if not flashed_nodes:
            self.empty_label = tk.Label(
                self.scroll_frame,
                text="No flashes recorded yet.",
                font=("Arial", 9, "italic"), fg="#888888", bg="#f5f5f5",
            )
            self.empty_label.pack(pady=10)
            return

        # Newest first
        for idx in range(len(flashed_nodes) - 1, -1, -1):
            rec = flashed_nodes[idx]
            self._add_row(idx, rec)

    def _add_row(self, index, rec):
        row = tk.Frame(self.scroll_frame, bg="#ffffff", relief="groove", bd=1)
        row.pack(fill="x", padx=2, pady=2)

        name = rec.get("name") or "(unnamed)"
        tk.Label(row, text=name, font=("Arial", 9, "bold"),
                 bg="#ffffff", width=18, anchor="w").pack(side="left", padx=(8, 0))

        lab_id = rec.get("lab_id")
        node_id = rec.get("node_id")
        tk.Label(row, text=f"L{lab_id} / N{node_id}", font=("Consolas", 9),
                 bg="#ffffff", width=12, anchor="w").pack(side="left")

        flashed_at = rec.get("flashed_at", "")
        tk.Label(row, text=flashed_at, font=("Consolas", 9),
                 bg="#ffffff", width=18, anchor="w").pack(side="left")

        sensors_summary = ", ".join(
            s.get("template_name", s.get("channel", "?")) for s in rec.get("sensors", [])
        ) or "(none)"
        tk.Label(row, text=sensors_summary, font=("Arial", 9),
                 bg="#ffffff", anchor="w", wraplength=240, justify="left").pack(
            side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            row, text="Re-flash", font=("Arial", 9, "bold"),
            bg="#2196F3", fg="white", width=9,
            command=lambda r=rec: self._reflash(r),
        ).pack(side="right", padx=4, pady=4)

        tk.Button(
            row, text="Delete", font=("Arial", 9), fg="#b71c1c", width=7,
            command=lambda i=index: self.app.delete_flash_record(i),
        ).pack(side="right", padx=4, pady=4)

        self.row_widgets.append(row)

    def _reflash(self, record):
        self.app.flash_tab.load_from_flash_record(record)
        self.app.notebook.select(self.app.flash_tab.frame)


class ReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biodesign LoRa Receiver -> Grafana")
        self.root.geometry("650x450")
        self.stop_event = threading.Event()
        self.reader_thread = None
        self.consumer_thread = None
        self.status_thread = None
        self.packet_queue = queue.Queue()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.stream_tab = DataStreamTab(self.notebook, self)
        self.pairing_tab = ReceiverPairingTab(self.notebook, self)
        self.known_flashes_tab = KnownFlashesTab(self.notebook, self)
        self.flash_tab = FlashTab(self.notebook, self)

        self.notebook.add(self.stream_tab.frame, text="  Data Stream  ")
        self.notebook.add(self.pairing_tab.frame, text="  Node Pairing  ")
        self.notebook.add(self.known_flashes_tab.frame, text="  Known Flashes  ")
        self.notebook.add(self.flash_tab.frame, text="  Flash Device  ")

        self.log(f"Grafana URL: {GRAFANA_CLOUD_URL or 'N/A'}")
        self.log(f"API token: {'configured' if GRAFANA_CLOUD_API_TOKEN else 'MISSING'}")

    def log(self, msg):
        self.stream_tab.log(msg)

    def flashed_nodes_ref(self):
        return flashed_nodes

    def remembered_nodes_ref(self):
        return remembered_nodes

    def listened_nodes_ref(self):
        return listened_nodes

    def _choose_port_dialog(self, candidates):
        """Modal dialog for choosing a COM port. Returns device string or None."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select COM Port")
        dialog.geometry("480x260")
        dialog.grab_set()

        tk.Label(dialog, text="Multiple serial ports found.\nSelect the receiver port:").pack(pady=(12, 6), padx=16)

        listbox = tk.Listbox(dialog, font=("Consolas", 9), selectmode="single", height=min(len(candidates), 8))
        for p in candidates:
            listbox.insert("end", f"{p.device}  \u2014  {p.description}")
        listbox.select_set(0)
        listbox.pack(padx=16, fill="x")

        result = [None]

        def on_ok():
            sel = listbox.curselection()
            if sel:
                result[0] = candidates[sel[0]].device
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Connect", command=on_ok, bg="#4CAF50", fg="white", width=10).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=6)

        dialog.wait_window()
        return result[0]

    def start_stream(self):
        self.stop_event.clear()
        self.log("Searching for receiver...")

        confident, candidates = scan_ports(self.log)
        if confident:
            port = confident
        elif len(candidates) == 1:
            self.log(f"  {candidates[0].device}: no confident match, using as fallback")
            port = candidates[0].device
        elif len(candidates) > 1:
            port = self._choose_port_dialog(candidates)
            if port is None:
                self.log("Port selection cancelled.")
                return
        else:
            self.log("Receiver not found. Check USB connection.")
            return

        self.log("Starting stream...")
        self.reader_thread = threading.Thread(
            target=read_from_receiver,
            args=(self.log, self.stop_event, port, self.packet_queue),
            daemon=True,
        )
        self.consumer_thread = threading.Thread(
            target=consume_packets,
            args=(self.log, self.stop_event, self.packet_queue),
            daemon=True,
        )
        self.status_thread = threading.Thread(
            target=status_loop,
            args=(self.log, self.stop_event, node_last_seen),
            daemon=True,
        )
        self.reader_thread.start()
        self.consumer_thread.start()
        self.status_thread.start()
        self.stream_tab.start_btn.config(state="disabled")
        self.stream_tab.stop_btn.config(state="normal")

    def stop_stream(self):
        self.stop_event.set()
        self.log("Stopping stream...")
        self.stream_tab.start_btn.config(state="normal")
        self.stream_tab.stop_btn.config(state="disabled")

    def forget_node(self, key):
        """Remove a (lab_id, node_id) from all persistent state and refresh UI."""
        lab_id, node_id = key
        label = node_display_name(lab_id, node_id)
        storage_forget_node(lab_id, node_id, listened_nodes, remembered_nodes, flashed_nodes)
        discovered_nodes.pop(key, None)
        node_last_seen.pop(key, None)
        _save()
        self.pairing_tab._remove_row(key)
        if hasattr(self, "known_flashes_tab"):
            self.known_flashes_tab.refresh()
        self.log(f"Forgot {label}.")

    def delete_flash_record(self, index):
        """Delete a single flash history entry by index."""
        if not (0 <= index < len(flashed_nodes)):
            return
        rec = flashed_nodes[index]
        label = rec.get("name") or f"Lab {rec.get('lab_id')}, Node {rec.get('node_id')}"
        if not messagebox.askyesno(
            "Delete flash record",
            f"Delete flash record for '{label}'?\n\nThis only removes the saved flash entry. "
            "The node itself remains paired/remembered if it has been seen on the air.",
            parent=self.root,
        ):
            return
        storage_delete_flash(flashed_nodes, index)
        _save()
        if hasattr(self, "known_flashes_tab"):
            self.known_flashes_tab.refresh()
        self.log(f"Deleted flash record: {label}")

    def record_flash(self, lab_id, node_id, name, sensors):
        """Record a successful transmitter flash. Called from the GUI thread."""
        record = {
            "lab_id": lab_id,
            "node_id": node_id,
            "name": name,
            "flashed_at": datetime.now().isoformat(timespec="seconds"),
            "sensors": [
                {
                    "channel": s["template"]["channel"],
                    "template_name": s["template"]["name"],
                    "params": s["param_values"],
                }
                for s in sensors
            ],
        }
        flashed_nodes.append(record)

        key_str = f"{lab_id},{node_id}"
        if key_str in remembered_nodes:
            if name:
                remembered_nodes[key_str]["name"] = name
        else:
            remembered_nodes[key_str] = {"last_seen": None, "name": name}

        _save()

        # Refresh name label in pairing tab if that row already exists
        key = (lab_id, node_id)
        if name and key in self.pairing_tab.node_rows:
            self.pairing_tab.node_rows[key]["name_label"].config(text=name)

        if hasattr(self, "known_flashes_tab"):
            self.known_flashes_tab.refresh()

        self.log(f"Flash recorded: Lab {lab_id}, Node {node_id} — named '{name}'")


root = tk.Tk()
app = ReceiverApp(root)
root.mainloop()

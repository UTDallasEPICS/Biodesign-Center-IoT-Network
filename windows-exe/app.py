import queue
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk

from grafana import GRAFANA_CLOUD_URL, GRAFANA_CLOUD_API_TOKEN, grafana_push, push_status
from serial_reader import scan_ports, read_from_receiver

node_last_seen = {}  # (lab_id, node_id) -> time.time()
discovered_nodes = {}  # (lab_id, node_id) -> {"last_seen": float}
listened_nodes = set()  # set of (lab_id, node_id)


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
            discovered_nodes[key] = {"last_seen": time.time()}

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

        log_frame = tk.Frame(self.frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log_text = tk.Text(log_frame, font=("Consolas", 9), state="disabled", wrap="word", bg="#1e1e1e", fg="#cccccc")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

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
        tk.Label(header_frame, text="Transmitter", font=("Arial", 9, "bold"), bg="#e0e0e0", width=20, anchor="w").pack(side="left", padx=(8, 0))
        tk.Label(header_frame, text="Last Seen", font=("Arial", 9, "bold"), bg="#e0e0e0", width=16, anchor="w").pack(side="left")
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

        name_label = tk.Label(row, text=f"Lab {lab_id} / Node {node_id}", font=("Consolas", 10),
                              bg="#ffffff", width=20, anchor="w")
        name_label.pack(side="left", padx=(8, 0))

        seen_label = tk.Label(row, text="--", font=("Consolas", 9), bg="#ffffff", width=16, anchor="w")
        seen_label.pack(side="left")

        btn_var = tk.BooleanVar(value=False)
        toggle_btn = tk.Button(row, text="Off", bg="#cccccc", fg="#333333",
                               font=("Arial", 9, "bold"), width=8,
                               command=lambda k=key, v=btn_var: self._toggle(k, v))
        toggle_btn.pack(side="left", padx=4, pady=4)

        self.node_rows[key] = {
            "row": row,
            "seen_label": seen_label,
            "toggle_btn": toggle_btn,
            "btn_var": btn_var,
        }

    def _update_row(self, key, info, now):
        widgets = self.node_rows[key]
        elapsed = now - info["last_seen"]

        if elapsed < 10:
            seen_text = "just now"
        elif elapsed < 60:
            seen_text = f"{int(elapsed)}s ago"
        else:
            seen_text = f"{int(elapsed // 60)}m {int(elapsed % 60)}s ago"

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

        self.notebook.add(self.stream_tab.frame, text="  Data Stream  ")
        self.notebook.add(self.pairing_tab.frame, text="  Node Pairing  ")

        self.log(f"Grafana URL: {GRAFANA_CLOUD_URL or 'N/A'}")
        self.log(f"API token: {'configured' if GRAFANA_CLOUD_API_TOKEN else 'MISSING'}")

    def log(self, msg):
        self.stream_tab.log(msg)

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


root = tk.Tk()
app = ReceiverApp(root)
root.mainloop()

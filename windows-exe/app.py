import queue
import threading
import time
from datetime import datetime

import tkinter as tk

from grafana import GRAFANA_CLOUD_URL, GRAFANA_CLOUD_API_TOKEN, grafana_push, push_status
from serial_reader import scan_ports, read_from_receiver

node_last_seen = {}  # (lab_id, node_id) -> time.time()


def consume_packets(log_fn, stop_event, packet_queue):
    """Drain packet_queue, update node_last_seen, and push to Grafana."""
    packet_count = 0
    while not stop_event.is_set():
        try:
            decoded = packet_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if "error" not in decoded:
            node_last_seen[(decoded['lab_id'], decoded['node_id'])] = time.time()
            push_result = grafana_push(decoded)
            packet_count += 1
            msg_type = decoded.get("msg_type", "unknown")
            log_fn(f"Packet #{packet_count}: {msg_type.upper()} | Lab {decoded['lab_id']}, Node {decoded['node_id']} | Push: {push_result}")
        else:
            log_fn(f"Decode error: {decoded['error']}")


def status_loop(log_fn, stop_event, node_last_seen):
    while not stop_event.is_set():
        push_status(log_fn, node_last_seen)
        stop_event.wait(30)


class ReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biodesign LoRa Receiver -> Grafana")
        self.root.geometry("600x400")
        self.stop_event = threading.Event()
        self.reader_thread = None
        self.consumer_thread = None
        self.status_thread = None
        self.packet_queue = queue.Queue()

        title = tk.Label(root, text="LoRa Receiver Data Stream", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 5))

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        self.start_btn = tk.Button(button_frame, text="Start Stream", command=self.start_stream,
                                   bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=18, padx=10)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(button_frame, text="Stop Stream", command=self.stop_stream,
                                  bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=18, padx=10, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        log_frame = tk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log_text = tk.Text(log_frame, font=("Consolas", 9), state="disabled", wrap="word", bg="#1e1e1e", fg="#cccccc")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log(f"Grafana URL: {GRAFANA_CLOUD_URL or 'N/A'}")
        self.log(f"API token: {'configured' if GRAFANA_CLOUD_API_TOKEN else 'MISSING'}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{timestamp}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

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
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop_stream(self):
        self.stop_event.set()
        self.log("Stopping stream...")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


root = tk.Tk()
app = ReceiverApp(root)
root.mainloop()

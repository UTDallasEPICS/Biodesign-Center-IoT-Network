import tkinter as tk
import threading
import time
from datetime import datetime
import serial
import serial.tools.list_ports
import os
import requests
from dotenv import load_dotenv
from hex_parse import decode_lora

load_dotenv()
GRAFANA_CLOUD_URL = os.getenv("GRAFANA_CLOUD_URL", "https://prometheus-prod-66-prod-us-east-3.grafana.net/api/v1/push/influx/write")
GRAFANA_CLOUD_USERNAME = os.getenv("GRAFANA_CLOUD_USERNAME", "2988310")
GRAFANA_CLOUD_API_TOKEN = os.getenv("GRAFANA_CLOUD_API_TOKEN")

node_last_seen = {}  # (lab_id, node_id) -> time.time()

def grafana_push(data):
    if not GRAFANA_CLOUD_API_TOKEN:
        return "No API token configured"

    if "error" in data:
        return "Skipped: decode error"

    lab_id = f"Lab_{data['lab_id']}"
    node_id = f"Node_{data['node_id']}"

    lines = []
    for channel in data["channels"]:
        value = channel["value"]
        if type(value) == bool:
            value = 1.0 if value else 0.0
        else:
            value = float(value)

        line = f"biodesign_{channel['metric']},lab={lab_id},node_id={node_id} reading={value}"
        lines.append(line)

    payload = "\n".join(lines)

    try:
        resp = requests.post(
            GRAFANA_CLOUD_URL,
            headers={
                "Authorization": f"Bearer {GRAFANA_CLOUD_USERNAME}:{GRAFANA_CLOUD_API_TOKEN}",
                "Content-Type": "text/plain",
            },
            data=payload,
        )
        return f"{resp.status_code} {resp.reason}"
    except Exception as e:
        return f"Error: {e}"

def push_status(log_fn):
    if not GRAFANA_CLOUD_API_TOKEN or not node_last_seen:
        return

    now = time.time()
    lines = []
    for (lab_id, nid), last_seen in node_last_seen.items():
        elapsed = now - last_seen
        if elapsed < 30:
            status = 1.0
        elif elapsed < 90:
            status = 0.5
        else:
            status = 0.0
        lines.append(f"biodesign_status,lab=Lab_{lab_id},node_id=Node_{nid} reading={status}")

    payload = "\n".join(lines)
    try:
        resp = requests.post(
            GRAFANA_CLOUD_URL,
            headers={
                "Authorization": f"Bearer {GRAFANA_CLOUD_USERNAME}:{GRAFANA_CLOUD_API_TOKEN}",
                "Content-Type": "text/plain",
            },
            data=payload,
        )
        log_fn(f"Status push: {resp.status_code} {resp.reason}")
    except Exception as e:
        log_fn(f"Status push error: {e}")

def status_loop(log_fn, stop_event):
    while not stop_event.is_set():
        push_status(log_fn)
        stop_event.wait(30)

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

def read_from_receiver(log_fn, stop_event, port):
    """Read LoRa packets from the receiver via USB serial"""

    if not port:
        log_fn("Receiver not found. Check USB connection.")
        return

    ser = None
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        log_fn(f"Connected to {port}")

        packet_count = 0

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

                        if "error" not in decoded:
                            node_last_seen[(decoded['lab_id'], decoded['node_id'])] = time.time()
                            push_result = grafana_push(decoded)
                            packet_count += 1
                            msg_type = decoded.get("msg_type", "unknown")
                            log_fn(f"Packet #{packet_count}: {msg_type.upper()} | Lab {decoded['lab_id']}, Node {decoded['node_id']} | Push: {push_result}")
                        else:
                            log_fn(f"Decode error: {decoded['error']}")
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

class ReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biodesign LoRa Receiver -> Grafana")
        self.root.geometry("600x400")
        self.stop_event = threading.Event()
        self.reader_thread = None

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
        self.reader_thread = threading.Thread(target=read_from_receiver,
                                              args=(self.log, self.stop_event, port),
                                              daemon=True)
        self.reader_thread.start()
        self.status_thread = threading.Thread(target=status_loop,
                                              args=(self.log, self.stop_event),
                                              daemon=True)
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

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

def grafana_push(data):
    if not GRAFANA_CLOUD_API_TOKEN:
        return "No API token configured"

    if "error" in data:
        return "Skipped: decode error"

    payload = "biodesign_test,lab=Lab_1 reading=42.0"

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

def find_receiver_port(log_fn):
    """Auto-detect RP2040 receiver on COM port"""
    ports = serial.tools.list_ports.comports()
    log_fn(f"Found {len(ports)} COM port(s)")
    for port in ports:
        log_fn(f"  {port.device}: {port.description} (mfr: {port.manufacturer})")
        if "RP2040" in port.description or "CircuitPython" in port.description or (port.manufacturer and "Adafruit" in port.manufacturer):
            log_fn(f"  -> Matched as receiver")
            return port.device
    # Fallback: try common COM ports
    log_fn("No RP2040 match, trying common COM ports...")
    for com_port in ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]:
        try:
            s = serial.Serial(com_port, timeout=0.1)
            s.close()
            log_fn(f"  {com_port}: open OK, using as fallback")
            return com_port
        except Exception as e:
            log_fn(f"  {com_port}: {e}")
    return None

def read_from_receiver(log_fn, stop_event):
    """Read LoRa packets from the receiver via USB serial"""
    log_fn("Searching for receiver...")
    port = find_receiver_port(log_fn)

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

    def start_stream(self):
        self.stop_event.clear()
        self.log("Starting stream...")
        self.reader_thread = threading.Thread(target=read_from_receiver,
                                              args=(self.log, self.stop_event),
                                              daemon=True)
        self.reader_thread.start()
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

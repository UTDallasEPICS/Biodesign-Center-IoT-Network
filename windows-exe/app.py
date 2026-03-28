import tkinter as tk
import threading
import time
from datetime import datetime
import serial
import serial.tools.list_ports
import os
from dotenv import load_dotenv
from hex_parse import decode_lora

load_dotenv()
GRAFANA_CLOUD_URL = os.getenv("GRAFANA_CLOUD_URL", "https://prometheus-prod-66-prod-us-east-3.grafana.net/api/prom/push")
GRAFANA_CLOUD_USERNAME = os.getenv("GRAFANA_CLOUD_USERNAME", "2988310")
GRAFANA_CLOUD_API_TOKEN = os.getenv("GRAFANA_CLOUD_API_TOKEN")

def grafana_push(data):
    if not GRAFANA_CLOUD_API_TOKEN:
        return "No API token configured"

    if "error" in data:
        return "Skipped: decode error"

    lab_id = f"Lab_{data['lab_id']}"
    node_id = f"Node_{data['sensor_id']}"

    timestamp = int(time.time() * 1000000000)

    lines = []
    for channel in data["channels"]:
        metric = channel["metric"]
        value = channel["value"]

        if type(value) == bool:
            value = 1.0 if value else 0.0
        else:
            value = float(value)

        line = f"biodesign_sensors,lab={lab_id},node_id={node_id},metric={metric} reading={value} {timestamp}"
        lines.append(line)

    payload = "\n".join(lines)

    try:
        import requests
        resp = requests.post(GRAFANA_CLOUD_URL, auth=(GRAFANA_CLOUD_USERNAME, GRAFANA_CLOUD_API_TOKEN), data=payload)
        return f"{resp.status_code} {resp.reason}"
    except Exception as e:
        return f"Error: {e}"

def find_receiver_port():
    """Auto-detect RP2040 receiver on COM port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "RP2040" in port.description or "CircuitPython" in port.description or (port.manufacturer and "Adafruit" in port.manufacturer):
            return port.device
    # Fallback: try common COM ports
    for com_port in ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]:
        try:
            s = serial.Serial(com_port, timeout=0.1)
            s.close()
            return com_port
        except:
            pass
    return None

def read_from_receiver(status_label, log_label, stop_event):
    """Read LoRa packets from the receiver via USB serial"""
    port = find_receiver_port()

    if not port:
        status_label.after(0, lambda: status_label.config(text="❌ Receiver not found. Check USB connection."))
        return

    ser = None
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        status_label.after(0, lambda: status_label.config(text=f"✅ Connected to {port}"))

        packet_count = 0

        while not stop_event.is_set() and ser.is_open:
            try:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()

                    if not line or line.startswith("["):
                        continue

                    # Treat line as hex string
                    hex_str = line.replace(" ", "").upper()

                    try:
                        decoded = decode_lora(hex_str)

                        if "error" not in decoded:
                            push_result = grafana_push(decoded)
                            packet_count += 1
                            push_time = datetime.now().strftime("%H:%M:%S")

                            msg_type = decoded.get("msg_type", "unknown")
                            status_label.after(0, lambda m=msg_type, l=decoded['lab_id'], s=decoded['sensor_id'], c=packet_count:
                                status_label.config(text=f"📡 {m.upper()} | Lab {l}, Sensor {s} | Packets: {c}"))
                            log_label.after(0, lambda t=push_time, r=push_result:
                                log_label.config(text=f"Last push: {t} | Response: {r}"))
                    except:
                        pass
                else:
                    time.sleep(0.1)

            except Exception as e:
                status_label.after(0, lambda e=str(e): status_label.config(text=f"⚠️ {e}"))
                time.sleep(1)

    except serial.SerialException as e:
        status_label.after(0, lambda: status_label.config(text=f"❌ Connection failed: {str(e)}"))
    finally:
        if ser:
            ser.close()
        status_label.after(0, lambda: status_label.config(text="🛑 Stopped"))

class ReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biodesign LoRa Receiver → Grafana")
        self.root.geometry("480x200")
        self.stop_event = threading.Event()
        self.reader_thread = None

        title = tk.Label(root, text="LoRa Receiver Data Stream", font=("Arial", 12, "bold"))
        title.pack(pady=(10, 5))

        self.label = tk.Label(root, text="Ready to connect to receiver...", wraplength=450, justify="center", font=("Arial", 10))
        self.label.pack(pady=10)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=15)

        self.start_btn = tk.Button(button_frame, text="Start Stream", command=self.start_stream,
                                   bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=18, padx=10)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(button_frame, text="Stop Stream", command=self.stop_stream,
                                  bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=18, padx=10, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        status_frame = tk.Frame(root)
        status_frame.pack(pady=5)
        self.log_label = tk.Label(status_frame, text="Pushing to " + (GRAFANA_CLOUD_URL or "N/A"), font=("Arial", 8), fg="gray")
        self.log_label.pack()

    def start_stream(self):
        self.stop_event.clear()
        self.reader_thread = threading.Thread(target=read_from_receiver,
                                              args=(self.label, self.log_label, self.stop_event),
                                              daemon=True)
        self.reader_thread.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop_stream(self):
        self.stop_event.set()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

root = tk.Tk()
app = ReceiverApp(root)
root.mainloop()

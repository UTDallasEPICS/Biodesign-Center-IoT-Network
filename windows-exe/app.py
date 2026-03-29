import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import random
import requests
import os
import serial
import serial.tools.list_ports
from dotenv import load_dotenv
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from hex_parse import decode_lora

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
PANEL_BG = "#252526"
ENTRY_BG = "#333333"
ACCENT_COLOR = "#2196F3"
ACCENT_HOVER = "#1976D2"
ERROR_COLOR = "#ff5252"
SUCCESS_COLOR = "#4caf50"

class BiodesignApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biodesign Hardware & Simulation Dashboard")
        self.root.geometry("1100x750")
        self.root.configure(bg=BG_COLOR)

        self.running = False
        self.serial_conn = None
        
        self.time_data = deque(maxlen=50)
        self.temp_data = deque(maxlen=50)
        self.door_data = deque(maxlen=50)

        load_dotenv()
        self.build_gui()

    def build_gui(self):
        control_frame = tk.Frame(self.root, bg=PANEL_BG, width=350)
        control_frame.pack(side="left", fill="y", padx=10, pady=10)
        control_frame.pack_propagate(False)

        header = tk.Label(control_frame, text="BIODESIGN DASHBOARD", bg=PANEL_BG, fg=ACCENT_COLOR, font=("Arial", 14, "bold"))
        header.pack(pady=(15, 20))

        self.url_entry = self.create_input(control_frame, "Grafana URL:", os.getenv("GRAFANA_URL", ""))
        self.user_entry = self.create_input(control_frame, "Username:", os.getenv("GRAFANA_USERNAME", ""))
        self.pass_entry = self.create_input(control_frame, "Token:", os.getenv("GRAFANA_PASSWORD", ""), is_password=True)

        tk.Label(control_frame, text="Operation Mode:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.mode_var = tk.StringVar(value="sim")
        
        style = ttk.Style()
        style.configure("TRadiobutton", background=PANEL_BG, foreground=FG_COLOR)
        ttk.Radiobutton(control_frame, text="Simulation Mode", variable=self.mode_var, value="sim", command=self.toggle_mode).pack(anchor="w", padx=30)
        ttk.Radiobutton(control_frame, text="Hardware Mode (USB)", variable=self.mode_var, value="hw", command=self.toggle_mode).pack(anchor="w", padx=30)

        self.sim_frame = tk.Frame(control_frame, bg=PANEL_BG)
        self.min_entry = self.create_input(self.sim_frame, "Sim Minutes:", "5")
        self.sim_frame.pack(fill="x", pady=10)

        self.hw_frame = tk.Frame(control_frame, bg=PANEL_BG)
        tk.Label(self.hw_frame, text="COM Port:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9)).pack(side="left", padx=20)
        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.hw_frame, textvariable=self.port_var, state="readonly", width=15)
        self.port_dropdown.pack(side="left", padx=5)
        self.refresh_ports()
        ttk.Button(self.hw_frame, text="↻", width=3, command=self.refresh_ports).pack(side="left")

        self.start_btn = tk.Button(control_frame, text="Start System", command=self.toggle_system, bg=ACCENT_COLOR, fg=FG_COLOR, font=("Arial", 12, "bold"), relief="flat")
        self.start_btn.pack(pady=25, ipadx=20, ipady=8)

        tk.Label(control_frame, text="System Log:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9, "bold")).pack(anchor="w", padx=20)
        self.log_box = scrolledtext.ScrolledText(control_frame, bg=ENTRY_BG, fg=FG_COLOR, height=15, font=("Consolas", 8), relief="flat")
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.log_box.tag_config("info", foreground="#90caf9")
        self.log_box.tag_config("success", foreground=SUCCESS_COLOR)
        self.log_box.tag_config("error", foreground=ERROR_COLOR)
        self.log_box.tag_config("raw", foreground="#aaaaaa")

        graph_frame = tk.Frame(self.root, bg=BG_COLOR)
        graph_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor=BG_COLOR)
        
        self.ax1 = self.fig.add_subplot(211)
        self.ax1.set_title("Fridge Temperature (°C)", color=FG_COLOR)
        self.ax1.set_facecolor(ENTRY_BG)
        self.ax1.tick_params(colors=FG_COLOR)
        self.line_temp, = self.ax1.plot([], [], color=ERROR_COLOR, linewidth=2)

        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_title("Door Status (0=Closed, 1=Open)", color=FG_COLOR)
        self.ax2.set_facecolor(ENTRY_BG)
        self.ax2.tick_params(colors=FG_COLOR)
        self.ax2.set_yticks([0, 1])
        self.line_door, = self.ax2.step([], [], color=ACCENT_COLOR, linewidth=2, where='post')

        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toggle_mode()
        self.log("System initialized. Select mode and press Start.", "info")

    def create_input(self, parent, label_text, default_val="", is_password=False):
        frame = tk.Frame(parent, bg=PANEL_BG)
        frame.pack(fill="x", padx=20, pady=5)
        tk.Label(frame, text=label_text, bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9), width=10, anchor="w").pack(side="left")
        entry = tk.Entry(frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat", show="*" if is_password else "")
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.insert(0, default_val)
        return entry

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_dropdown['values'] = ports
        if ports:
            self.port_dropdown.current(0)

    def toggle_mode(self):
        if self.mode_var.get() == "sim":
            self.hw_frame.pack_forget()
            self.sim_frame.pack(fill="x", pady=10)
        else:
            self.sim_frame.pack_forget()
            self.hw_frame.pack(fill="x", pady=10)

    def log(self, message, tag="info"):
        def append():
            self.log_box.config(state="normal")
            self.log_box.insert(tk.END, message + "\n", tag)
            self.log_box.see(tk.END)
            self.log_box.config(state="disabled")
        self.root.after(0, append)

    def update_graphs(self, temp=None, door=None):
        current_time = time.time()
        self.time_data.append(current_time)
        
        t_val = temp if temp is not None else (self.temp_data[-1] if self.temp_data else 4.0)
        d_val = door if door is not None else (self.door_data[-1] if self.door_data else 0)
        
        self.temp_data.append(t_val)
        self.door_data.append(d_val)

        times = [t - self.time_data[0] for t in self.time_data]

        def draw():
            self.line_temp.set_data(times, list(self.temp_data))
            self.ax1.set_xlim(left=0, right=max(10, times[-1]))
            self.ax1.set_ylim(min(self.temp_data)-1, max(self.temp_data)+1)

            self.line_door.set_data(times, list(self.door_data))
            self.ax2.set_xlim(left=0, right=max(10, times[-1]))
            
            self.canvas.draw()
        
        self.root.after(0, draw)

    def grafana_push(self, data):
        url = self.url_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        if not url or not user or not password:
            return

        lab_id = f"Lab_{data['lab_id']}"
        sensor_id = f"Node_{data['sensor_id']}"
        timestamp = int(time.time() * 1000000000)

        lines = []
        temp_val = None
        door_val = None

        for channel in data["channels"]:
            metric = channel["metric"]
            value = float(channel["value"]) if not isinstance(channel["value"], bool) else (1.0 if channel["value"] else 0.0)
            lines.append(f"biodesign_sensors,lab={lab_id},sensor_id={sensor_id},metric={metric} reading={value} {timestamp}")
            
            if metric == "temperature_celsius": temp_val = value
            if metric == "door_open": door_val = value

        if temp_val is not None or door_val is not None:
            self.update_graphs(temp=temp_val, door=door_val)

        try:
            response = requests.post(url, auth=(user, password), data="\n".join(lines), timeout=3)
            response.raise_for_status()
            self.log(f"✅ Data pushed: Node {sensor_id}", "success")
        except Exception as e:
            self.log(f"❌ Upload Error: {e}", "error")

    def toggle_system(self):
        if self.running:
            self.running = False
            self.start_btn.config(text="Start System", bg=ACCENT_COLOR)
            self.log("🛑 System stopped.", "error")
            if self.serial_conn:
                self.serial_conn.close()
        else:
            self.running = True
            self.start_btn.config(text="Stop System", bg=ERROR_COLOR)
            
            if self.mode_var.get() == "sim":
                minutes = int(self.min_entry.get())
                threading.Thread(target=self.run_simulation, args=(minutes,), daemon=True).start()
            else:
                threading.Thread(target=self.run_hardware, daemon=True).start()

    def run_hardware(self):
        port = self.port_var.get()
        if not port:
            self.log("❌ Please select a COM port.", "error")
            self.toggle_system()
            return

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=1)
            self.log(f"🔌 Connected to Hardware on {port}", "success")
            
            while self.running:
                if self.serial_conn.in_waiting > 0:
                    raw_line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if raw_line:
                        self.log(f"📥 RAW IN: {raw_line}", "raw")
                        
                        data = decode_lora(raw_line)
                        if "error" not in data:
                            self.grafana_push(data)
                        else:
                            self.log(f"⚠️ Parse Error: {data['error']}", "error")
                            
        except Exception as e:
            self.log(f"❌ Hardware Error: {e}", "error")
            self.toggle_system()

    def run_simulation(self, minutes):
        duration = minutes * 60
        start_time = time.time()
        self.log(f"🚀 Simulation started ({minutes} min)", "info")

        while self.running and (time.time() - start_time) < duration:
            temp = round(random.uniform(3.8, 5.2), 2)
            door = random.choices([0.0, 1.0], weights=[0.95, 0.05])[0]
            
            packet = {
                "lab_id": 1, "sensor_id": 1,
                "channels": [
                    {"metric": "temperature_celsius", "value": temp},
                    {"metric": "door_open", "value": door}
                ]
            }
            self.grafana_push(packet)
            time.sleep(5)
            
        if self.running:
            self.toggle_system()
            self.log("🏁 Simulation Complete!", "success")

if __name__ == "__main__":
    root = tk.Tk()
    app = BiodesignApp(root)
    root.mainloop()
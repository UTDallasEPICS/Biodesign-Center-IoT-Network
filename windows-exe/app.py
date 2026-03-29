import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import random
import requests
import os
import sys
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
        
        self.node_data = {}
        self.temp_lines = {}
        self.door_lines = {}
        self.start_time = time.time()
        self.colors = ["#2196F3", "#ff5252", "#4caf50", "#ff9800", "#9c27b0", "#00bcd4", "#e91e63", "#cddc39"]

        self.sensors = {1: "Fridge", 2: "Door", 3: "Door", 4: "Door"}
        self.node_last_seen = {}

        if getattr(sys, 'frozen', False):
            env_path = os.path.join(os.path.dirname(sys.executable), '.env')
        else:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        load_dotenv(dotenv_path=env_path, override=True)
        load_dotenv(override=True)

        self.build_gui()

    def build_gui(self):
        left_panel = tk.Frame(self.root, bg=PANEL_BG, width=380)
        left_panel.pack(side="left", fill="y", padx=10, pady=10)
        left_panel.pack_propagate(False)

        self.canvas = tk.Canvas(left_panel, bg=PANEL_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.canvas.yview)
        
        self.control_frame = tk.Frame(self.canvas, bg=PANEL_BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.control_frame, anchor="nw")
        
        self.control_frame.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        header = tk.Label(self.control_frame, text="BIODESIGN DASHBOARD", bg=PANEL_BG, fg=ACCENT_COLOR, font=("Arial", 14, "bold"))
        header.pack(pady=(15, 20))

        env_url = os.getenv("GRAFANA_URL", "")
        env_user = os.getenv("GRAFANA_USERNAME", "")
        env_pass = os.getenv("GRAFANA_PASSWORD", "")

        self.url_entry = self.create_input(self.control_frame, "Grafana URL:", env_url)
        self.user_entry = self.create_input(self.control_frame, "Username:", env_user)
        self.pass_entry = self.create_input(self.control_frame, "Token:", env_pass, is_password=True)

        tk.Label(self.control_frame, text="Active Nodes:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.sensor_listbox = tk.Listbox(self.control_frame, bg=ENTRY_BG, fg=FG_COLOR, height=5, relief="flat", selectbackground=ACCENT_COLOR)
        self.sensor_listbox.pack(fill="x", padx=20, pady=5)
        self.update_sensor_listbox()

        sensor_input_frame = tk.Frame(self.control_frame, bg=PANEL_BG)
        sensor_input_frame.pack(fill="x", padx=20, pady=5)

        self.new_sensor_id = tk.Entry(sensor_input_frame, bg=ENTRY_BG, fg=FG_COLOR, width=5)
        self.new_sensor_id.pack(side="left", padx=(0, 5))
        self.new_sensor_id.insert(0, "ID")

        self.new_sensor_type = ttk.Combobox(sensor_input_frame, values=["Fridge", "Door"], state="readonly", width=10)
        self.new_sensor_type.current(0)
        self.new_sensor_type.pack(side="left", padx=5)

        tk.Button(sensor_input_frame, text="Add", bg=ACCENT_COLOR, fg=FG_COLOR, relief="flat", command=self.add_sensor).pack(side="left", padx=5)
        tk.Button(sensor_input_frame, text="Del", bg=ERROR_COLOR, fg=FG_COLOR, relief="flat", command=self.delete_sensor).pack(side="left", padx=5)

        tk.Label(self.control_frame, text="Operation Mode:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.mode_var = tk.StringVar(value="sim")
        
        style = ttk.Style()
        style.configure("TRadiobutton", background=PANEL_BG, foreground=FG_COLOR)
        ttk.Radiobutton(self.control_frame, text="Simulation Mode", variable=self.mode_var, value="sim", command=self.toggle_mode).pack(anchor="w", padx=30)
        ttk.Radiobutton(self.control_frame, text="Hardware Mode (USB)", variable=self.mode_var, value="hw", command=self.toggle_mode).pack(anchor="w", padx=30)

        self.mode_container = tk.Frame(self.control_frame, bg=PANEL_BG)
        self.mode_container.pack(fill="x", pady=10)

        self.sim_frame = tk.Frame(self.mode_container, bg=PANEL_BG)
        self.min_entry = self.create_input(self.sim_frame, "Sim Minutes:", "5")

        self.hw_frame = tk.Frame(self.mode_container, bg=PANEL_BG)
        tk.Label(self.hw_frame, text="COM Port:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9)).pack(side="left", padx=20)
        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.hw_frame, textvariable=self.port_var, state="readonly", width=15)
        self.port_dropdown.pack(side="left", padx=5)
        self.refresh_ports()
        ttk.Button(self.hw_frame, text="↻", width=3, command=self.refresh_ports).pack(side="left")

        self.start_btn = tk.Button(self.control_frame, text="Start System", command=self.toggle_system, bg=ACCENT_COLOR, fg=FG_COLOR, font=("Arial", 12, "bold"), relief="flat")
        self.start_btn.pack(pady=15, ipadx=20, ipady=8)

        tk.Label(self.control_frame, text="System Log:", bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9, "bold")).pack(anchor="w", padx=20)
        self.log_box = scrolledtext.ScrolledText(self.control_frame, bg=ENTRY_BG, fg=FG_COLOR, height=15, font=("Consolas", 8), relief="flat")
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

        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_title("Door Status (0=Closed, 1=Open)", color=FG_COLOR)
        self.ax2.set_facecolor(ENTRY_BG)
        self.ax2.tick_params(colors=FG_COLOR)
        self.ax2.set_yticks([0, 1])

        self.fig.tight_layout(pad=3.0)
        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.graph_canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toggle_mode()
        self.log("System initialized. Select mode and press Start.", "info")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_scroll_region(self, event=None):
        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_input(self, parent, label_text, default_val="", is_password=False):
        frame = tk.Frame(parent, bg=PANEL_BG)
        frame.pack(fill="x", padx=20, pady=5)
        tk.Label(frame, text=label_text, bg=PANEL_BG, fg=FG_COLOR, font=("Arial", 9), width=10, anchor="w").pack(side="left")
        entry = tk.Entry(frame, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, relief="flat", show="*" if is_password else "")
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.insert(0, default_val)
        return entry

    def update_sensor_listbox(self):
        self.sensor_listbox.delete(0, tk.END)
        for sid in sorted(self.sensors.keys()):
            self.sensor_listbox.insert(tk.END, f"Node {sid} ({self.sensors[sid]})")
        self.update_scroll_region()

    def add_sensor(self):
        try:
            sid = int(self.new_sensor_id.get())
            if 1 <= sid <= 255:
                self.sensors[sid] = self.new_sensor_type.get()
                self.update_sensor_listbox()
                self.new_sensor_id.delete(0, tk.END)
            else:
                self.log("❌ Node ID must be between 1 and 255.", "error")
        except ValueError:
            self.log("❌ Invalid Node ID. Must be a number.", "error")

    def delete_sensor(self):
        selected = self.sensor_listbox.curselection()
        if selected:
            idx = selected[0]
            sid = sorted(self.sensors.keys())[idx]
            del self.sensors[sid]
            self.update_sensor_listbox()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_dropdown['values'] = ports
        if ports:
            self.port_dropdown.current(0)

    def find_receiver_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "RP2040" in port.description or "CircuitPython" in port.description or (port.manufacturer and "Adafruit" in port.manufacturer):
                return port.device
        for com_port in ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]:
            try:
                s = serial.Serial(com_port, timeout=0.1)
                s.close()
                return com_port
            except Exception:
                pass
        return None

    def toggle_mode(self):
        if self.mode_var.get() == "sim":
            self.hw_frame.pack_forget()
            self.sim_frame.pack(fill="x", pady=5)
        else:
            self.sim_frame.pack_forget()
            self.hw_frame.pack(fill="x", pady=5)
        self.update_scroll_region()

    def log(self, message, tag="info"):
        def append():
            self.log_box.config(state="normal")
            self.log_box.insert(tk.END, message + "\n", tag)
            self.log_box.see(tk.END)
            self.log_box.config(state="disabled")
        self.root.after(0, append)

    def update_graphs(self, node_id, temp=None, door=None):
        node_type = self.sensors.get(node_id, "Unknown")
        
        if node_id not in self.node_data:
            self.node_data[node_id] = {'times': deque(maxlen=50), 'temps': deque(maxlen=50), 'doors': deque(maxlen=50)}
            c = self.colors[node_id % len(self.colors)]
            
            if node_type == "Fridge":
                self.temp_lines[node_id], = self.ax1.plot([], [], color=c, linewidth=2, label=f"Node {node_id}")
                self.ax1.legend(loc="upper left", fontsize=8, facecolor=ENTRY_BG, labelcolor=FG_COLOR)
            elif node_type == "Door":
                self.door_lines[node_id], = self.ax2.step([], [], color=c, linewidth=2, where='post', label=f"Node {node_id}")
                self.ax2.legend(loc="upper left", fontsize=8, facecolor=ENTRY_BG, labelcolor=FG_COLOR)

        nd = self.node_data[node_id]
        current_t = time.time() - self.start_time
        
        last_t = nd['temps'][-1] if nd['temps'] else None
        last_d = nd['doors'][-1] if nd['doors'] else None
        
        nd['times'].append(current_t)
        nd['temps'].append(temp if temp is not None else last_t)
        nd['doors'].append(door if door is not None else last_d)

        def draw():
            all_t = []
            all_y = []
            for nid, d in self.node_data.items():
                all_t.extend(d['times'])
                
                if nid in self.temp_lines:
                    vt = [v for v in d['temps'] if v is not None]
                    if vt: all_y.extend(vt)
                    self.temp_lines[nid].set_data(d['times'], [v if v is not None else float('nan') for v in d['temps']])
                
                if nid in self.door_lines:
                    self.door_lines[nid].set_data(d['times'], [v if v is not None else float('nan') for v in d['doors']])

            if all_t:
                self.ax1.set_xlim(max(0, min(all_t)-2), max(10, max(all_t)+2))
                self.ax2.set_xlim(max(0, min(all_t)-2), max(10, max(all_t)+2))
            if all_y:
                self.ax1.set_ylim(min(all_y)-1, max(all_y)+1)

            self.graph_canvas.draw_idle()
        
        self.root.after(0, draw)

    def push_status(self):
        url = self.url_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not password or not self.node_last_seen:
            return

        now = time.time()
        timestamp = int(now * 1000000000)
        lines = []
        for (lab_id, nid), last_seen in self.node_last_seen.items():
            elapsed = now - last_seen
            if elapsed < 30:
                status = 1.0
            elif elapsed < 90:
                status = 0.5
            else:
                status = 0.0
            lines.append(f"biodesign_sensors,lab=Lab_{lab_id},sensor_id=Node_{nid},metric=status reading={status} {timestamp}")

        payload = "\n".join(lines)
        auth = (user, password) if user else None
        headers = {} if user else {"Authorization": f"Bearer {password}"}

        try:
            if user:
                requests.post(url, auth=auth, data=payload, timeout=3)
            else:
                requests.post(url, headers=headers, data=payload, timeout=3)
        except Exception:
            pass

    def status_loop_worker(self):
        while self.running:
            self.push_status()
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)

    def grafana_push(self, data):
        url = self.url_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        if not url or not password:
            return

        lab_id = f"Lab_{data.get('lab_id', 1)}"
        nid = data.get("node_id") or data.get("sensor_id")
        sensor_id = f"Node_{nid}"
        timestamp = int(time.time() * 1000000000)

        lines = []
        temp_val = None
        door_val = None

        for channel in data["channels"]:
            m = channel["metric"]
            if m == "temperature": m = "temperature_celsius"
            if m == "door": m = "door_open"

            val = float(channel["value"]) if not isinstance(channel["value"], bool) else (1.0 if channel["value"] else 0.0)
            lines.append(f"biodesign_sensors,lab={lab_id},sensor_id={sensor_id},metric={m} reading={val} {timestamp}")
            
            if m == "temperature_celsius": temp_val = val
            if m == "door_open": door_val = val

        if temp_val is not None or door_val is not None:
            self.update_graphs(nid, temp=temp_val, door=door_val)

        payload = "\n".join(lines)
        auth = (user, password) if user else None
        headers = {} if user else {"Authorization": f"Bearer {password}"}

        try:
            if user:
                response = requests.post(url, auth=auth, data=payload, timeout=3)
            else:
                response = requests.post(url, headers=headers, data=payload, timeout=3)
            response.raise_for_status()
            self.log(f"✅ Data pushed: Node {nid}", "success")
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
            
            threading.Thread(target=self.status_loop_worker, daemon=True).start()

            if self.mode_var.get() == "sim":
                try:
                    minutes = int(self.min_entry.get())
                    threading.Thread(target=self.run_simulation, args=(minutes,), daemon=True).start()
                except ValueError:
                    self.log("❌ Invalid simulation minutes.", "error")
                    self.toggle_system()
            else:
                threading.Thread(target=self.run_hardware, daemon=True).start()

    def run_hardware(self):
        port = self.port_var.get()
        if not port:
            port = self.find_receiver_port()
            if port:
                self.log(f"🔍 Auto-detected receiver on {port}", "info")
            else:
                self.log("❌ No COM port selected or detected.", "error")
                self.toggle_system()
                return

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=1)
            self.log(f"🔌 Connected to Hardware on {port}", "success")
            
            while self.running:
                if self.serial_conn.in_waiting > 0:
                    raw_line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if raw_line and not raw_line.startswith("["):
                        data = decode_lora(raw_line)
                        if "error" not in data:
                            nid = data.get("node_id") or data.get("sensor_id")
                            if nid in self.sensors:
                                self.log(f"📥 RAW IN: {raw_line}", "raw")
                                self.node_last_seen[(data.get('lab_id', 1), nid)] = time.time()
                                self.grafana_push(data)
                            else:
                                self.log(f"⚠️ Ignored Node {nid} (Not active)", "raw")
                        else:
                            self.log(f"⚠️ Parse Error: {data['error']}", "error")
                else:
                    time.sleep(0.1)
                            
        except Exception as e:
            self.log(f"❌ Hardware Error: {e}", "error")
            self.toggle_system()

    def run_simulation(self, minutes):
        duration = minutes * 60
        start_time = time.time()
        self.log(f"🚀 Simulation started ({minutes} min)", "info")

        while self.running and (time.time() - start_time) < duration:
            for sid, stype in list(self.sensors.items()):
                if stype == "Fridge":
                    temp = round(random.uniform(3.8, 5.2), 2)
                    door = random.choices([0.0, 1.0], weights=[0.95, 0.05])[0]
                    packet = {
                        "lab_id": 1, "node_id": sid,
                        "channels": [
                            {"metric": "temperature_celsius", "value": temp},
                            {"metric": "door_open", "value": door}
                        ]
                    }
                else:
                    door = random.choices([0.0, 1.0], weights=[0.90, 0.10])[0]
                    packet = {
                        "lab_id": 1, "node_id": sid,
                        "channels": [{"metric": "door_open", "value": door}]
                    }
                
                self.node_last_seen[(1, sid)] = time.time()
                self.grafana_push(packet)
            
            time.sleep(5)
            
        if self.running:
            self.toggle_system()
            self.log("🏁 Simulation Complete!", "success")

if __name__ == "__main__":
    root = tk.Tk()
    app = BiodesignApp(root)
    root.mainloop()
import tkinter as tk
import threading
import time
import random
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GRAFANA_URL = os.getenv("GRAFANA_URL")
USERNAME = os.getenv("GRAFANA_USERNAME")
PASSWORD = os.getenv("GRAFANA_PASSWORD")

def grafana_push(data):
    if not USERNAME or not PASSWORD or not GRAFANA_URL:
        return

    if "error" in data:
        return

    lab_id = f"Lab_{data['lab_id']}"
    node_id = f"Node_{data['node_id']}"

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
        requests.post(GRAFANA_URL, auth=(USERNAME, PASSWORD), data=payload)
    except Exception:
        pass

def run_simulation(minutes, status_label, button):
    duration_seconds = minutes * 60
    start_time = time.time()
    interval = 5 
    
    button.config(state="disabled")

    while (time.time() - start_time) < duration_seconds:
        remaining_seconds = int(duration_seconds - (time.time() - start_time))
        status_label.after(0, lambda r=remaining_seconds: status_label.config(text=f"🔴 Live: Sending data... ({r}s remaining)"))

        temp = round(random.uniform(3.8, 5.2), 2)
        fridge_door = random.choices([0.0, 1.0], weights=[0.95, 0.05])[0]
        fridge_data = {
            "lab_id": 1, "node_id": 1,
            "channels": [
                {"metric": "temperature_celsius", "value": temp},
                {"metric": "door_open", "value": fridge_door}
            ]
        }
        grafana_push(fridge_data)

        for current_node_id in [2, 3, 4]:
            door_status = random.choices([0.0, 1.0], weights=[0.90, 0.10])[0]
            door_data = {
                "lab_id": 1, "node_id": current_node_id,
                "channels": [{"metric": "door_open", "value": door_status}]
            }
            grafana_push(door_data)
        
        time.sleep(interval)

    status_label.after(0, lambda: status_label.config(text="✅ Live Simulation Complete!"))
    button.after(0, lambda: button.config(state="normal"))

def button_click():
    try:
        minutes = int(entry.get())
        threading.Thread(target=run_simulation, args=(minutes, label, button), daemon=True).start()
    except ValueError:
        label.config(text="Please enter a valid number.")

root = tk.Tk()
root.title("Biodesign Live Sensor Stream")
root.geometry("320x160")

label = tk.Label(root, text="Enter minutes to stream live data:")
label.pack(pady=(15, 5))

entry = tk.Entry(root, justify="center")
entry.insert(0, "5")
entry.pack(pady=5)

button = tk.Button(root, text="Start Live Stream", command=button_click, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
button.pack(pady=10)

root.mainloop()
import requests
import time
from hex_parse import *
from dotenv import load_dotenv
import os

load_dotenv()

GRAFANA_URL = os.getenv("GRAFANA_URL")
USERNAME = os.getenv("GRAFANA_USERNAME")
PASSWORD = os.getenv("GRAFANA_PASSWORD")

def grafana_push(data):
    if "error" in data:
        return

    lab_id = f"Lab_{data['lab_id']}"
    sensor_id = f"Node_{data['sensor_id']}"
    timestamp = int(time.time() * 1000000000)

    lines = []
    for channel in data["channels"]:
        metric = channel["metric"]
        value = channel["value"]

        if type(value) == bool:
            value = 1.0 if value else 0.0
        else:
            value = float(value)

        line = f"biodesign_sensors,lab={lab_id},sensor_id={sensor_id},metric={metric} reading={value} {timestamp}"
        lines.append(line)

    payload = "\n".join(lines)

    try:
        response = requests.post(
            GRAFANA_URL,
            auth=(USERNAME, PASSWORD),
            data=payload
        )
        response.raise_for_status()
        print("Success")
        print(response.text)
        print(payload)
    except Exception as e:
        print(e)
        if hasattr(e, 'response') and e.response is not None:
            print(e.response.text)


if __name__ == "__main__":
    hex_data = "01 01 01 01 02 01 00 01 C5 02 00 00 00"
    decoded_data = decode_lora(hex_data)
    grafana_push(decoded_data)
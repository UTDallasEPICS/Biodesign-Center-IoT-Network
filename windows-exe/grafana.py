import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
GRAFANA_CLOUD_URL = os.getenv("GRAFANA_CLOUD_URL", "https://prometheus-prod-66-prod-us-east-3.grafana.net/api/v1/push/influx/write")
GRAFANA_CLOUD_USERNAME = os.getenv("GRAFANA_CLOUD_USERNAME", "2988310")
GRAFANA_CLOUD_API_TOKEN = os.getenv("GRAFANA_CLOUD_API_TOKEN")


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


def push_status(log_fn, node_last_seen):
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

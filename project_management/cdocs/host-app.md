# Host Application Context: Biodesign Center IoT Network

Python 3 Tkinter GUI (`windows-exe/app.py`) that reads LoRa data from the receiver via USB serial and pushes metrics to Grafana Cloud. Packaged as a standalone Windows `.exe` via PyInstaller.

---

## Threading Model

Two daemon threads launched on "Start Stream":
- `reader_thread` → `read_from_receiver(log_fn, stop_event)`: serial read loop
- `status_thread` → `status_loop(log_fn, stop_event)`: pushes node status every 30 seconds

Both share a `threading.Event` stop signal. GUI updates (`self.log`) use `root.after(0, ...)` to marshal back to the main thread.

---

## Serial Reading (`read_from_receiver`)

1. Call `find_receiver_port(log_fn)` — scans COM ports for "RP2040", "CircuitPython", or Adafruit manufacturer. Falls back to probing COM3–COM8.
2. Open serial at 115200 baud.
3. Read lines. Skip empty lines and lines starting with `[` (debug output from CircuitPython).
4. Strip spaces, uppercase → pass to `decode_lora()`.
5. On successful decode: update `node_last_seen[(lab_id, node_id)]`, call `grafana_push(decoded)`.

---

## Grafana Push (`grafana_push`)

Credentials loaded from `.env` via `python-dotenv`: `GRAFANA_CLOUD_URL`, `GRAFANA_CLOUD_USERNAME`, `GRAFANA_CLOUD_API_TOKEN`.

Each channel becomes one InfluxDB line protocol line:
```
biodesign_{metric},lab=Lab_{lab_id},node_id=Node_{node_id} reading={value}
```

Bool values are cast to `1.0` / `0.0`. All values sent as `float`. Auth header: `Bearer {username}:{token}`. Content-Type: `text/plain`. Heartbeat packets have no channels so produce no lines and are not pushed.

---

## Node Status Tracking (`push_status`)

`node_last_seen: dict[(lab_id, node_id) → float]` tracks the last time each node sent a packet. `push_status` runs every 30 seconds and pushes a separate metric:

```
biodesign_status,lab=Lab_{lab_id},node_id=Node_{node_id} reading={status}
```

Status values: `1.0` (seen within 30s), `0.5` (30–90s ago), `0.0` (>90s ago). Only nodes that have been seen at least once are included.

---

## Packet Decoding (`hex_parse.py`)

`decode_lora(hex_string)` is the only public function. See `cdocs/packet-protocol.md` for return structure. This is a standalone decoder — it does not import `packet.py` and must be kept in sync with the protocol manually.

---

## Building the Executable

`pyinstaller app.spec` from `windows-exe/`. The spec bundles `hex_parse.py` as a data file. `requirements.txt`: `pyinstaller`, `python-dotenv`, `pyserial`, `requests`. Output: `windows-exe/dist/app.exe`.

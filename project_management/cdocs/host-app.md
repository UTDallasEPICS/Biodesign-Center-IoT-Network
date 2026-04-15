# Host Application Context: Biodesign Center IoT Network

Python 3 Tkinter GUI (`windows-exe/app.py`) that reads LoRa data from the receiver via USB serial and pushes metrics to Grafana Cloud. Packaged as a standalone Windows `.exe` via PyInstaller.

---

## File Layout

| File | Responsibility |
|------|---------------|
| `app.py` | Tabbed GUI and orchestration. Owns `node_last_seen`, `discovered_nodes`, `listened_nodes`, and `packet_queue`. Manages thread lifecycle. Contains `DataStreamTab` (log view), `ReceiverPairingTab` (transmitter discovery and listen toggles), and `ReceiverApp` (orchestration). |
| `grafana.py` | Grafana Cloud I/O. Credentials, metric formatting, push functions. |
| `serial_reader.py` | COM port discovery and serial read loop. Puts decoded packets onto a queue. |
| `hex_parse.py` | Pure decoder. `decode_lora(hex_string)` → structured dict. No I/O. |

---

## Threading Model

Three daemon threads launched on "Start Stream":
- `reader_thread` → `read_from_receiver(log_fn, stop_event, port, packet_queue)`: serial read loop, puts decoded dicts onto `packet_queue`
- `consumer_thread` → `consume_packets(log_fn, stop_event, packet_queue)`: drains queue, updates `node_last_seen`, calls `grafana_push`
- `status_thread` → `status_loop(log_fn, stop_event, node_last_seen)`: pushes node status every 30 seconds

All three share a `threading.Event` stop signal. GUI updates (`self.log`) use `root.after(0, ...)` to marshal back to the main thread.

`node_last_seen: dict[(lab_id, node_id) → float]` and `packet_queue: queue.Queue` are owned by `app.py` and passed as parameters to the threads that need them.

---

## Port Selection (`serial_reader.py`)

`scan_ports(log_fn)` returns `(confident_device, candidates)`:
- If any port matches "RP2040"/"CircuitPython" in description or "Adafruit" in manufacturer, returns that device string and an empty candidates list.
- Otherwise returns `None` and a list of non-Bluetooth port objects.

`start_stream` (main thread) calls `scan_ports`, then:
- Confident match → use it.
- One candidate → use it with a fallback log message.
- Multiple candidates → show `_choose_port_dialog` (modal `Toplevel` listbox); if cancelled, abort.
- No candidates → log error, abort.

## Serial Reading (`serial_reader.py` — `read_from_receiver`)

1. Receives `port` as a parameter (resolved by `start_stream` before thread launch).
2. Open serial at 115200 baud.
3. Read lines. Skip empty lines and lines starting with `[` (debug output from CircuitPython).
4. Strip spaces, uppercase → pass to `decode_lora()`.
5. Put decoded dict onto `packet_queue` (regardless of decode error — consumer checks for `"error"` key).

---

## Packet Consumer (`app.py` — `consume_packets`)

Runs in `consumer_thread`. Blocks on `packet_queue.get(timeout=0.5)` to remain responsive to `stop_event`.

For each decoded packet:
- Always: update `discovered_nodes[(lab_id, node_id)]` with current time and log the packet.
- If `(lab_id, node_id)` is in `listened_nodes`: update `node_last_seen`, call `grafana_push(decoded)`, log push result.
- If not in `listened_nodes`: log as ignored (not paired).
- If `"error"` key: log decode error.

---

## Receiver Pairing (`app.py` — `ReceiverPairingTab`)

Tabbed view that displays all transmitters discovered via incoming packets. Each unique `(lab_id, node_id)` pair gets a row showing the transmitter identity, last-seen time, and a listen toggle button (default: off).

Module-level state:
- `discovered_nodes: dict[(lab_id, node_id) → {"last_seen": float}]` — all transmitters seen since app start.
- `listened_nodes: set[(lab_id, node_id)]` — transmitters whose packets should be pushed to Grafana.

The view refreshes every 2 seconds via `root.after()`. New transmitters are added as rows automatically. Toggling a transmitter on adds it to `listened_nodes`; toggling off removes it. Neither set persists across app restarts.

---

## Grafana Push (`grafana.py` — `grafana_push`)

Credentials loaded from `.env` via `python-dotenv`: `GRAFANA_CLOUD_URL`, `GRAFANA_CLOUD_USERNAME`, `GRAFANA_CLOUD_API_TOKEN`.

Each channel becomes one InfluxDB line protocol line:
```
biodesign_{metric},lab=Lab_{lab_id},node_id=Node_{node_id} reading={value}
```

Bool values are cast to `1.0` / `0.0`. All values sent as `float`. Auth header: `Bearer {username}:{token}`. Content-Type: `text/plain`. All packets are `DATA` type and carry channels, so every packet produces at least one Grafana line.

---

## Node Status Tracking (`grafana.py` — `push_status`)

`push_status(log_fn, node_last_seen)` runs every 30 seconds via `status_loop` and pushes a separate metric:

```
biodesign_status,lab=Lab_{lab_id},node_id=Node_{node_id} reading={status}
```

Status values: `1.0` (seen within 30s), `0.5` (30–90s ago), `0.0` (>90s ago). Only nodes that have been seen at least once are included.

---

## Packet Decoding (`hex_parse.py`)

`decode_lora(hex_string)` is the only public function. See `cdocs/packet-protocol.md` for return structure. This is a standalone decoder — it does not import `packet.py` and must be kept in sync with the protocol manually.

---

## Building the Executable

`pyinstaller app.spec` from `windows-exe/`. The spec bundles `hex_parse.py`, `grafana.py`, and `serial_reader.py` as data files. `requirements.txt`: `pyinstaller`, `python-dotenv`, `pyserial`, `requests`. Output: `windows-exe/dist/app.exe`.

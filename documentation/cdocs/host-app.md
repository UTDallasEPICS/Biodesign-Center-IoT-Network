# Host Application Context: Biodesign Center IoT Network

Python 3 Tkinter GUI (`windows-exe/app.py`) that reads LoRa data from the receiver via USB serial and pushes metrics to Grafana Cloud. Packaged as a standalone Windows `.exe` via PyInstaller.

---

## File Layout

| File | Responsibility |
|------|---------------|
| `app.py` | Tabbed GUI and orchestration. Owns `node_last_seen`, `discovered_nodes`, `listened_nodes`, `remembered_nodes`, `flashed_nodes`, and `packet_queue`. Manages thread lifecycle. Contains `DataStreamTab` (log view), `ReceiverPairingTab` (transmitter discovery, listen toggles, Forget), `KnownFlashesTab` (re-flash and delete saved flash records), and `ReceiverApp` (orchestration). |
| `storage.py` | Persistent state I/O. Reads/writes `%LOCALAPPDATA%\biosensing\state.json`. No GUI, no serial, no Grafana. |
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
3. Read lines. Skip empty lines.
   - Lines starting with `[` are logged as "Serial: …" and not decoded (the current receiver firmware does not emit bracket-prefixed lines — kept as a defensive filter).
   - Lines starting with `#` are logged as "Receiver: …" and not decoded. The receiver emits `"# alive"` heartbeats every 10 seconds of idle and `"# RECEIVER FAULT: …"` before self-resetting.
4. Strip spaces, uppercase → pass to `decode_lora()`.
5. Put decoded dict onto `packet_queue` (regardless of decode error — consumer checks for `"error"` key).
6. **Silence detection:** if no line (of any kind) is received for `SILENCE_WARN_SECONDS` (default 30), log `"No data from receiver for 30s — receiver may be hung"`. Warning fires once per silence event; reset on next received line, which logs `"Receiver responded after silence"`. With the receiver's 10-second heartbeat, normal operation should never trigger this — a fired warning means the receiver itself is dead.

---

## Packet Consumer (`app.py` — `consume_packets`)

Runs in `consumer_thread`. Blocks on `packet_queue.get(timeout=0.5)` to remain responsive to `stop_event`.

For each decoded packet:
- Always: update `discovered_nodes[(lab_id, node_id)]` with current time and log the packet.
- If `(lab_id, node_id)` is in `listened_nodes`: update `node_last_seen`, call `grafana_push(decoded)`, log push result.
- If not in `listened_nodes`: log as ignored (not paired).
- If `"error"` key: log decode error.

---

## Persistent State (`app.py` + `storage.py`)

State is loaded on startup from `%LOCALAPPDATA%\biosensing\state.json` via `_load_initial_state()` and saved atomically (write-then-rename) by `_save()`. Save triggers:
- New node first discovered (in `consume_packets`)
- Listen toggle changed (in `ReceiverPairingTab._toggle`)
- Flash recorded (in `ReceiverApp.record_flash`)
- Node forgotten (in `ReceiverApp.forget_node` — removes from listened, remembered, discovered, last_seen, and drops matching `flashed_nodes` history)
- Flash record deleted (in `ReceiverApp.delete_flash_record` — independent of node existence)
- Every 30 seconds in `status_loop` (to flush current `last_seen` timestamps)

### Uniqueness Invariants

- `(lab_id, node_id)` is unique across `remembered_nodes`. Flash blocks an attempt to flash an ID already in use unless that ID has prior flash history (re-flash, confirmed via dialog).
- Flash record names are unique (case-insensitive) across `flashed_nodes`. Re-flashing the same `(lab_id, node_id)` may keep its existing name (the dialog excludes the same pair from the uniqueness check).
- A name is required at flash time. Discovered-but-not-flashed nodes may have `name: None` until adopted.

Module-level state:
- `discovered_nodes: dict[(lab_id, node_id) → {"last_seen": float|None}]` — all nodes known this session plus nodes pre-loaded from storage.
- `listened_nodes: set[(lab_id, node_id)]` — transmitters whose packets are pushed to Grafana. Persisted.
- `remembered_nodes: dict["lab_id,node_id" → {"last_seen": float|None, "name": str|None}]` — persisted across sessions. Carries optional user-assigned names.
- `flashed_nodes: list[dict]` — ordered flash history. Each record: `{lab_id, node_id, name, flashed_at, sensors: [{channel, template_name, params}]}`.

**Thread safety note:** These dicts and the set are shared across the GUI thread, `consumer_thread`, and `status_thread` with no explicit locking. Python's GIL protects simple get/set operations, but compound read-modify-write sequences are not atomic. This is an existing limitation; avoid adding patterns that depend on multi-step atomicity across these globals.

`node_display_name(lab_id, node_id)` returns `"Name (Lab X/Node Y)"` if a name is stored, else `"Lab X, Node Y"`. Used in both the pairing tab and the broadcast strip.

---

## Receiver Pairing (`app.py` — `ReceiverPairingTab`)

Tabbed view that displays all transmitters known (discovered this session or loaded from storage). Each unique `(lab_id, node_id)` pair gets a row showing identity, optional name, last-seen time, a listen toggle button, and a Forget button.

The view refreshes every 2 seconds via `root.after()`. New transmitters are added as rows automatically. Toggling a transmitter calls `_save()`. Forget prompts a confirm dialog and calls `ReceiverApp.forget_node`, which removes the node from all in-memory state, drops matching flash history, persists, and removes the row. Listen state and node names survive app restarts. Rows for nodes pre-loaded from storage appear immediately on launch with their stored last-seen time and name.

---

## Known Flashes (`app.py` — `KnownFlashesTab`)

Lists every record in `flashed_nodes` (newest first). Each row shows name, Lab/Node, flashed_at, sensor summary, and two actions:

- **Re-flash** → calls `FlashTab.load_from_flash_record(record)` to populate Lab ID, Node ID, and sensor list (matching `template_name` back to a parsed template; missing templates are skipped with a warning), then switches focus to the Flash Device tab.
- **Delete** → confirm-then-remove via `ReceiverApp.delete_flash_record(index)`. Independent of whether the node was ever discovered; only the saved flash record is removed. The node row in Receiver Pairing is unaffected.

Refreshes on `record_flash`, `forget_node`, and `delete_flash_record`.

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

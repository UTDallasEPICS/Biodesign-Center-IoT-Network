# Codebase Review — Issues Found

Issues are grouped by file. Severity: **[critical]** = functional bug or broken feature, **[logic]** = incorrect behavior in edge cases or hidden assumptions, **[quality]** = dead code, naming inconsistency, or bad practice.

---

## `windows-exe/hex_parse.py`

- **[critical]** Metric names diverge from `packet.py` channel names: channel 0x04 is labeled `"doorbell"` here but `"light_event"` in packet.py; 0x03 is `"light"` here vs `"light_level"`; 0x05 is `"power"` here vs `"current_draw"`. These names flow into Grafana metric names (`biodesign_doorbell`, `biodesign_light`, etc.) and will not match if packet.py is used as the canonical reference. The two decode implementations have silently diverged.
- **[logic]** Door/light_event/current_draw are decoded as `parse_int24(raw_val_bytes) == 1`. This returns False for any value other than exactly 1 (e.g. 2 or 255 would read as False). `packet.py` correctly uses `bool(ch_bytes[2])`. Malformed or future values would silently mis-decode.
- **[quality]** The `if __name__ == "__main__"` block writes `test.json` to disk. This is a development artifact that should be removed or moved to a separate test file.
- **[quality]** `hex_parse.py` is a full parallel re-implementation of `packet.py`'s decode logic. Maintaining two independent decoders will cause drift. The host app should use `packet.py` directly (it's pure Python, not CircuitPython-specific).

---

## `windows-exe/grafana.py`

- **[logic]** Status thresholds in `push_status` (30 s → 1.0, 90 s → 0.5, else → 0.0) are hardcoded magic numbers. The transmitter's `HEARTBEAT_INTERVAL` is 30 s, but nothing ties these thresholds to that constant. If the heartbeat interval changes in config, status reporting silently goes stale.
- **[quality]** `type(value) == bool` should be `isinstance(value, bool)`. Using `==` on types is bad practice in Python.
- **[quality]** `GRAFANA_CLOUD_URL` has a hardcoded default prod URL in the source. A missing `.env` file silently points at the real endpoint.

---

## `windows-exe/serial_reader.py`

- **[quality]** `if line.startswith("["):` (line 45) matches nothing emitted by the current receiver firmware. The receiver prints startup banners without brackets, then raw hex. This filter is dead code.
- **[quality]** `hex_str = line.replace(" ", "").upper()` is called before passing to `decode_lora`, which also calls `hex_string.replace(" ", "").upper()` internally. Double-stripping is harmless but redundant.

---

## `windows-exe/app.py`

- **[critical]** `discovered_nodes`, `remembered_nodes`, `listened_nodes`, and `flashed_nodes` are module-level mutable globals written by both the consumer thread and status thread, and read/written by the GUI thread, with no locking. Python's GIL prevents torn reads on simple dict operations, but compound read-modify-write sequences (e.g. checking then setting `remembered_nodes[key_str]` in `consume_packets`) are not atomic and can produce inconsistent state under concurrent access.
- **[logic]** `start_stream` does not check whether threads are already alive before starting new ones. Rapid stop/start cycling could leave a stale reader or consumer thread running alongside a new one, producing duplicate Grafana pushes and log noise.
- **[quality]** Module-level code runs `_load_initial_state()` at import time (line 40), before any GUI is constructed. A corrupt state file would crash the process before a user-visible error can be shown.

---

## `windows-exe/storage.py`

- **[quality]** `name_in_use` has an `exclude_index` parameter that is never called with a non-None value anywhere in the codebase. It is dead code and should be removed.

---

## `windows-exe/flash_actions.py`

- **[logic]** `flash_receiver` copies `packet.py` from `hardware/shared/` to the receiver board, but `hardware/receiver/code.py` never imports `packet`. The copy wastes flash space and may confuse anyone reading the board's filesystem.
- **[quality]** `scan_drives` iterates `"DEFGHIJKLMNOPQRSTUVWXYZABC"` — an unusual ordering that skips nothing (A, B, C appear at the end). A comment explaining why D-Z comes first (avoids hammering A:/C: on typical Windows) would prevent future "cleanup" that re-alphabetizes it.

---

## `windows-exe/flash_templates.py`

- **[quality]** `discover_templates` silently swallows all parse errors with `except Exception: pass`. A malformed template file produces no log output and is silently omitted from the template list. The error should be logged.

---

## `windows-exe/flash_dialogs.py`

- **[logic]** `open_add_sensor_dialog` has a fixed window size (`"420x360"`) and the `param_frame` has no scrollbar. A template with many parameters will overflow the dialog with no way to reach the bottom fields.

---

## `hardware/shared/code.py`

- **[quality]** Sensor read calls (`READERS[ch]()`) are not wrapped in any error handling. A hardware fault (e.g. sensor unplugged mid-run) will raise an unhandled exception and crash the main loop in CircuitPython, requiring a manual reboot. A try/except per-sensor with a logged warning would make the node self-healing.

---

## `hardware/sensor_templates/current_amps_cts-cs-cax-04.py`

- **[logic]** In calibrating mode, the function returns `vout_total / samples * 1000000` — the average Vout in **microvolts**. For a 2.53 V baseline this returns ~2,530,000, a confusing number. The intent is to help the user set `VBase`, so returning the value in volts (e.g. `round(vout_total / samples, 4)`) would be far more useful.
- **[logic]** When `calibrating=True`, the return value (~millions) will be encoded as milliamps in the packet (since `current_amps` calls `int(value)`). If a calibration-mode board is accidentally left running, it will push wildly incorrect current readings to Grafana.

---

## `hardware/sensor_templates/light_event_tsl2591.py`

- **[logic]** `LIGHT_THRESHOLD = int({threshold_pct} / 100.0 * 10000)` maps a 0–100% parameter to a 0–10,000 raw ADC scale. The TSL2591's `visible` property can return raw counts well above 10,000 depending on gain/integration settings. "50% threshold" does not mean 50% of max sensor range. This should be documented in the template comment or recalibrated against actual sensor range.

---

## `flash.sh`

- **[critical]** The auto-detect and transmitter flash logic looks for `sensors.py`/`config.py` in per-transmitter subdirectories (`hardware/fridge-transmitter/`, `hardware/door-transmitter/`). Those directories no longer exist — the firmware is now generated by the GUI flash tool. Running `flash.sh` to flash a transmitter will silently copy nothing and exit without error (files are skipped with "WARNING: not found"). This script is effectively broken for transmitter flashing.

---

## `project_management/manifest.md`

- **[critical]** Lists `hardware/fridge-transmitter/sensors.py`, `hardware/fridge-transmitter/config.py`, `hardware/door-transmitter/sensors.py`, and `hardware/door-transmitter/config.py` — none of these paths exist on disk. These entries should be removed.
- **[critical]** `hardware/sensor_templates/current_amps_cts-cs-cax-04.py` exists on disk but is not listed in the manifest.
- **[quality]** `app.py` description says "Three tabs: Data Stream (log, start/stop), Receiver Pairing (discover transmitters, toggle listen), and Flash Device." The app now has **four** tabs: Data Stream, Node Pairing, Known Flashes, and Flash Device. The tab formerly called "Receiver Pairing" is now labeled "Node Pairing" in the UI. The manifest is stale.

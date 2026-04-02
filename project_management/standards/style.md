# Style Guide: Biodesign Center IoT Network

---

## Languages

- **Firmware** (`hardware/`): CircuitPython (subset of Python 3). No f-strings — use `.format()`.
- **Host app** (`windows-exe/`): CPython 3. f-strings and type annotations are acceptable.

---

## Naming

- Variables, functions, module-level state: `snake_case`.
- Constants: `UPPER_SNAKE_CASE` at module level.
- Protocol code constants (channel types, message types): prefixed by category — `CH_TEMPERATURE`, `MSG_DATA`, etc.
- No classes in firmware files. Host app uses one class (`ReceiverApp`) for the GUI widget tree only.

---

## Configuration Files

`config.py` files are plain assignment-only Python. No functions, no classes, no imports, no logic. All values are literals or simple expressions. This keeps them safe to edit without understanding the rest of the codebase.

---

## `packet.py` Duplication

`hardware/shared/packet.py` is the single canonical copy of the packet protocol, used by all transmitters and the receiver. The host app's `hex_parse.py` is a separate decoder and must be updated manually — it does not share code with `packet.py`.

---

## Error Handling

- Firmware: let errors propagate to the CircuitPython REPL. No try/except in main loops unless catching hardware-specific exceptions.
- `hex_parse.decode_lora()`: returns `{"error": "..."}` on bad input rather than raising — callers check for the key.
- `packet.decode_packet()`: raises `ValueError` on malformed input.
- Host app serial loop: wraps individual reads in try/except and logs errors; the loop continues rather than crashing.

---

## Formatting

- 4-space indentation everywhere.
- Module docstrings as block comments at the top of firmware files (see `hardware/shared/code.py` header style).
- Section separators (`# ---`) used to divide hardware init, helpers, and main loop in firmware files.
- Keep line length reasonable (~100 chars). No hard limit.

---

## Imports

- Standard library first, then third-party, then local. One blank line between groups.
- Firmware imports only what CircuitPython provides (`board`, `busio`, `digitalio`, `adafruit_rfm9x`, `time`).
- No wildcard imports.

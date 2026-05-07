import os
import re

from flash_paths import TEMPLATES_DIR


def parse_template(filepath):
    """Parse a sensor template file into metadata and code sections."""
    with open(filepath, "r") as f:
        text = f.read()

    meta = {
        "filepath": filepath,
        "name": "",
        "channel": "",
        "trigger": "none",
        "libraries": [],
        "params": [],
    }

    # Parse structured comment headers
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "# --- imports ---":
            break
        m = re.match(r"#\s*name:\s*(.+)", stripped)
        if m:
            meta["name"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*channel:\s*(.+)", stripped)
        if m:
            meta["channel"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*trigger:\s*(.+)", stripped)
        if m:
            meta["trigger"] = m.group(1).strip()
            continue
        m = re.match(r"#\s*libraries:\s*(.*)", stripped)
        if m:
            libs = m.group(1).strip()
            meta["libraries"] = [l.strip() for l in libs.split(",") if l.strip()] if libs else []
            continue
        m = re.match(r"#\s*param:\s*(.+)", stripped)
        if m:
            parts = [p.strip() for p in m.group(1).split("|")]
            if len(parts) == 4:
                meta["params"].append({
                    "key": parts[0],
                    "label": parts[1],
                    "type": parts[2],
                    "default": parts[3],
                })

    # Parse code sections delimited by "# --- <name> ---"
    sections = {"imports": "", "setup": "", "read": ""}
    current = None
    lines_buf = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "# --- imports ---":
            current = "imports"
            lines_buf = []
            continue
        elif stripped == "# --- setup ---":
            if current is not None:
                sections[current] = "\n".join(lines_buf).strip()
            current = "setup"
            lines_buf = []
            continue
        elif stripped == "# --- read ---":
            if current is not None:
                sections[current] = "\n".join(lines_buf).strip()
            current = "read"
            lines_buf = []
            continue

        if current is not None:
            lines_buf.append(line)

    if current is not None:
        sections[current] = "\n".join(lines_buf).strip()

    meta["sections"] = sections
    return meta


def discover_templates():
    """Scan hardware/sensor_templates/ and return a list of parsed templates."""
    if not os.path.isdir(TEMPLATES_DIR):
        return []
    templates = []
    for fname in sorted(os.listdir(TEMPLATES_DIR)):
        if fname.endswith(".py"):
            try:
                templates.append(parse_template(os.path.join(TEMPLATES_DIR, fname)))
            except Exception:
                pass
    return templates


def match_sensor_records(records, templates):
    """Resolve saved flash sensor records against the live template list.

    Returns (sensors, missing_names): `sensors` is the list ready for FlashTab
    in {"template": tmpl, "param_values": {...}} form; `missing_names` lists
    template_names that no longer exist on disk.
    """
    by_name = {t["name"]: t for t in templates}
    sensors = []
    missing = []
    for s in records or []:
        tmpl = by_name.get(s.get("template_name"))
        if tmpl is None:
            missing.append(s.get("template_name") or s.get("channel") or "?")
            continue
        sensors.append({"template": tmpl, "param_values": dict(s.get("params", {}))})
    return sensors, missing

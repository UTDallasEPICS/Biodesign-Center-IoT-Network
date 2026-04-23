import json
import os
import tempfile


def storage_dir():
    """Return (and create) the per-user persistent storage directory."""
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    path = os.path.join(base, "biosensing")
    os.makedirs(path, exist_ok=True)
    return path


def _state_path():
    return os.path.join(storage_dir(), "state.json")


def load_state():
    """Load persisted state from disk. Returns defaults on missing or corrupt file."""
    try:
        with open(_state_path(), "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    data.setdefault("listened_nodes", [])
    data.setdefault("remembered_nodes", {})
    data.setdefault("flashed_nodes", [])
    return data


def save_state(listened_nodes, remembered_nodes, flashed_nodes):
    """Atomically write full state to disk.

    listened_nodes   – set of (lab_id, node_id) tuples
    remembered_nodes – dict of "lab_id,node_id" → {"last_seen": float|None, "name": str|None}
    flashed_nodes    – list of flash record dicts
    """
    data = {
        "listened_nodes": [list(k) for k in sorted(listened_nodes)],
        "remembered_nodes": remembered_nodes,
        "flashed_nodes": flashed_nodes,
    }
    tmp_fd, tmp_path = tempfile.mkstemp(dir=storage_dir(), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, _state_path())
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

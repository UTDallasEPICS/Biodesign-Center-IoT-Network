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


def id_in_use(remembered_nodes, lab_id, node_id):
    """True if (lab_id, node_id) is already registered."""
    return f"{lab_id},{node_id}" in remembered_nodes


def name_in_use(flashed_nodes, name, exclude_index=None, exclude_pair=None):
    """Case-insensitive check for an existing flash record with this name.

    exclude_index – skip the record at this index.
    exclude_pair  – (lab_id, node_id) to skip (used during re-flash so a node
                    can keep its previous name without colliding with itself).
    """
    if not name:
        return False
    target = name.strip().lower()
    for i, rec in enumerate(flashed_nodes):
        if exclude_index is not None and i == exclude_index:
            continue
        if exclude_pair is not None and (rec.get("lab_id"), rec.get("node_id")) == tuple(exclude_pair):
            continue
        existing = (rec.get("name") or "").strip().lower()
        if existing and existing == target:
            return True
    return False


def delete_flash(flashed_nodes, index):
    """Remove a single flash record by list index. Mutates in place."""
    if 0 <= index < len(flashed_nodes):
        del flashed_nodes[index]


def forget_node(lab_id, node_id, listened_nodes, remembered_nodes, flashed_nodes):
    """Remove all traces of (lab_id, node_id) from persistent state. Mutates in place."""
    key_tuple = (lab_id, node_id)
    key_str = f"{lab_id},{node_id}"

    listened_nodes.discard(key_tuple)
    remembered_nodes.pop(key_str, None)

    flashed_nodes[:] = [
        r for r in flashed_nodes
        if not (r.get("lab_id") == lab_id and r.get("node_id") == node_id)
    ]

import tkinter as tk
from tkinter import messagebox, ttk

from flash_paths import BOARD_PINS
from storage import name_in_use


def confirm_reflash(parent, lab_id, node_id, existing_name):
    """Yes/no prompt for re-flashing an already-flashed node."""
    label = existing_name or "this node"
    return messagebox.askyesno(
        "Re-flash existing node",
        "Lab {}, Node {} is already flashed as '{}'.\n\n"
        "Re-flash this node?".format(lab_id, node_id, label),
        parent=parent,
    )


def show_id_blocked(parent, lab_id, node_id, existing_name):
    """Error dialog when an id is remembered but has no flash history."""
    label = existing_name or "Lab {}, Node {}".format(lab_id, node_id)
    messagebox.showerror(
        "ID already in use",
        "Lab {}, Node {} is already known ({}).\n\n"
        "Pick a different ID, or Forget that node in the Node Pairing tab first."
        .format(lab_id, node_id, label),
        parent=parent,
    )


def open_add_sensor_dialog(parent, templates, existing_sensors, on_add):
    """Modal dialog for picking a sensor template and configuring its params.

    Calls on_add({"template": tmpl, "param_values": {...}}) when the user
    accepts a valid selection. Refuses to add a sensor whose channel is
    already present in existing_sensors.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Add Sensor")
    dialog.geometry("420x360")
    dialog.grab_set()

    tk.Label(dialog, text="Select sensor type:",
             font=("Arial", 10, "bold")).pack(pady=(12, 4))

    listbox = tk.Listbox(dialog, font=("Consolas", 10), selectmode="single",
                         height=min(len(templates), 6))
    for tmpl in templates:
        listbox.insert("end", tmpl["name"])
    listbox.select_set(0)
    listbox.pack(padx=16, fill="x")

    param_frame = tk.LabelFrame(dialog, text="Parameters", font=("Arial", 9, "bold"))
    param_frame.pack(fill="x", padx=16, pady=(8, 4))

    param_widgets = {}
    selected_idx = [None]

    def on_type_select(event=None):
        sel = listbox.curselection()
        if not sel:
            # Focus transitions (e.g. picking a value in a readonly Combobox)
            # can fire <<ListboxSelect>> with no selection. Don't rebuild —
            # destroying the param widgets here loses the user's input.
            return
        idx = sel[0]
        if idx == selected_idx[0]:
            return
        selected_idx[0] = idx

        for w in param_frame.winfo_children():
            w.destroy()
        param_widgets.clear()

        tmpl = templates[idx]

        if not tmpl["params"]:
            tk.Label(param_frame, text="No configurable parameters",
                     font=("Arial", 9), fg="#888888").pack(pady=4)
            return

        for p in tmpl["params"]:
            row = tk.Frame(param_frame)
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text="{}:".format(p["label"]),
                     font=("Arial", 9)).pack(side="left")

            if p["type"] == "pin":
                var = tk.StringVar(value=p["default"])
                ttk.Combobox(row, textvariable=var, values=BOARD_PINS,
                             width=6, font=("Consolas", 9),
                             state="readonly").pack(side="right", padx=4)
                param_widgets[p["key"]] = var
            elif p["type"] == "percent":
                var = tk.IntVar(value=int(p["default"]))
                tk.Spinbox(row, from_=0, to=100, textvariable=var,
                           width=5, font=("Arial", 9)).pack(side="right", padx=4)
                param_widgets[p["key"]] = var
            elif p["type"] == "number":
                var = tk.StringVar(value=p["default"])
                tk.Entry(row, textvariable=var, width=8,
                         font=("Consolas", 9)).pack(side="right", padx=4)
                param_widgets[p["key"]] = var

    listbox.bind("<<ListboxSelect>>", on_type_select)
    on_type_select()

    error_var = tk.StringVar(value="")
    tk.Label(dialog, textvariable=error_var, fg="red",
             font=("Arial", 9)).pack(pady=(0, 2))

    def commit():
        idx = selected_idx[0]
        if idx is None:
            return
        tmpl = templates[idx]

        for existing in existing_sensors:
            if existing["template"]["channel"] == tmpl["channel"]:
                error_var.set("Channel '{}' is already added.".format(tmpl["channel"]))
                return

        values = {key: var.get() for key, var in param_widgets.items()}
        on_add({"template": tmpl, "param_values": values})
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=8)
    tk.Button(btn_frame, text="Add", command=commit, bg="#4CAF50", fg="white",
              font=("Arial", 9, "bold"), width=8).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
              font=("Arial", 9), width=8).pack(side="left", padx=6)

    dialog.wait_window()


def open_name_dialog(parent, lab_id, node_id, flashed_nodes, on_save, prefill=None):
    """Modal dialog prompting for a required, unique name for a flashed node.

    Calls on_save(name) when the user enters a non-empty, unique name. The
    uniqueness check excludes the (lab_id, node_id) pair itself so re-flashes
    can keep their existing name.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Name This Node")
    dialog.geometry("380x190")
    dialog.resizable(False, False)
    dialog.grab_set()

    tk.Label(
        dialog,
        text="Flash complete — Lab {}, Node {}".format(lab_id, node_id),
        font=("Arial", 10, "bold"),
    ).pack(pady=(14, 4))
    tk.Label(dialog, text="Name this node (required, must be unique):",
             font=("Arial", 9)).pack()

    name_var = tk.StringVar(value=prefill or "")
    name_entry = tk.Entry(dialog, textvariable=name_var, font=("Arial", 10), width=28)
    name_entry.pack(pady=(6, 4))
    name_entry.focus_set()
    name_entry.icursor("end")

    error_var = tk.StringVar(value="")
    tk.Label(dialog, textvariable=error_var, fg="red", font=("Arial", 9)).pack()

    def commit():
        name = name_var.get().strip()
        if not name:
            error_var.set("Name is required.")
            return
        if name_in_use(flashed_nodes, name, exclude_pair=(lab_id, node_id)):
            error_var.set("That name is already used by another flash record.")
            return
        dialog.destroy()
        on_save(name)

    name_entry.bind("<Return>", lambda _e: commit())

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=(4, 8))
    tk.Button(
        btn_frame, text="Save", font=("Arial", 9, "bold"), bg="#4CAF50", fg="white", width=8,
        command=commit,
    ).pack(side="left", padx=6)

    dialog.wait_window()


def open_code_preview(parent, config_code, sensors_code):
    """Read-only preview window with tabbed config.py and sensors.py output."""
    preview = tk.Toplevel(parent)
    preview.title("Code Preview")
    preview.geometry("600x500")

    nb = ttk.Notebook(preview)
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    for title, code in [("config.py", config_code), ("sensors.py", sensors_code)]:
        tab = ttk.Frame(nb)
        nb.add(tab, text="  {}  ".format(title))

        text_w = tk.Text(tab, font=("Consolas", 9), wrap="none",
                         bg="#1e1e1e", fg="#cccccc")
        text_w.insert("1.0", code)
        text_w.config(state="disabled")

        ysb = tk.Scrollbar(tab, orient="vertical", command=text_w.yview)
        xsb = tk.Scrollbar(tab, orient="horizontal", command=text_w.xview)
        text_w.config(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        text_w.pack(fill="both", expand=True)

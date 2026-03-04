from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict

from .schema_utils import (
    assay_information_schema,
    loading_step_types,
    method_information_schema,
    processing_step_types,
    load_schema,
)
from .validation import validate_protocol


class PropertyEditor(ttk.Frame):
    def __init__(self, master: tk.Widget, schema: Dict[str, Any], on_change: Callable[[], None]):
        super().__init__(master)
        self.schema = schema
        self.on_change = on_change
        self.vars: Dict[str, tk.Variable] = {}
        self.build()

    def build(self) -> None:
        required = set(self.schema.get("required", []))
        row = 0
        for name, field in self.schema.get("properties", {}).items():
            label = f"{name}{' *' if name in required else ''}"
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            self._build_widget(row, name, field)
            row += 1

    def _build_widget(self, row: int, name: str, field: Dict[str, Any]) -> None:
        if "enum" in field:
            var = tk.StringVar()
            widget = ttk.Combobox(self, textvariable=var, values=field["enum"], state="readonly")
            if field["enum"]:
                var.set(field["enum"][0])
            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        elif field.get("type") == "boolean":
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(self, variable=var).grid(row=row, column=1, sticky="w", padx=4, pady=2)
        else:
            var = tk.StringVar()
            ttk.Entry(self, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        self.vars[name] = var
        var.trace_add("write", lambda *_: self.on_change())

    def data(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, field in self.schema.get("properties", {}).items():
            var = self.vars[name]
            if isinstance(var, tk.BooleanVar):
                out[name] = bool(var.get())
                continue
            raw = str(var.get()).strip()
            if raw == "":
                continue
            field_type = field.get("type")
            if field_type == "integer":
                out[name] = int(raw)
            elif field_type == "number":
                out[name] = float(raw)
            elif field_type in {"array", "object"}:
                out[name] = json.loads(raw)
            else:
                out[name] = raw
        return out


class StepEditor(ttk.Frame):
    def __init__(self, master: tk.Widget, title: str, step_types: Dict[str, Dict[str, Any]], on_change: Callable[[], None]):
        super().__init__(master)
        self.step_types = step_types
        self.on_change = on_change
        self.title = title
        self.steps: list[dict[str, Any]] = []

        hdr = ttk.Frame(self)
        hdr.pack(fill="x")
        ttk.Label(hdr, text=title).pack(side="left")
        ttk.Button(hdr, text="Add", command=self.add_step).pack(side="left", padx=4)

        self.listbox = tk.Listbox(self, height=6)
        self.listbox.pack(fill="x", pady=4)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(self, textvariable=self.type_var, values=sorted(step_types.keys()), state="readonly")
        self.type_combo.pack(fill="x")
        self.type_combo.bind("<<ComboboxSelected>>", lambda *_: self.rebuild_params())

        self.params_container = ttk.Frame(self)
        self.params_container.pack(fill="both", expand=True)
        self.param_editor: PropertyEditor | None = None

    def add_step(self) -> None:
        step_type = sorted(self.step_types.keys())[0]
        self.steps.append({"StepType": step_type, "StepParameters": {}})
        self.listbox.insert(tk.END, f"{len(self.steps)}. {step_type}")
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(tk.END)
        self.on_select()
        self.on_change()

    def on_select(self, *_: Any) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        step = self.steps[idx]
        self.type_var.set(step["StepType"])
        self.rebuild_params()

    def rebuild_params(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        step_type = self.type_var.get()
        self.steps[idx]["StepType"] = step_type
        self.listbox.delete(idx)
        self.listbox.insert(idx, f"{idx + 1}. {step_type}")
        self.listbox.selection_set(idx)

        for child in self.params_container.winfo_children():
            child.destroy()
        schema = self.step_types[step_type]
        self.param_editor = PropertyEditor(self.params_container, schema, self.on_change)
        self.param_editor.pack(fill="x")
        self.on_change()

    def data(self, processing: bool = False) -> list[Dict[str, Any]]:
        out = []
        for i, step in enumerate(self.steps):
            entry: Dict[str, Any] = {
                "StepType": step["StepType"],
                "StepParameters": {},
            }
            if processing:
                entry["StepIndex"] = i
                entry["StaticDurationInSeconds"] = 0
                entry["DynamicDurationInSeconds"] = 0
            out.append(entry)
        return out


class ProtocolWizardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Protocol Generator GUI")
        self.geometry("1100x800")
        self.schema = load_schema(Path(__file__).resolve().parents[2] / "protocol.schema.json")
        self.save_path: Path | None = None
        self.autosave_job: str | None = None

        self.status = tk.StringVar(value="Not validated")
        self.step_state = {
            "general": tk.StringVar(value="✗"),
            "loading": tk.StringVar(value="✗"),
            "processing": tk.StringVar(value="✗"),
        }

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=6, pady=4)
        ttk.Button(toolbar, text="Save As", command=self.save_as).pack(side="left")
        ttk.Button(toolbar, text="Export ProtocolFile.json", command=self.export_protocol).pack(side="left", padx=4)
        ttk.Label(toolbar, textvariable=self.status).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        general = ttk.Frame(notebook)
        loading = ttk.Frame(notebook)
        processing = ttk.Frame(notebook)
        notebook.add(general, text="Step 1 General")
        notebook.add(loading, text="Step 2 Loading")
        notebook.add(processing, text="Step 3 Processing")

        ttk.Label(general, textvariable=self.step_state["general"]).pack(anchor="ne")
        self.method_editor = PropertyEditor(general, method_information_schema(self.schema), self.on_change)
        self.method_editor.pack(fill="x")
        ttk.Label(general, text="AssayInformation[0]").pack(anchor="w", pady=(12, 0))
        self.assay_editor = PropertyEditor(general, assay_information_schema(self.schema), self.on_change)
        self.assay_editor.pack(fill="x")

        ttk.Label(loading, textvariable=self.step_state["loading"]).pack(anchor="ne")
        self.loading_editor = StepEditor(loading, "LoadingWorkflowSteps", loading_step_types(self.schema), self.on_change)
        self.loading_editor.pack(fill="both", expand=True)

        ttk.Label(processing, textvariable=self.step_state["processing"]).pack(anchor="ne")
        self.processing_editor = StepEditor(processing, "ProcessingWorkflowSteps", processing_step_types(self.schema), self.on_change)
        self.processing_editor.pack(fill="both", expand=True)

    def protocol_data(self) -> Dict[str, Any]:
        return {
            "MethodInformation": self.method_editor.data(),
            "AssayInformation": [self.assay_editor.data()],
            "LoadingWorkflowSteps": self.loading_editor.data(processing=False),
            "ProcessingWorkflowSteps": [{"GroupDisplayName": "Default Group", "GroupIndex": 0, "GroupSteps": self.processing_editor.data(processing=True)}],
        }

    def on_change(self) -> None:
        data = self.protocol_data()
        errors = validate_protocol(self.schema, data)
        self.step_state["general"].set("✓" if not any(e[0].startswith(p) for e in errors for p in ["MethodInformation", "AssayInformation"]) else "✗")
        self.step_state["loading"].set("✓" if not any(e[0].startswith("LoadingWorkflowSteps") for e in errors) else "✗")
        self.step_state["processing"].set("✓" if not any(e[0].startswith("ProcessingWorkflowSteps") for e in errors) else "✗")
        self.status.set("Valid" if not errors else f"Errors: {len(errors)} ({errors[0][0]}: {errors[0][1]})")
        self.schedule_autosave()

    def save_as(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not filename:
            return
        self.save_path = Path(filename)
        self.save_now()

    def schedule_autosave(self) -> None:
        if self.save_path is None:
            return
        if self.autosave_job:
            self.after_cancel(self.autosave_job)
        self.autosave_job = self.after(600, self.save_now)

    def save_now(self) -> None:
        if self.save_path is None:
            return
        self.save_path.write_text(json.dumps(self.protocol_data(), indent=2), encoding="utf-8")
        self.status.set(f"Autosaved: {self.save_path}")

    def export_protocol(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        output = Path(folder) / "ProtocolFile.json"
        data = self.protocol_data()
        errors = validate_protocol(self.schema, data)
        if errors:
            messagebox.showerror("Validation failed", "\n".join(f"{p}: {m}" for p, m in errors[:8]))
            return
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Export complete", f"Exported to {output}")


def main() -> None:
    app = ProtocolWizardApp()
    app.mainloop()


if __name__ == "__main__":
    main()

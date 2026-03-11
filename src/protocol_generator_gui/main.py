from __future__ import annotations

import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict

from addon_generator.services.generation_service import GenerationService, fragments_from_protocol_payload
from protocol_generator_gui.schema_utils import (
    assay_information_schema,
    loading_step_types,
    method_information_schema,
    processing_step_types,
    load_schema,
)
from protocol_generator_gui.persistence import DraftPersistence
from protocol_generator_gui.validation import validate_protocol
from protocol_generator_gui.wizard_logic import (
    WizardState,
    apply_checklist_action,
    assay_analyte_integrity_warnings,
    build_field_tooltip,
    build_import_conflicts,
    build_required_by_schema_checklist,
    build_output_preview,
    can_progress,
    categorize_schema_fields,
    make_step_help,
    minimal_intervention_items,
    summarize_progress,
    validate_method_editor,
    required_checklist_blockers,
)

logger = logging.getLogger(__name__)


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, *_: Any) -> None:
        if self.tip or not self.text.strip():
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + 18
        self.tip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tip, text=self.text, relief="solid", borderwidth=1, padding=6, wraplength=360)
        label.pack()

    def hide(self, *_: Any) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None


class PropertyEditor(ttk.Frame):
    def __init__(self, master: tk.Widget, schema: Dict[str, Any], on_change: Callable[[], None]):
        super().__init__(master)
        self.schema = schema
        self.on_change = on_change
        self.vars: Dict[str, tk.Variable] = {}
        self.widgets: Dict[str, tk.Widget] = {}
        self.required_names, self.advanced_names = categorize_schema_fields(schema)
        self.show_advanced = tk.BooleanVar(value=False)
        self.advanced_frame: ttk.Frame | None = None
        self.build()

    def build(self) -> None:
        basic_frame = ttk.LabelFrame(self, text="Required fields")
        basic_frame.pack(fill="x", padx=2, pady=2)
        self._build_fields(basic_frame, self.required_names)

        self.advanced_frame = ttk.LabelFrame(self, text="Advanced options")
        self.advanced_frame.pack(fill="x", padx=2, pady=8)
        if self.advanced_names:
            toggle = ttk.Checkbutton(
                self,
                text="Show advanced options",
                variable=self.show_advanced,
                command=self._toggle_advanced,
            )
            toggle.pack(anchor="w", padx=4, pady=(2, 0))
            self._build_fields(self.advanced_frame, self.advanced_names)
            self._toggle_advanced()
        else:
            self.advanced_frame.pack_forget()

    def _toggle_advanced(self) -> None:
        if not self.advanced_frame:
            return
        if self.show_advanced.get():
            self.advanced_frame.pack(fill="x", padx=2, pady=4)
        else:
            self.advanced_frame.pack_forget()

    def _build_fields(self, container: ttk.Frame, field_names: list[str]) -> None:
        row = 0
        required = set(self.schema.get("required", []))
        for name in field_names:
            field = self.schema.get("properties", {}).get(name, {})
            label = f"{name}{' *' if name in required else ''}"
            label_widget = ttk.Label(container, text=label)
            label_widget.grid(row=row, column=0, sticky="w", padx=4, pady=2)
            widget = self._build_widget(container, row, name, field)
            help_text = build_field_tooltip(name, field)
            ToolTip(label_widget, help_text)
            ToolTip(widget, help_text)
            row += 1
        container.columnconfigure(1, weight=1)

    def _build_widget(self, container: ttk.Frame, row: int, name: str, field: Dict[str, Any]) -> tk.Widget:
        if "enum" in field:
            var = tk.StringVar()
            widget = ttk.Combobox(container, textvariable=var, values=field["enum"], state="readonly")
            if field["enum"]:
                var.set(field["enum"][0])
            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        elif field.get("type") == "boolean":
            var = tk.BooleanVar(value=False)
            widget = ttk.Checkbutton(container, variable=var)
            widget.grid(row=row, column=1, sticky="w", padx=4, pady=2)
        else:
            var = tk.StringVar()
            widget = ttk.Entry(container, textvariable=var)
            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        self.vars[name] = var
        self.widgets[name] = widget
        var.trace_add("write", lambda *_: self.on_change())
        return widget

    def focus_field(self, field_name: str) -> bool:
        widget = self.widgets.get(field_name)
        if widget is None:
            return False
        if field_name in self.advanced_names and not self.show_advanced.get():
            self.show_advanced.set(True)
            self._toggle_advanced()
        widget.focus_set()
        return True

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

    def set_data(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            var = self.vars.get(key)
            if var is None:
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(value, (dict, list)):
                var.set(json.dumps(value))
            else:
                var.set(str(value))


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
        ttk.Button(hdr, text="Delete", command=self.delete_step).pack(side="left", padx=4)
        ttk.Button(hdr, text="Move Up", command=lambda: self.move_step(-1)).pack(side="left", padx=4)
        ttk.Button(hdr, text="Move Down", command=lambda: self.move_step(1)).pack(side="left", padx=4)

        self.listbox = tk.Listbox(self, height=6, exportselection=False)
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

    def delete_step(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        step_name = self.steps[idx]["StepType"]
        if not messagebox.askyesno("Confirm delete", f"Delete workflow step '{step_name}'?"):
            return
        del self.steps[idx]
        self.listbox.delete(idx)
        for i, step in enumerate(self.steps):
            self.listbox.delete(i)
            self.listbox.insert(i, f"{i + 1}. {step['StepType']}")
        if self.steps:
            self.listbox.selection_set(min(idx, len(self.steps) - 1))
            self.on_select()
        self.on_change()

    def move_step(self, direction: int) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.steps):
            return
        if not messagebox.askyesno("Confirm reorder", "Reorder this step? This can impact runtime behavior."):
            return
        self.steps[idx], self.steps[new_idx] = self.steps[new_idx], self.steps[idx]
        self.listbox.delete(0, tk.END)
        for i, step in enumerate(self.steps):
            self.listbox.insert(i, f"{i + 1}. {step['StepType']}")
        self.listbox.selection_set(new_idx)
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
        if self.param_editor is not None:
            self.steps[idx]["StepParameters"] = self.param_editor.data()
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
        self._populate_param_editor(self.steps[idx].get("StepParameters", {}))
        self.on_change()

    def _populate_param_editor(self, values: Dict[str, Any]) -> None:
        if self.param_editor is None:
            return
        for key, value in values.items():
            var = self.param_editor.vars.get(key)
            if var is None:
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(value, (dict, list)):
                var.set(json.dumps(value))
            else:
                var.set(str(value))

    def data(self, processing: bool = False) -> list[Dict[str, Any]]:
        out = []
        selected = self.listbox.curselection()
        if selected and self.param_editor is not None:
            self.steps[selected[0]]["StepParameters"] = self.param_editor.data()
        for i, step in enumerate(self.steps):
            entry: Dict[str, Any] = {
                "StepType": step["StepType"],
                "StepParameters": step.get("StepParameters", {}),
            }
            if processing:
                entry["StepIndex"] = i
                entry["StaticDurationInSeconds"] = 0
                entry["DynamicDurationInSeconds"] = 0
            out.append(entry)
        return out

    def set_data(self, steps: list[Dict[str, Any]]) -> None:
        self.steps = []
        self.listbox.delete(0, tk.END)
        for index, step in enumerate(steps):
            step_type = step.get("StepType")
            if step_type not in self.step_types:
                continue
            self.steps.append(
                {
                    "StepType": step_type,
                    "StepParameters": step.get("StepParameters", {}),
                }
            )
            self.listbox.insert(tk.END, f"{index + 1}. {step_type}")
        if self.steps:
            self.listbox.selection_set(0)
            self.on_select()


class ProtocolWizardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Protocol Generator GUI")
        self.geometry("1200x830")
        self.schema = load_schema()
        self.save_path: Path | None = None
        self.autosave_job: str | None = None
        self.current_tab_index = 0
        self.autosave_delay_ms = 400
        self.persistence = DraftPersistence(Path.home() / ".protocol_generator_last_draft.json")
        self.generation_service = GenerationService()

        self.status = tk.StringVar(value="Not validated")
        self.autosave_status = tk.StringVar(value="Autosave idle")
        self.progress_text = tk.StringVar(value="Stage 1/5 | Completed: 0/5 | Unresolved errors: 0")
        self.step_state = {
            "general": tk.StringVar(value="✗"),
            "loading": tk.StringVar(value="✗"),
            "processing": tk.StringVar(value="✗"),
        }
        self.help_text = {
            "general": tk.StringVar(value=make_step_help("general")),
            "loading": tk.StringVar(value=make_step_help("loading")),
            "processing": tk.StringVar(value=make_step_help("processing")),
        }

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=6, pady=4)
        ttk.Button(toolbar, text="Save As", command=self.save_as).pack(side="left")
        ttk.Button(toolbar, text="Export ProtocolFile.json", command=self.export_protocol).pack(side="left", padx=4)
        ttk.Label(toolbar, textvariable=self.progress_text).pack(side="left", padx=20)
        ttk.Label(toolbar, textvariable=self.autosave_status).pack(side="right", padx=20)
        ttk.Label(toolbar, textvariable=self.status).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        general = ttk.Frame(notebook)
        loading = ttk.Frame(notebook)
        processing = ttk.Frame(notebook)
        import_preview = ttk.Frame(notebook)
        validation = ttk.Frame(notebook)
        output = ttk.Frame(notebook)
        notebook.add(general, text="1. Method setup")
        notebook.add(loading, text="2. Assay/analyte setup")
        notebook.add(import_preview, text="3. Import preview/conflicts")
        notebook.add(validation, text="4. Validation")
        notebook.add(output, text="5. Output preview/export")
        self.notebook = notebook

        self.general_help = self._build_step_panel(general, "general")
        self.method_editor = PropertyEditor(self.general_help["editor_area"], method_information_schema(self.schema), self.on_change)
        self.method_editor.pack(fill="x")
        ttk.Label(self.general_help["editor_area"], text="AssayInformation[0]").pack(anchor="w", pady=(12, 0))
        self.assay_editor = PropertyEditor(self.general_help["editor_area"], assay_information_schema(self.schema), self.on_change)
        self.assay_editor.pack(fill="x")

        self.loading_help = self._build_step_panel(loading, "loading")
        self.loading_editor = StepEditor(self.loading_help["editor_area"], "LoadingWorkflowSteps", loading_step_types(self.schema), self.on_change)
        self.loading_editor.pack(fill="both", expand=True)

        self.processing_help = self._build_step_panel(processing, "processing")
        self.processing_editor = StepEditor(self.processing_help["editor_area"], "ProcessingWorkflowSteps", processing_step_types(self.schema), self.on_change)
        self.processing_editor.pack(fill="both", expand=True)

        self.wizard_state = WizardState()
        self.minimal_intervention_mode = tk.BooleanVar(value=True)
        self.latest_checklist: dict[str, Any] = {}
        conflict_toolbar = ttk.Frame(import_preview)
        conflict_toolbar.pack(fill="x", padx=8, pady=(8, 2))
        ttk.Checkbutton(
            conflict_toolbar,
            text="Minimal intervention mode",
            variable=self.minimal_intervention_mode,
            command=self.on_change,
        ).pack(side="left")
        ttk.Button(conflict_toolbar, text="Accept imported", command=lambda: self._apply_selected_checklist_action("accept_imported")).pack(side="left", padx=6)
        ttk.Button(conflict_toolbar, text="Accept default", command=lambda: self._apply_selected_checklist_action("accept_default")).pack(side="left", padx=6)

        self.import_conflict_list = tk.Listbox(import_preview, height=18, exportselection=False)
        self.import_conflict_list.pack(fill="both", expand=True, padx=8, pady=4)
        self.import_conflict_text = tk.Text(import_preview, height=8)
        self.import_conflict_text.pack(fill="both", expand=False, padx=8, pady=(0, 8))

        self.validation_text = tk.Text(validation, height=20)
        self.validation_text.pack(fill="both", expand=True, padx=8, pady=8)

        self.output_text = tk.Text(output, height=20)
        self.output_text.pack(fill="both", expand=True, padx=8, pady=8)

        self.bind_all("<Return>", self.on_enter_next)
        self.bind_all("<Escape>", self.on_escape_cancel)
        self._attempt_recovery()

    def _build_step_panel(self, container: ttk.Frame, step_key: str) -> Dict[str, ttk.Frame]:
        panel = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        panel.pack(fill="both", expand=True)

        editor = ttk.Frame(panel)
        help_panel = ttk.LabelFrame(panel, text="Help")
        panel.add(editor, weight=3)
        panel.add(help_panel, weight=2)

        top = ttk.Frame(editor)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.step_state[step_key]).pack(anchor="ne")

        help_label = ttk.Label(help_panel, textvariable=self.help_text[step_key], justify="left", wraplength=360)
        help_label.pack(fill="both", expand=True, padx=8, pady=8)
        return {"editor_area": editor, "help_area": help_panel}

    def on_tab_changed(self, *_: Any) -> None:
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index > 0 and self.save_path is None:
            if messagebox.askyesno("Save location required", "Choose a save location before completing step 1?"):
                self.save_as()
            if self.save_path is None:
                self.notebook.select(self.current_tab_index)
                return
        self.current_tab_index = tab_index
        self.progress_text.set(summarize_progress(tab_index + 1, self.step_state, self.status.get()))

    def on_enter_next(self, event: tk.Event[tk.Widget]) -> None:
        if isinstance(event.widget, ttk.Entry):
            idx = self.notebook.index(self.notebook.select())
            if idx < 4:
                self.notebook.select(idx + 1)

    def on_escape_cancel(self, *_: Any) -> None:
        if self.autosave_job:
            self.after_cancel(self.autosave_job)
            self.autosave_job = None
            self.autosave_status.set("Autosave cancelled")

    def collect_ui_payload(self) -> Dict[str, Any]:
        assay = self.assay_editor.data()
        return {
            "MethodInformation": self.method_editor.data(),
            "AssayInformation": [assay],
            "LoadingWorkflowSteps": self.loading_editor.data(processing=False),
            "ProcessingWorkflowSteps": [{"GroupDisplayName": "Default Group", "GroupIndex": 0, "GroupSteps": self.processing_editor.data(processing=True)}],
            "analytes": self.wizard_state.analytes,
        }

    def protocol_data(self) -> Dict[str, Any]:
        payload = self.collect_ui_payload()
        context = self.generation_service.import_from_gui_payload(payload)
        fragments = fragments_from_protocol_payload(payload)
        return self.generation_service.generate_protocol_json(context, fragments).payload

    def _focus_first_invalid(self, errors: list[tuple[str, str]]) -> None:
        if not errors:
            return
        path = errors[0][0]
        if path.startswith("MethodInformation/"):
            field = path.split("/", 1)[1]
            self.notebook.select(0)
            self.method_editor.focus_field(field)
        elif path.startswith("AssayInformation/0/"):
            field = path.split("/", 2)[2]
            self.notebook.select(0)
            self.assay_editor.focus_field(field)

    def on_change(self) -> None:
        payload = self.collect_ui_payload()
        context = self.generation_service.import_from_gui_payload(payload)
        fragments = fragments_from_protocol_payload(payload)
        generation_result = self.generation_service.generate_protocol_json(context, fragments)
        data = generation_result.payload
        merge_report = generation_result.merge_report
        errors = validate_protocol(self.schema, data)
        general_err = [e for e in errors if e[0].startswith("MethodInformation") or e[0].startswith("AssayInformation")]
        loading_err = [e for e in errors if e[0].startswith("LoadingWorkflowSteps")]
        processing_err = [e for e in errors if e[0].startswith("ProcessingWorkflowSteps")]
        self.step_state["general"].set("✓" if not general_err else f"✗ ({len(general_err)})")
        self.step_state["loading"].set("✓" if not loading_err else f"✗ ({len(loading_err)})")
        self.step_state["processing"].set("✓" if not processing_err else f"✗ ({len(processing_err)})")
        self.status.set("Valid" if not errors else f"Errors: {len(errors)} ({errors[0][0]}: {errors[0][1]})")
        tab_index = self.notebook.index(self.notebook.select()) + 1
        self.progress_text.set(summarize_progress(min(tab_index,3), self.step_state, self.status.get()))
        if errors:
            logger.warning("validation_errors", extra={"event": "validation_errors", "error_count": len(errors), "errors": errors[:8]})
            self._focus_first_invalid(errors)

        self.wizard_state.method_information = payload.get("MethodInformation", {})
        self.wizard_state.assays = payload.get("AssayInformation", [])
        self.wizard_state.loading_steps = payload.get("LoadingWorkflowSteps", [])
        self.wizard_state.processing_steps = payload.get("ProcessingWorkflowSteps", [])

        method_issues = validate_method_editor(self.wizard_state.method_information)
        analyte_warnings = assay_analyte_integrity_warnings(self.wizard_state.assays, self.wizard_state.analytes)
        self.wizard_state.conflicts = build_import_conflicts(payload, self.wizard_state.imported_payload, {"MethodInformation", "AssayInformation"})
        allowed, reason = can_progress("output_preview_export", self.wizard_state.conflicts)

        self.import_conflict_text.delete("1.0", tk.END)
        self.import_conflict_text.insert(tk.END, f"Conflicts: {len(self.wizard_state.conflicts)}\n")
        for conflict in self.wizard_state.conflicts:
            self.import_conflict_text.insert(tk.END, f"- {conflict.field}: imported={conflict.imported_value!r} current={conflict.current_value!r} resolution={conflict.resolution}\n")

        self.validation_text.delete("1.0", tk.END)
        self.validation_text.insert(tk.END, "Method validation\n")
        for issue in method_issues:
            self.validation_text.insert(tk.END, f"- {issue}\n")
        self.validation_text.insert(tk.END, "Analyte relationship checks\n")
        for warning in analyte_warnings:
            self.validation_text.insert(tk.END, f"- {warning}\n")

        checklist = build_required_by_schema_checklist(self.schema, payload, self.wizard_state.imported_payload, merge_report)
        self.latest_checklist = {item.path: item for item in checklist}
        self._refresh_conflict_list(checklist)
        self.validation_text.insert(tk.END, "\nRequired by schema\n")
        for item in checklist:
            fallback = f", fallback={item.fallback_source}" if item.fallback_source else ""
            self.validation_text.insert(
                tk.END,
                f"- {item.path}: class={item.classification} source={item.source}{fallback} resolved={'yes' if item.resolved else 'no'} fallback_only={'yes' if item.fallback_only else 'no'}\n",
            )

        preview_blockers = required_checklist_blockers(checklist)
        blockers = [] if allowed else [reason]
        blockers.extend(preview_blockers)
        output_preview = build_output_preview(data, "<preview unavailable>", self.wizard_state.export_target, blockers)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, "ProtocolFile.json preview\n")
        self.output_text.insert(tk.END, output_preview["ProtocolFile.json"][:1000] + "\n")
        self.output_text.insert(tk.END, "Messages\n")
        for msg in output_preview["messages"]:
            self.output_text.insert(tk.END, f"- {msg}\n")

        self.schedule_autosave()

    def _refresh_conflict_list(self, checklist: list[Any]) -> None:
        self.import_conflict_list.delete(0, tk.END)
        visible_items = minimal_intervention_items(checklist, enabled=self.minimal_intervention_mode.get())
        for item in visible_items:
            fallback = f" | fallback: {item.fallback_source}" if item.fallback_source else ""
            self.import_conflict_list.insert(
                tk.END,
                f"{item.path} [{item.classification}] source={item.source}{fallback}",
            )

    def _apply_selected_checklist_action(self, action: str) -> None:
        selection = self.import_conflict_list.curselection()
        if not selection:
            return
        selected_line = self.import_conflict_list.get(selection[0])
        path = selected_line.split(" [", 1)[0]
        item = self.latest_checklist.get(path)
        if item is None:
            return
        ok, value = apply_checklist_action(item, action)
        if not ok:
            messagebox.showwarning("Action unavailable", f"No candidate value available for {path}")
            return
        self._set_field_by_path(path, value)
        self.on_change()

    def _set_field_by_path(self, path: str, value: Any) -> None:
        if path.startswith("MethodInformation."):
            key = path.split(".", 1)[1]
            var = self.method_editor.vars.get(key)
            if var is not None:
                var.set(str(value))
            return
        if path.startswith("AssayInformation[0]."):
            key = path.split(".", 1)[1]
            var = self.assay_editor.vars.get(key)
            if var is not None:
                var.set(str(value))

    def save_as(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not filename:
            return
        self.save_path = Path(filename)
        self.save_now()

    def schedule_autosave(self) -> None:
        if self.autosave_job:
            self.after_cancel(self.autosave_job)
        self.autosave_status.set("Saving…")
        self.autosave_job = self.after(self.autosave_delay_ms, self.save_now)

    def save_now(self) -> None:
        self.autosave_job = None
        data = self.protocol_data()
        self.autosave_status.set("Saving…")
        try:
            self.persistence.save_temp_draft(data)
            if self.save_path is not None:
                DraftPersistence.write_json_atomic(self.save_path, data)
                self.autosave_status.set(f"Saved at {DraftPersistence.now_stamp()}")
            else:
                self.autosave_status.set(f"Saved draft at {DraftPersistence.now_stamp()}")
        except Exception as exc:  # noqa: BLE001
            destination = str(self.save_path) if self.save_path else "temp_draft"
            self.persistence.log_save_failure(destination, exc)
            self.autosave_status.set("Save failed")

    def _attempt_recovery(self) -> None:
        draft = self.persistence.load_temp_draft()
        if not draft:
            return
        if not messagebox.askyesno("Recover draft", "A previous draft was found. Reopen it?"):
            return
        self.apply_protocol_data(draft)
        self.autosave_status.set("Recovered last draft")

    def apply_protocol_data(self, data: Dict[str, Any]) -> None:
        self.method_editor.set_data(data.get("MethodInformation", {}))
        assay = data.get("AssayInformation", [{}])
        self.assay_editor.set_data(assay[0] if assay else {})
        self.loading_editor.set_data(data.get("LoadingWorkflowSteps", []))
        processing_groups = data.get("ProcessingWorkflowSteps", [])
        first_group = processing_groups[0] if processing_groups else {}
        self.processing_editor.set_data(first_group.get("GroupSteps", []))
        self.on_change()

    def export_protocol(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        output = Path(folder) / "ProtocolFile.json"
        data = self.protocol_data()
        errors = validate_protocol(self.schema, data)
        if errors:
            self._focus_first_invalid(errors)
            messagebox.showerror("Validation failed", "\n".join(f"{p}: {m}" for p, m in errors[:8]))
            return
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Export complete", f"Exported to {output}")


def main() -> None:
    app = ProtocolWizardApp()
    app.mainloop()


if __name__ == "__main__":
    main()

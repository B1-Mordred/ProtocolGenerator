# Protocol Generator GUI

Desktop wizard application for building a `ProtocolFile.json` from `protocol.schema.json`.

## Run locally

```bash
python -m pip install -e .
protocol-generator-gui
```

## Features

- 3-step wizard UI:
  - General information (`MethodInformation`, `AssayInformation`)
  - Loading workflow steps (`LoadingWorkflowSteps`)
  - Processing workflow steps (`ProcessingWorkflowSteps`)
- Schema-driven rendering for required flags, primitive input types, minimum-constrained numeric fields, and `StepType` conditional parameter forms with required-first progressive disclosure for advanced options.
- Inline schema validation with completion/error counters, top-level progress indicator, and automatic focus on the first invalid field.
- `Save As` + autosave-on-change, including an unsaved-path safeguard dialog before autosave can begin.
- Per-step help panel and per-field tooltips sourced from schema descriptions (with metadata fallback when unavailable).
- Destructive action safeguards (delete/reorder confirmation dialogs) and keyboard navigation (`Enter` advances tabs, `Esc` cancels pending autosave).
- Export to `ProtocolFile.json` with final schema validation.

## Build Windows executable

```powershell
./build_windows_exe.ps1
```

The script creates a one-file desktop executable using PyInstaller.

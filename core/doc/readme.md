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
- Schema-driven rendering for required flags, primitive input types, minimum-constrained numeric fields, and `StepType` conditional parameter forms.
- Inline schema validation and section completion indicators.
- `Save As` + autosave-on-change.
- Export to `ProtocolFile.json` with final schema validation.

## Build Windows executable

```powershell
./build_windows_exe.ps1
```

The script creates a one-file desktop executable using PyInstaller.

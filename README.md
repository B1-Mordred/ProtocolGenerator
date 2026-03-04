# Protocol Generator GUI

`protocol-generator-gui` is a schema-driven desktop wizard that helps scientists and operators build a valid `ProtocolFile.json` from `protocol.schema.json` without editing JSON by hand.

## Project purpose

The application reduces authoring errors by combining:

- A **3-step guided wizard** (`Step 1 General`, `Step 2 Loading`, `Step 3 Processing`)
- **Inline validation** with per-step error counts and first-error focus
- **Autosave and draft recovery** so in-progress protocol work is not lost
- **Validated export** to `ProtocolFile.json`

## Installation / setup

### Prerequisites

- Python 3.10+
- `pip`

### Install

```bash
python -m pip install -e .
```

For contributor and CI parity tooling:

```bash
python -m pip install -e .[dev]
```

## Launch instructions

Start the desktop app with the installed entry point:

```bash
protocol-generator-gui
```

Alternative module form:

```bash
python -m protocol_generator_gui.main
```

## Workflow walkthrough (3 steps)

1. **Step 1 General**
   - Fill required fields under `MethodInformation` and `AssayInformation[0]`.
   - Use **Show advanced options** only when optional parameters are needed.
   - Choose **Save As** before moving to Step 2 or Step 3.

2. **Step 2 Loading**
   - Use **Add**, **Delete**, **Move Up**, and **Move Down** to manage `LoadingWorkflowSteps`.
   - Pick `StepType`, then fill `StepParameters` in the dynamic form.

3. **Step 3 Processing**
   - Build `ProcessingWorkflowSteps` similarly.
   - The app auto-populates `StepIndex`, `StaticDurationInSeconds`, and `DynamicDurationInSeconds` during data assembly.

When all steps show `✓` and status is `Valid`, use **Export ProtocolFile.json**.

## Example output

```json
{
  "MethodInformation": {
    "MethodName": "RNA QC",
    "OperatorName": "QA Analyst"
  },
  "AssayInformation": [
    {
      "AssayName": "Sample Prep"
    }
  ],
  "LoadingWorkflowSteps": [
    {
      "StepType": "LoadMfxCarriers",
      "StepParameters": {
        "BarcodeMask": "MFX-*"
      }
    }
  ],
  "ProcessingWorkflowSteps": [
    {
      "GroupDisplayName": "Default Group",
      "GroupIndex": 0,
      "GroupSteps": [
        {
          "StepType": "SingleTransfer",
          "StepParameters": {
            "SourceLabware": "PlateA"
          },
          "StepIndex": 0,
          "StaticDurationInSeconds": 0,
          "DynamicDurationInSeconds": 0
        }
      ]
    }
  ]
}
```

## Troubleshooting

- **"Save location required" when changing tabs**
  - Expected behavior. Click **Save As**, choose a `.json` location, then proceed.
- **Status shows `Errors: N (...)`**
  - Fill required fields in the reported section. The app attempts to focus the first invalid field.
- **Autosave status is `Save failed`**
  - Verify file permissions and destination path availability. Re-run **Save As** if needed.
- **Draft recovery prompt appears on launch**
  - Choose **Yes** to restore in-progress data from the temporary draft file.

## Windows EXE build

Use the provided PowerShell helper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\build_windows_exe.ps1
```

The script invokes PyInstaller via module mode (`python -m PyInstaller`) so the build works even when `%LOCALAPPDATA%\...\Python313\Scripts` is not on `PATH`.

## Additional documentation

- End-user guide: [`doc/user-guide.md`](doc/user-guide.md)
- Developer guide: [`doc/developer-guide.md`](doc/developer-guide.md)
- Changelog: [`doc/changelog.md`](doc/changelog.md)

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
- Lifecycle-based saving with in-memory drafts before first file selection, temporary crash-recovery draft persistence, and debounced autosave-on-change (400ms).
- Mandatory save-path selection before leaving Step 1, atomic file persistence (`.tmp` write then replace), and explicit autosave status UI (`Saving…`, `Saved at HH:MM`, `Save failed`).
- Crash/restart recovery prompt to reopen the last temporary draft when present.
- Per-step help panel and per-field tooltips sourced from schema descriptions (with metadata fallback when unavailable).
- Destructive action safeguards (delete/reorder confirmation dialogs) and keyboard navigation (`Enter` advances tabs, `Esc` cancels pending autosave).
- Export to `ProtocolFile.json` with final schema validation.

## Build Windows executable

```powershell
./build_windows_exe.ps1
```

The script creates a one-file desktop executable using PyInstaller.

The Windows build uses `python -m PyInstaller`, embeds `protocol.schema.json` via `--add-data`, and resolves schema resources from bundled runtime paths so the EXE has no external schema-file dependency.
Module-safe imports in `src/protocol_generator_gui/main.py` prevent packaged startup failures from relative-import errors.

## Testing

```bash
python -m pip install -e .[dev]
pytest
```

- Test framework: `pytest` with `pytest-cov` coverage enforcement (`--cov-fail-under=85`). Coverage metrics omit `src/protocol_generator_gui/main.py` (Tkinter UI shell) to keep the gate focused on testable core logic modules.
- Unit tests cover schema parsing, dynamic field grouping, conditional `StepType` required-field behavior, and validation edge cases.
- Integration tests use a headless wizard-flow harness to verify transition guards, processing-step reorder/edit behavior, and autosave behavior after save-path selection (no Qt helpers are required because the app is Tkinter-based).
- CI runs the same test command on push and pull requests via GitHub Actions.

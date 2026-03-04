# Changelog

## Added

- Added a new schema-driven Python desktop wizard package at `src/protocol_generator_gui` with three workflow steps for protocol authoring, live validation, autosave, and validated export to `ProtocolFile.json`.
- Added packaging/build scaffolding (`pyproject.toml`, PyInstaller PowerShell build script) to generate a self-contained Windows executable.
- Added unit and integration test coverage for schema parsing, conditional `StepType` required-field handling, wizard-flow transitions, autosave behavior, and edge-case validation scenarios.
- Added GitHub Actions CI test workflow with a coverage quality gate (85% minimum) to fail regressions.

## Changed

- Enhanced the desktop wizard UX with step help panels, schema/metadata-backed tooltips, required-first progressive disclosure, progress/error indicators, and focus on the first invalid field.
- Added guard dialogs for missing autosave path setup and destructive loading/processing step delete/reorder actions, plus keyboard shortcuts for Enter-next and Esc-cancel.
- Added unit tests for wizard help/tooltip/progress logic to keep new behavior covered.
- Reworked save lifecycle behavior to persist temp drafts before first file selection, require save-path choice before leaving Step 1, autosave with a 400ms debounce and explicit save-state messaging, recover last draft on restart, and write files atomically with structured error logging for failures/validation issues.

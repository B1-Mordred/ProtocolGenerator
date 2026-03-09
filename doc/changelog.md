# Changelog

## Added

- Added deterministic analyte AddOn XML generation modules with required reference fields and deterministic sort ordering plus pre-write XSD validation that returns structured warning/error issues.
- Added v1 addon mapping configuration at `config/mapping.v1.yaml` with defaults and ID strategy definitions for method/assay/analyte projection workflows.
- Added addon mapping utilities under `src/addon_generator/mapping/` including safe field-path resolution, normalization helpers, projection/linkage resolution APIs, and strict config safety validation.
- Added the schema-driven **Protocol Generator GUI** wizard that authors `ProtocolFile.json` through `Step 1 General`, `Step 2 Loading`, and `Step 3 Processing`.
- Added lifecycle persistence with debounced autosave, temporary draft storage, startup draft recovery prompt, and atomic writes for target save paths.
- Added inline validation UX including per-step completion/error indicators, top-level progress summary, and first-invalid-field focus behavior.
- Added contextual help UX with per-step Help panels plus schema/metadata-backed field tooltips.
- Added packaging/build scaffolding (`pyproject.toml`, `build_windows_exe.ps1`) and CI-backed pytest coverage enforcement.
- Added canonical protocol JSON generator and generation service APIs (`import_from_excel`, `import_from_gui_payload`, `validate_domain`, `generate_analytes_xml`, `generate_protocol_json`, `generate_all`) with UI integration so Tkinter no longer assembles final JSON directly.

## Changed

- Changed wizard interaction flow to require **Save As** before progressing beyond Step 1 so autosave and subsequent edits target a user-selected file.
- Changed destructive workflow-step actions to explicit confirmation dialogs (**Confirm delete**, **Confirm reorder**) and added keyboard shortcuts (`Enter` to advance tab from entry fields, `Esc` to cancel pending autosave).
- Changed documentation set with a root README plus dedicated end-user and developer guides aligned to current command usage and UI labels.

## Fixed

- Fixed missing bundled-schema runtime failure by embedding `protocol.schema.json` into the PyInstaller build (`--add-data`) and adding schema path resolution logic that supports frozen execution (`sys._MEIPASS`).
- Fixed packaged app startup crash (`ImportError: attempted relative import with no known parent package`) by switching GUI entrypoint imports in `src/protocol_generator_gui/main.py` to absolute package imports.
- Fixed Windows EXE packaging by invoking PyInstaller with `python -m PyInstaller` in `build_windows_exe.ps1`, avoiding PATH-related `pyinstaller` command resolution failures.
- Fixed coverage gate reliability by excluding the Tkinter shell module from measured coverage while retaining test depth on schema, validation, persistence, and wizard logic modules.

## Changed

- Added a new addon domain package at `src/addon_generator/domain/` with typed models, deterministic ID/key assignment utilities, protocol fragment composition primitives, and structured validation issue containers for generation workflows.
- Changed test suite coverage to include dedicated unit tests for mapping mode behavior (`exact`, `normalized`, `alias_map`, `explicit_key`), ID assignment, and cross-file linkage validation.

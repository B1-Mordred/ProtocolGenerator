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

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.

- Changed wizard interaction flow to require **Save As** before progressing beyond Step 1 so autosave and subsequent edits target a user-selected file.
- Changed destructive workflow-step actions to explicit confirmation dialogs (**Confirm delete**, **Confirm reorder**) and added keyboard shortcuts (`Enter` to advance tab from entry fields, `Esc` to cancel pending autosave).
- Changed documentation set with a root README plus dedicated end-user and developer guides aligned to current command usage and UI labels.

## Fixed

- Fixed `config/mapping.v1.yaml` to use real YAML syntax and updated mapping loader fallback so YAML config remains loadable when PyYAML is unavailable.

- Fixed protocol generator to emit schema-complete minimal `ProtocolFile.json` sections (method, assay, loading, processing) so end-to-end generation validates against `protocol.schema.json`.

- Fixed missing bundled-schema runtime failure by embedding `protocol.schema.json` into the PyInstaller build (`--add-data`) and adding schema path resolution logic that supports frozen execution (`sys._MEIPASS`).
- Fixed packaged app startup crash (`ImportError: attempted relative import with no known parent package`) by switching GUI entrypoint imports in `src/protocol_generator_gui/main.py` to absolute package imports.
- Fixed Windows EXE packaging by invoking PyInstaller with `python -m PyInstaller` in `build_windows_exe.ps1`, avoiding PATH-related `pyinstaller` command resolution failures.
- Fixed coverage gate reliability by excluding the Tkinter shell module from measured coverage while retaining test depth on schema, validation, persistence, and wizard logic modules.

## Changed

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.

- Added a new addon domain package at `src/addon_generator/domain/` with typed models, deterministic ID/key assignment utilities, protocol fragment composition primitives, and structured validation issue containers for generation workflows.
- Changed test suite coverage to include dedicated unit tests for mapping mode behavior (`exact`, `normalized`, `alias_map`, `explicit_key`), ID assignment, and cross-file linkage validation.

## Unreleased

### Added
- Added fragment-definition domain contracts (`FragmentMetadata`, selectors, loader/renderer protocols) and deterministic selection logic for assay/loading/processing protocol fragments based on assay family, reagent, dilution, instrument, and config metadata.

- Added staged wizard workflow support for method setup, assay/analyte setup, import preview/conflicts, validation, and output preview/export, including required-conflict gating for progression/export.
- Added wizard-state draft serialize/restore support with canonical DTO adapter helpers and persisted conflict metadata.
- Added method validation (`Id`, `Version`, `DisplayName`) and assay/analyte relationship integrity warnings (orphan, duplicate, ambiguous mappings).
- Added import/output preview models surfacing imported vs current values, provenance hints, unresolved field blockers, and export target readiness messages.
- Added deterministic merge provenance output for protocol generation with required-field conflict/unresolved reporting and explicit precedence (`GUI > imported > config default > built-in default`).
### Changed
- Changed protocol JSON generation to resolve GUI workflow output via fragment definitions instead of direct placeholder lists, preserving deterministic precedence and schema-valid rendering.

- Strengthened addon validation and mapping checks: cross-file validation now detects missing method identity and duplicate assay/analyte/unit XML IDs in addition to broken refs; domain validation now flags empty assay lists, unsupported analyte/assay type combinations, missing analyte units, ambiguous aliases, and non-numeric method-version formats; mapping config validation now enforces section shape/typing and mode-specific semantics earlier in config loading.
- Improved `src/addon_generator/importers/excel_importer.py` with worksheet-specific parsing paths, deterministic layout/version column registries, canonical value coercion, and structured diagnostics (`rule_id`, `sheet`, `row`, `column`, `value`) for missing required columns and duplicate rows.
- Extended importer tests for valid workbook parsing, required-column validation, duplicate detection metadata, coercion edge cases, and importer-to-canonical integration flow through `GenerationService.import_from_excel`.
- Changed `src/addon_generator/importers/xml_importer.py` to enforce `AddOn.xsd` validation before conversion and to raise `XmlImportValidationError` on schema-invalid payloads, while preserving importer-only canonical mapping responsibilities.
- Added importer unit coverage for schema-valid XML, schema-invalid XML, and canonical equivalence between XML and overlapping Excel fixtures.

- Added `doc/implementation-plan.md`, an executable phased delivery plan that converts `doc/backlog.md` epics/tasks into concrete implementation steps, target files, and runnable validation commands.
- Added additive unit/integration coverage for deterministic field-path resolution, matching modes (`exact`, `normalized`, `alias_map`, `explicit_key`), stable ID assignment, domain/cross-file validators, and canonical generation golden fixtures for `Analytes.xml` and `ProtocolFile.json` outputs.

### Changed

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Changed test fixtures to enforce deterministic ordering and stable output diffs for addon XML/JSON generation.
- Changed `doc/implementation-plan.md` Task 1.4 to split E2.1–E2.5 execution details, add explicit E2.4 UI display areas, align acceptance criteria wording to backlog requirements, and enumerate E2.4 assertions in wizard/validation test plans.
### Added
- Added addon validation modules (`domain_validator`, `protocol_schema_validator`, `xsd_validator`, `cross_file_validator`) with hard-failure checks (linkage/ref/duplicate/uniqueness/schema/XSD) and warning-level quality checks, all returning structured issue metadata.
- Introduced `src/addon_generator/importers/` with Excel, GUI, and XML importers that normalize inputs into `AddonModel`/`ProtocolContextModel` and optionally attach loading/processing/dilution/reagent/calibrator/control context fragments for downstream generation (PR pending).

### Changed

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Refactored `GenerationService` import entrypoints to delegate domain mapping to the new importer layer (PR pending).

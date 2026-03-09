
### Changed
- Extended addon validation services to consume DTO/provenance context and emit entity-scoped errors with source-location hints; added checks for incompatible duplicate analyte scopes, unresolved `Parameter Set` assay links, hidden-vocab sample-prep actions, malformed/invalid dilution ratios, merged method identity requirements, and richer cross-file assay mismatch checks wired through `GenerationService.generate_all` before output writing.

# Changelog

## 2026-03-09

### Added
- Added workbook-template fixture scenarios for production workbook shape and edge cases (`production-shape`, `header-offset-and-checklist`, `invalid-hidden-vocab`) under `tests/fixtures/workbooks/`, plus index metadata for deterministic materialization and expectation tracking.
- Added workbook-template focused parser tests for successful import, header row detection, analyte/assay linkage, sample prep ordering, dilution parsing, checklist exclusion, and hidden-list vocabulary validation in `tests/unit/test_excel_workbook_parser.py`.
- Added workbook-template golden-output integration assertions for selected scenarios to verify stable `Analytes.xml` and `ProtocolFile.json` output under `tests/integration/test_addon_generation_pipeline.py`.

### Changed
- Changed CI and coverage gates to make `src/addon_generator` workbook/import-generation paths the primary quality gate by adding a dedicated pipeline test step and raising addon coverage threshold from 70 to 75.
- Changed developer test dependencies to include `openpyxl` so workbook fixture materialization and parser-path tests run in CI.

## Added

- Added `doc/canonical-model-reference.md` documenting core canonical addon entities (method/assay/analyte/unit/context/root), required-vs-optional fields, domain constraints, deterministic identity/defaulting semantics, and canonical-to-output projection rules; linked it from `doc/developer-guide.md`.

- Added `doc/mapping-config-reference.md` covering mapping-loader/validator top-level sections, validated field-path keys, value shapes, fallback precedence, alias-mode behavior, and deterministic ID assignment rules; linked it from `doc/developer-guide.md`.
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
- Added fragment resolver plugin modules under `src/addon_generator/fragments/resolvers/` plus `src/addon_generator/fragments/registry.py` to collect concern-specific protocol section contributions and feed centralized deterministic ordering in protocol JSON generation.
- Added typed mapping-schema models and a strict schema validation layer for addon mapping YAML (`src/addon_generator/config/models.py`, `src/addon_generator/config/schema_validator.py`), including actionable errors for unknown keys, invalid field paths, invalid enum/strategy modes, and missing mandatory sections.
- Added DTO-first addon input model modules (`input_models/dtos.py`, `input_models/provenance.py`) and canonical conversion boundary (`services/canonical_model_builder.py`) to centralize DTO→domain transformation.
- Added workbook-template Excel import parsing under `src/addon_generator/importers/excel/` with `workbook_parser.py` orchestration and dedicated basics/sample-prep/dilutions/analytes parsers using header-driven start detection, blank-row termination, `Hidden_Lists` vocabulary validation/normalization, and explicit ignore behavior for `AddOn CheckList`.
- Added `services/input_merge_service.py` with deterministic precedence ordering and structured conflict capture across multi-source DTO bundles.

### Changed
- Refactored `src/addon_generator/generators/protocol_json_generator.py` to consume registry-provided fragment contributions with centralized deterministic section merge/sort behavior while preserving legacy raw fragment definitions through the default resolver.
- Refactored Excel/XML/GUI importers to emit DTO bundles with provenance while preserving domain import entry points via the canonical model builder.
- Updated `GenerationService` import entry points to consume importer DTO bundles through the canonical builder/merge path.
- Added unit coverage for merge precedence/conflict behavior and canonical DTO-to-domain conversion.

### Changed
- Updated `doc/user-guide.md` to document the full 5-stage GUI workflow (import preview/conflicts, editing inputs, validation, output preview/export), align wording to current tab/button labels, and add blocker-focused troubleshooting and examples for validation/export failures.

### Added
- Expanded `doc/developer-guide.md` with end-to-end import → canonical model → generation flow, generator/validator internals, extension boundaries, and step-by-step contributor workflows for adding assay families and fragment templates; added `doc/canonical-model-reference.md` and linked both reference docs.
- Added addon-generation golden snapshot fixtures for representative GUI scenarios and canonical integration assertions for `Analytes.xml` and `ProtocolFile.json`, plus a documented update workflow (`scripts/update_addon_generation_goldens.py`).
- Added scenario-indexed integration workbook fixtures under `tests/fixtures/workbooks/` with index metadata (`tests/fixtures/index.json`) and docs (`tests/fixtures/README.md`) for valid and failure-path importer pipelines.
- Added deterministic addon package export support in `GenerationService.build_package`, including `<method-id>-<method-version>` folder naming, explicit collision handling (`error` and `increment`), overwrite policy enforcement, and temp-write + atomic move behavior for final artifact publishing.
- Added regression coverage for deterministic linkage and generation pipeline edge cases in `tests/unit/test_addon_determinism_and_linkage.py` and `tests/integration/test_addon_generation_pipeline.py` (ambiguity failures, multi-assay processing behavior, and multi-unit normalization).
- Added fragment-definition domain contracts (`FragmentMetadata`, selectors, loader/renderer protocols) and deterministic selection logic for assay/loading/processing protocol fragments based on assay family, reagent, dilution, instrument, and config metadata.

- Added staged wizard workflow support for method setup, assay/analyte setup, import preview/conflicts, validation, and output preview/export, including required-conflict gating for progression/export.
- Added wizard-state draft serialize/restore support with canonical DTO adapter helpers and persisted conflict metadata.
- Added method validation (`Id`, `Version`, `DisplayName`) and assay/analyte relationship integrity warnings (orphan, duplicate, ambiguous mappings).
- Added import/output preview models surfacing imported vs current values, provenance hints, unresolved field blockers, and export target readiness messages.
- Added deterministic merge provenance output for protocol generation with required-field conflict/unresolved reporting and explicit precedence (`GUI > imported > config default > built-in default`).
### Changed
- Changed coverage configuration and test commands to target `src/addon_generator`, publish `term-missing` output in local/CI runs, and enforce a focused non-trivial coverage gate (`--cov-fail-under=70`) for ongoing addon-generator development.
- Fixed protocol JSON assembly to preserve direct GUI workflow section payload arrays (`LoadingWorkflowSteps`, `ProcessingWorkflowSteps`) instead of treating each step as a fragment definition.
- Changed fixture consumption to a shared loader helper (`tests/fixture_loader.py`) so unit/integration tests materialize workbook scenarios consistently, including malformed-workbook handling and expected domain-error assertions.
- Changed canonical import/validation/generation boundaries to enforce explicit assay↔analyte constraints, normalize/expand multi-unit inputs, and render conditional protocol behavior for multi-assay methods (`SamplesLayoutType` + per-assay processing groups).
- Changed protocol JSON generation to resolve GUI workflow output via fragment definitions instead of direct placeholder lists, preserving deterministic precedence and schema-valid rendering.

- Strengthened addon validation and mapping checks: cross-file validation now detects missing method identity and duplicate assay/analyte/unit XML IDs in addition to broken refs; domain validation now flags empty assay lists, unsupported analyte/assay type combinations, missing analyte units, ambiguous aliases, and non-numeric method-version formats; mapping config validation now enforces section shape/typing and mode-specific semantics earlier in config loading.
- Improved `src/addon_generator/importers/excel_importer.py` with worksheet-specific parsing paths, deterministic layout/version column registries, canonical value coercion, and structured diagnostics (`rule_id`, `sheet`, `row`, `column`, `value`) for missing required columns and duplicate rows.
- Extended importer tests for valid workbook parsing, required-column validation, duplicate detection metadata, coercion edge cases, and importer-to-canonical integration flow through `GenerationService.import_from_excel`.
- Expanded workbook fixture coverage with importer layout variants (`v1-flat`, extra-column `v2-sheeted`, and historical unit delimiters) plus malformed scenarios with deterministic expected diagnostics, and added matrix assertions in `tests/unit/test_importers.py` for both success and failure-path metadata.
- Changed Excel workbook load failures to raise `ExcelImportValidationError` with deterministic `invalid-workbook` diagnostics instead of leaking parser-specific exceptions.
- Changed `src/addon_generator/importers/xml_importer.py` to enforce `AddOn.xsd` validation before conversion and to raise `XmlImportValidationError` on schema-invalid payloads, while preserving importer-only canonical mapping responsibilities.
- Added importer unit coverage for schema-valid XML, schema-invalid XML, and canonical equivalence between XML and overlapping Excel fixtures.

- Added `doc/implementation-plan.md`, an executable phased delivery plan that converts `doc/backlog.md` epics/tasks into concrete implementation steps, target files, and runnable validation commands.
- Added additive unit/integration coverage for deterministic field-path resolution, matching modes (`exact`, `normalized`, `alias_map`, `explicit_key`), stable ID assignment, domain/cross-file validators, and canonical generation golden fixtures for `Analytes.xml` and `ProtocolFile.json` outputs.

### Changed

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Changed test fixtures to enforce deterministic ordering and stable output diffs for addon XML/JSON generation.
- Changed `doc/implementation-plan.md` Task 1.4 to split E2.1–E2.5 execution details, add explicit E2.4 UI display areas, align acceptance criteria wording to backlog requirements, and enumerate E2.4 assertions in wizard/validation test plans.
### Added
- Added scenario-indexed integration workbook fixtures under `tests/fixtures/workbooks/` with index metadata (`tests/fixtures/index.json`) and docs (`tests/fixtures/README.md`) for valid and failure-path importer pipelines.
- Added addon validation modules (`domain_validator`, `protocol_schema_validator`, `xsd_validator`, `cross_file_validator`) with hard-failure checks (linkage/ref/duplicate/uniqueness/schema/XSD) and warning-level quality checks, all returning structured issue metadata.
- Introduced `src/addon_generator/importers/` with Excel, GUI, and XML importers that normalize inputs into `AddonModel`/`ProtocolContextModel` and optionally attach loading/processing/dilution/reagent/calibrator/control context fragments for downstream generation (PR pending).

### Changed

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Refactored `GenerationService` import entrypoints to delegate domain mapping to the new importer layer (PR pending).

## Unreleased

### Changed
- Refactored assay projection/import normalization so `protocol_type`, `protocol_display_name`, and `xml_name` remain independent by default, with explicit opt-in fallback behavior via a shared normalizer used by import/projection paths.

### Fixed
- Stopped emitting invalid `MethodInformation.SamplesLayoutType` (`SAMPLES_LAYOUT_SEPARATE`) during protocol generation; multi-assay output now uses schema-allowed values and mapping validation now rejects invalid `protocol_defaults.method_information.SamplesLayoutType`.

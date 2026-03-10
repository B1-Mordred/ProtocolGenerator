# Changelog

## 2026-03-10

### Changed
- Expanded UI shell status orchestration with computed app-state dimensions for validation staleness/currentness, preview staleness/currentness, export readiness/blocking, and draft dirty/saved state; updated status banner API/text and added focused transition tests for post-edit, post-validate, post-preview, post-export, and post-save/restore flows.
- Expanded GUI draft lifecycle handling to restore complete DTO bundles and provenance, persist export/preview payload metadata, track dirty/last-saved/restore state, and guard restore/close actions behind unsaved-change confirmation prompts; added roundtrip tests covering conflict-resolution and preview/validation stale-state reproduction after restore.
- Enhanced GUI preview flow with richer `PreviewState` snapshots (generated timestamp, error state, validation/export snapshots), structured preview summaries, failure-safe preview responses, per-tab copy controls, and preview status banners that highlight stale/current readiness and user-friendly generation errors.
- Refined GUI export orchestration to enforce validation gating before write attempts, keep Export actions disabled when blockers exist, and surface structured export outcomes (destination, written files, failure reasons, cleanup notes) directly in the Export screen.


### Added
- Expanded GUI regression coverage with new unit tests for Sample Prep, Dilutions, and Import Review interaction flows (add/edit/reorder/duplicate/delete, filter switching, resolution actions, navigation callbacks) plus sidebar badge-refresh assertions in shell navigation tests.
- Expanded UI integration coverage in `tests/integration/test_ui_authoring_flow.py` to exercise import review conflict handling, Sample Prep editing, validation/preview stale-flag lifecycle transitions, and post-preview stale re-triggering after edits.
- Added validation-service regression tests for issue-category assignment, severity/category counts, and export-blocking derivation; updated shell orchestration tests to assert the new validation summary/state wiring.
- Added export-service and shell orchestration regression tests for validation-blocked export state, successful export result rendering with written file paths, and failed export rendering with clear reason/cleanup messaging.

### Changed
- Refactored UI validation orchestration to classify issues into Import Issues, Domain Validation, Cross-file Validation, Schema/XSD Validation, Export Blockers, Warnings, and Info, with per-issue navigation targets and optional recommended actions.
- Expanded `ValidationState` with grouped issues, severity/category counters, `export_blocked`, and `last_validated_at`, and updated shell refresh logic/sidebar badges to consume the new state shape.

## 2026-03-09

### Added
- Added a new PySide6 business-oriented GUI package at `src/addon_generator/ui/` with modular shell/state/services/models/views/widgets structure, stale-aware validation/preview state handling, draft persistence service, and navigation-ready section scaffolding for Method, Assays, Analytes, Sample Prep, Dilutions, Import Review, Validation, Output Preview, and Export workflows.
- Added GUI-focused tests for shell navigation, state propagation, stale-preview defaults, draft save/restore, and an end-to-end UI orchestration flow (`import → edit → validate → preview → export`) under `tests/unit/ui/` and `tests/integration/test_ui_authoring_flow.py`.

### Fixed
- Fixed PySide6 shell dock-area wiring to use Qt dock enums and persist current sidebar section in `EditorState.selected_section_index` for reliable non-linear navigation restoration.
- Fixed UI import provenance mapping to emit stable location strings from `FieldProvenance` (`file:sheet:row:column`) instead of missing attributes.
- Fixed draft restore behavior to rebuild import/editor/preview/validation slices from saved JSON and preserve draft source path metadata for subsequent saves.
- Fixed export adapter test coverage by adding explicit validation-blocked export behavior assertions (`ExportService` now guarded by a focused unit test).
- Fixed the PySide6 shell to orchestrate Validate/Preview/Export/Draft actions through service adapters, keep sidebar issue badges synchronized, and enforce validation-gated export button state in the UI shell layer.
- Added shell orchestration tests for validate/preview/export state transitions and draft-based section restoration (`tests/unit/ui/test_shell_orchestration.py`).
- Fixed coverage-gate instability for backend-focused CI jobs by excluding the new PySide6 UI package (`src/addon_generator/ui/**`) from the addon coverage target until a Qt-enabled GUI test lane is enforced.
- Fixed UI Qt test collection on Linux runners missing system OpenGL/EGL libs by switching module guards from `importorskip("PySide6")` to runtime-safe `QApplication` import/skip handling.

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
- Added deterministic UI badge derivation for Sample Prep (issues + conflicts), Dilutions (issues + conflicts), Import Review (conflicts + unresolved required method fields), and Validation; `MainShell._refresh_status()` now updates section badges 3-6 after editor mutations and import-review resolutions, with regression tests covering count stability across state transitions.
- Refactored the Sample Prep UI to a split-pane table/detail editor backed by a screen-level view model with stable step IDs, explicit mutation APIs, provenance/status metadata, and required/invalid-action highlighting; edits now flow through editor overrides and merge recompute to mark validation/preview stale.
- Extended UI import/merge state and adapters to support structured sample-prep/dilution override caches, conflict/provenance lookup summaries, flattened import-review rows, and provenance source-label/location-text rendering for field-level sample-prep/dilution details.
- Changed addon protocol JSON generation to pass resolver output through a dedicated workflow assembler stage (`src/addon_generator/fragments/assembler.py`) that normalizes processing/loading schema shape, applies deterministic ordering, and enforces sequential group/step index and duration defaults.
- Stabilized canonical importer parity by adding shared DTO/domain normalization (trimmed text, optional `""` → `None`, empty-container cleanup) and canonical addon comparison helpers that exclude source-only metadata such as `source_metadata.provenance`; parity tests now compare normalized canonical forms and include explicit None/empty-string, assay-label normalization, and metadata-exclusion coverage.

### Added
- Added workbook-template fixture scenarios for production workbook shape and edge cases (`production-shape`, `header-offset-and-checklist`, `invalid-hidden-vocab`) under `tests/fixtures/workbooks/`, plus index metadata for deterministic materialization and expectation tracking.
- Added workbook-template focused parser tests for successful import, header row detection, analyte/assay linkage, sample prep ordering, dilution parsing, checklist exclusion, and hidden-list vocabulary validation in `tests/unit/test_excel_workbook_parser.py`.
- Added workbook-template golden-output integration assertions for selected scenarios to verify stable `Analytes.xml` and `ProtocolFile.json` output under `tests/integration/test_addon_generation_pipeline.py`.

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
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
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
- Refactored `src/addon_generator/generators/protocol_json_generator.py` to consume registry-provided fragment contributions with centralized deterministic section merge/sort behavior while preserving legacy raw fragment definitions through the default resolver.
- Refactored Excel/XML/GUI importers to emit DTO bundles with provenance while preserving domain import entry points via the canonical model builder.
- Updated `GenerationService` import entry points to consume importer DTO bundles through the canonical builder/merge path.
- Added unit coverage for merge precedence/conflict behavior and canonical DTO-to-domain conversion.

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
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
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
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
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Changed test fixtures to enforce deterministic ordering and stable output diffs for addon XML/JSON generation.
- Changed `doc/implementation-plan.md` Task 1.4 to split E2.1–E2.5 execution details, add explicit E2.4 UI display areas, align acceptance criteria wording to backlog requirements, and enumerate E2.4 assertions in wizard/validation test plans.
### Added
- Added scenario-indexed integration workbook fixtures under `tests/fixtures/workbooks/` with index metadata (`tests/fixtures/index.json`) and docs (`tests/fixtures/README.md`) for valid and failure-path importer pipelines.
- Added addon validation modules (`domain_validator`, `protocol_schema_validator`, `xsd_validator`, `cross_file_validator`) with hard-failure checks (linkage/ref/duplicate/uniqueness/schema/XSD) and warning-level quality checks, all returning structured issue metadata.
- Introduced `src/addon_generator/importers/` with Excel, GUI, and XML importers that normalize inputs into `AddonModel`/`ProtocolContextModel` and optionally attach loading/processing/dilution/reagent/calibrator/control context fragments for downstream generation (PR pending).

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.

- Changed addon generation architecture to canonical `AddonModel` + mapping resolver; generation now produces XSD-shaped `Analytes.xml` and method-linked `ProtocolFile.json` with deterministic IDs.
- Refactored `GenerationService` import entrypoints to delegate domain mapping to the new importer layer (PR pending).

## Unreleased

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
- Refactored the Dilutions UI into a split table/detail workflow backed by a screen-level view model with dilution CRUD/duplicate/reset operations, provenance/effective metadata, reference-used indicators, and incomplete/invalid-ratio validation states that flow through merge recomputation and stale preview/validation flags.
- Implemented an Import Review split layout with dedicated review-row modeling, filterable review states (All/Conflicts/Overrides/Missing Required/Imported Only), resolution actions, and owner-navigation callbacks that route through merge recomputation and stale validation/preview invalidation.

### Fixed
- Hardened `GenerationService._dto_bundle_from_addon()` to treat nullable source metadata collections (`sample_prep_steps`, `dilution_schemes`, `hidden_vocab`, `provenance`) as empty structures, preventing `NoneType` iteration crashes in generation flows.
- Corrected DTO bundle metadata type-guards so non-mapping `provenance`/`hidden_vocab` values are safely discarded instead of leaking invalid payload types into downstream validation.
- Fixed workbook-template Basics parsing identity tracking bug where assay duplicate detection overwrote method identity state, causing `AttributeError: 'tuple' object has no attribute 'get'` during import.
- Restored workbook-template parser parity by allowing sparse/blank interstitial rows (without terminating parsing), adding assay XML-name fallback (`Protocol Display Name` when `Xml Assay Name` is absent), and preserving unlinked v2 sheet records so expected domain linkage errors (`unknown-assay-key`, `assay-missing-analytes`, `unknown-analyte-key`) surface correctly.
- Fixed v2 workbook normalization to avoid auto-promoting analyte-only `AssayKey` values into assay definitions when assay identity fields are missing, restoring expected `unknown-assay-key` diagnostics for invalid linkage fixtures.
- Adjusted domain-validation issue ordering so analyte linkage failures (`unknown-assay-key`) are emitted before derived assay coverage fallout (`assay-missing-analytes`), restoring deterministic fixture error-order expectations.
- Updated `GenerationService` issue sorting to preserve insertion order within each severity/phase bucket, preventing alphabetical reordering from masking root-cause diagnostics (e.g., `unknown-assay-key` before `assay-missing-analytes`).
- Fixed v2 workbook normalization to avoid synthesizing analyte records from unit-only rows; dangling unit references now correctly surface `unknown-analyte-key` without introducing spurious `empty-analyte-name`/`unknown-assay-key` noise.
- Fixed Excel importer normalization and v2 sheet parsing regressions by restoring assay `xml_name` fallback from `ProtocolType` when `XmlAssayName` is absent and by continuing duplicate-row detection per sheet even after prior diagnostics are recorded.
- Restored Excel/XML canonical parity for flat workbook assays by applying fallback for `protocol_display_name` from `xml_name`/`protocol_type` during workbook row normalization when display labels are omitted.
- Updated workflow assembly so loading steps no longer emit empty `StepParameters` objects and fragment-only processing group descriptors remain deterministic without schema-breaking placeholder step payloads.
- Updated protocol JSON generator fragment rendering expectations to match the normalized loading-step contract (no empty parameter maps) and keep deterministic workflow merge assertions stable.
- Normalized canonical comparison semantics for importer parity by case-folding assay label fields, collapsing empty/whitespace-only strings to `None`, and excluding `source_metadata` from canonical equality checks so XML and Excel imports compare on entity content only.
- Reordered generation projection validation so cross-file consistency checks run before protocol schema validation, preserving expected domain-first and linkage-first issue code ordering in invalid fixture scenarios.
- Hardened workflow fragment assembly by preserving deterministic processing-step ordering with explicit `StepIndex` precedence, enforcing default duration fields, and omitting empty `StepParameters` payloads to keep fragment-composed protocol JSON schema compliant.

### Changed
- Enhanced GUI Validation screen with grouped/filterable issue navigation, detailed issue inspector, and validation-state-driven export-blocked/current messaging; added Qt unit tests for grouping/filtering/navigation callback behavior.
- Reordered `GenerationService.generate_all` validation into explicit phases (domain/structural, linkage, then projection/schema/cross-file), added deterministic issue sorting, and updated validators/tests so domain linkage errors consistently surface ahead of downstream projection fallout with stable ordering.
- Excel workbook-template sheet parsers now enforce deterministic duplicate detection per sheet with stable `duplicate-row` diagnostics and duplicate-key metadata: assay identity (`Basics`), analyte identity per assay (`Analytes`), dilution scheme name uniqueness (`Dilutions`), and sample-prep order/action uniqueness (`SamplePrep`); tests were expanded for workbook-template duplicate diagnostics.
- Refactored assay projection/import normalization so `protocol_type`, `protocol_display_name`, and `xml_name` remain independent by default, with explicit opt-in fallback behavior via a shared normalizer used by import/projection paths.

### Fixed
- Stopped emitting invalid `MethodInformation.SamplesLayoutType` (`SAMPLES_LAYOUT_SEPARATE`) during protocol generation; multi-assay output now uses schema-allowed values and mapping validation now rejects invalid `protocol_defaults.method_information.SamplesLayoutType`.
- Hardened Excel workbook parsing entrypoints to convert workbook open failures into `ExcelImportValidationError` diagnostics with stable rule taxonomy (`invalid-workbook-format`/`workbook-open-failed`) and debug-safe error metadata (`path`, `error_type`, `error_message`).

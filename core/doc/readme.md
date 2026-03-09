# Protocol Generator GUI

Desktop wizard application for building a `ProtocolFile.json` from `protocol.schema.json`.

## Run locally

```bash
python -m pip install -e .
protocol-generator-gui
```

## Features

- 5-stage wizard UI:
  - Method setup
  - Assay/analyte setup
  - Import preview/conflicts
  - Validation
  - Output preview/export
- Schema-driven rendering for required flags, primitive input types, minimum-constrained numeric fields, and `StepType` conditional parameter forms with required-first progressive disclosure for advanced options.
- Inline schema validation with completion/error counters, top-level progress indicator, and automatic focus on the first invalid field.
- Lifecycle-based saving with in-memory drafts before first file selection, temporary crash-recovery draft persistence, and debounced autosave-on-change (400ms).
- Mandatory save-path selection before leaving Step 1, atomic file persistence (`.tmp` write then replace), and explicit autosave status UI (`Saving…`, `Saved at HH:MM`, `Save failed`).
- Crash/restart recovery prompt to reopen the last temporary draft when present.
- Per-step help panel and per-field tooltips sourced from schema descriptions (with metadata fallback when unavailable).
- Destructive action safeguards (delete/reorder confirmation dialogs) and keyboard navigation (`Enter` advances tabs, `Esc` cancels pending autosave).
- Export to `ProtocolFile.json` with final schema validation.
- Addon-domain building blocks under `src/addon_generator/domain/` for deterministic internal identity handling (`method.key`, `assay.key`, `analyte.key`, `unit.key`), protocol fragment composition, and structured validation issue tracking.
- Addon mapping package under `src/addon_generator/mapping/` for v1 mapping-config loading/validation, safe dotted-path evaluation, normalization helpers, projection resolution across method/assay/analyte records, ID assignment, and cross-file linkage checks.
- Addon XML generation pipeline under `src/addon_generator/generators/`, `src/addon_generator/serialization/`, and `src/addon_generator/validation/` for deterministic analyte XML (`AddOn -> Assays -> Assay -> Analytes -> Analyte -> AnalyteUnits -> AnalyteUnit`) with required reference elements (`AddOnRef`, `AssayRef`, `AnalyteRef`) and pre-write XSD validation issue reporting.
- Addon validation modules under `src/addon_generator/validation/` for domain-level hard failures/warnings, protocol JSON Schema validation (`jsonschema`), AddOn XML XSD validation (`lxml`), and cross-file consistency checks that return structured issues (`severity`, `entity_keys`, `source_location`).
- Addon validation now consumes optional DTO/provenance context to emit entity-scoped issues with source hints, including duplicate analyte incompatible-scope detection, unresolved `Parameter Set` assay links, hidden-vocabulary sample-prep checks, dilution ratio/scheme validation, and merged method-identity requirements enforced in `GenerationService.generate_all` before artifact write.
- Domain/cross-file validation now also enforces method identity presence/consistency, duplicate XML key detection (assay/analyte/unit IDs), analyte-to-assay compatibility checks, analyte-unit presence, empty-assay guards, alias ambiguity detection, and method-version format constraints.
- Addon protocol JSON generation pipeline under `src/addon_generator/generators/protocol_generator.py` and `src/addon_generator/services/generation_service.py` that builds output strictly from canonical domain context plus explicit protocol fragments, with service entrypoints for GUI payload import, Excel import, domain validation, JSON/XML generation, and combined generation orchestration.
- Addon protocol merge resolution now emits deterministic field-level provenance (`field_provenance`), required-field conflict/unresolved summaries, and enforces explicit precedence for overrides (`GUI > imported fragments > config defaults > built-in defaults`) for UI/validation consumption.
- Addon fragment domain models now define metadata, loading, and rendering contracts and protocol generation deterministically selects workflow/assay fragments by assay family, reagent, dilution, instrument, and config context before merge resolution.
- Addon protocol fragment resolution is now plugin-style via `src/addon_generator/fragments/registry.py`, with concern-specific resolvers (default/sample-prep/dilution) that contribute section fragments before centralized deterministic merge ordering.
- Protocol JSON assembly now preserves direct GUI-provided workflow section arrays (`LoadingWorkflowSteps`, `ProcessingWorkflowSteps`) while still supporting fragment-wrapper selection metadata for advanced import paths.
- Addon importer package under `src/addon_generator/importers/` with `gui_mapper.py` (UI payload to canonical `AddonModel`/`ProtocolContextModel`), `excel_importer.py` (layout-aware worksheet parsing with deterministic column registries, type coercion, layout-version detection, and structured diagnostics for missing columns/duplicate rows/invalid workbook payloads), and `xml_importer.py` (AddOn XML import that validates against `AddOn.xsd` before mapping to the same canonical entities used by GUI/Excel paths) while keeping generation side effects outside the importer layer.
- Assay identity mapping now treats `protocol_type`, `protocol_display_name`, and `xml_name` as independent canonical fields; cross-field fallback is centralized in a single normalizer and only applied when a caller/config explicitly opts in (for example XML import deriving protocol fields from XML assay name).
- Addon Excel workbook-template import support under `src/addon_generator/importers/excel/` with a coordinating `workbook_parser.py` and header-driven sheet parsers (`basics_parser.py`, `sampleprep_parser.py`, `dilutions_parser.py`, `analytes_parser.py`) that detect table starts by labels, stop on blank rows, treat `AddOn CheckList` as read-only/ignored, and use `Hidden_Lists` vocabularies for normalization/validation before mapping to DTO bundles.
- Workbook-template QA fixtures now include production-shape and edge-case scenarios under `tests/fixtures/workbooks/`, with golden artifact assertions for `Analytes.xml` and `ProtocolFile.json` in integration coverage to keep workbook-import pipeline outputs stable.
- CI quality gates now prioritize addon pipeline paths by running workbook parser + addon generation integration tests before the full-suite coverage gate (`addon_generator` fail-under 75).
- Canonical validation/generation boundaries now enforce explicit assay↔analyte constraints, including hard failures for assays without analytes and ambiguous analyte-to-assay linkage (normalized-name collisions across assay keys).
- Canonical import processing now supports multi-unit expansion (e.g., `"mg/dL; mmol/L"`) and unit-name normalization for consistent downstream XML/domain handling.
- Protocol generation now applies conditional multi-assay behavior by generating per-assay processing groups and using a schema-valid `SamplesLayoutType` (`SAMPLES_LAYOUT_SPLIT` fallback or configured default) when multiple assays are present.
- Generation service package builder now exports deterministic addon bundles under `<method-id>-<method-version>/` containing `ProtocolFile.json`, `Analytes.xml`, and `package-metadata.json`, with configurable collision policies (`error`/`increment`), overwrite enforcement, and temp-write then atomic-move semantics for robust destination handling.

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
pytest --cov=addon_generator --cov-report=term-missing --cov-fail-under=70
```

- Test framework: `pytest` with `pytest-cov` coverage enforcement (`--cov-fail-under=70`) centered on `src/addon_generator`. Coverage output is published with `--cov-report=term-missing` so uncovered addon-generator lines are visible in local and CI runs.
- Unit tests cover schema parsing, dynamic field grouping, conditional `StepType` required-field behavior, and validation edge cases.
- Integration tests use a headless wizard-flow harness to verify transition guards, processing-step reorder/edit behavior, and autosave behavior after save-path selection (no Qt helpers are required because the app is Tkinter-based).
- Addon-generation tests now include deterministic field-path/linkage behavior, matching-mode/alias-map coverage, deterministic ID assignment checks, domain and cross-file validator checks, import-to-canonical integration scenarios, and golden fixture assertions for stable `Analytes.xml` and `ProtocolFile.json` outputs.
- Integration workbook fixtures under `tests/fixtures/workbooks/` are now scenario-indexed (`index.json` + `README.md`) covering minimal valid, single-assay, multi-assay, multi-analyte, alias-normalization, invalid cross-file linkage, invalid unit linkage, and malformed workbook cases, with shared test loader helpers in `tests/fixture_loader.py` for consistent fixture materialization across integration/unit suites.
- Golden snapshot workflow for addon generation outputs is documented in `tests/fixtures/README.md`; run `PYTHONPATH=src python scripts/update_addon_generation_goldens.py` to refresh fixtures when intentional output changes occur, then validate with `pytest -q -o addopts='' tests/integration/test_addon_generation_pipeline.py -k golden`.
- CI runs the same test command on push and pull requests via GitHub Actions.

## Addon domain package

`src/addon_generator/domain/` now includes:

- `models.py`: typed dataclass models (`AddonModel`, `MethodModel`, `AssayModel`, `AnalyteModel`, `AnalyteUnitModel`, `ProtocolContextModel`) with stable internal `key` identity fields separate from projection IDs.
- `ids.py`: deterministic key/ID helpers for repeatable assignment during protocol generation.
- `fragments.py`: protocol-fragment primitives and deterministic materialization helpers.
- `issues.py`: structured validation issue models with typed severity/source values.
- `mapping/field_path.py`: safe dotted/bracket path parser and accessor (`a.b[0].c`).
- `mapping/normalizers.py`: match normalizers (trim, whitespace collapse, case-fold) and combined normalized token generation.
- `mapping/config_loader.py`: v1 mapping config loader + safety validation (unknown modes, invalid paths, ambiguous projections, alias contradictions).
- `config/models.py` + `config/schema_validator.py`: typed mapping-schema models and strict YAML parsing/validation with actionable errors for unknown keys, invalid field-path syntax, unsupported modes/strategies, and missing required sections.
- `mapping/link_resolver.py`: projection APIs (`assign_ids`, `resolve_method_projection`, `resolve_assay_projection`, `resolve_analyte_projection`, `validate_cross_file_linkage`) supporting `exact`, `normalized`, `alias_map`, and `explicit_key` matching modes.
- `config/mapping.v1.yaml`: baseline v1 defaults and ID strategy configuration.


## AddOn generator backbone

Core now includes a canonical `addon_generator` pipeline:
- Mapping config `config/mapping.v1.yaml` is now authored in true YAML syntax; loader supports PyYAML and a built-in YAML fallback parser for environments without `yaml` installed.

- Protocol JSON generation now resolves schema-required `MethodInformation`, `AssayInformation`, and minimal valid Loading/Processing workflow defaults via mapping config fallback precedence.
- Importers map GUI/Excel/XML payloads to `AddonModel`
- `LinkResolver` assigns deterministic IDs from `config/mapping.v1.yaml`
- Generators emit both `ProtocolFile.json` and `Analytes.xml`
- Validation includes domain, XSD, protocol schema, and cross-file consistency checks

- Wizard state now tracks canonical DTO adapters and supports draft serialize/restore including import-conflict resolution context.
- Method editor now enforces `Id` / `Version` / `DisplayName` rules with live propagation into validation and preview stages.
- Import preview now shows imported/current values, unresolved required conflicts, provenance hints, and progression gating until required conflicts are resolved.
- Output stage previews `ProtocolFile.json` and `Analytes.xml` export readiness with blocker-aware messaging and target-selection requirements.

- Import ingestion is now DTO-first: Excel/XML/GUI importers emit `InputDTOBundle` payloads with field-level provenance metadata, then `InputMergeService` applies deterministic source precedence and conflict capture before `CanonicalModelBuilder` performs the single DTO→`AddonModel` conversion boundary used by `GenerationService`.

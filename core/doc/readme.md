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
- Addon-domain building blocks under `src/addon_generator/domain/` for deterministic internal identity handling (`method.key`, `assay.key`, `analyte.key`, `unit.key`), protocol fragment composition, and structured validation issue tracking.
- Addon mapping package under `src/addon_generator/mapping/` for v1 mapping-config loading/validation, safe dotted-path evaluation, normalization helpers, projection resolution across method/assay/analyte records, ID assignment, and cross-file linkage checks.
- Addon XML generation pipeline under `src/addon_generator/generators/`, `src/addon_generator/serialization/`, and `src/addon_generator/validation/` for deterministic analyte XML (`AddOn -> Assays -> Assay -> Analytes -> Analyte -> AnalyteUnits -> AnalyteUnit`) with required reference elements (`AddOnRef`, `AssayRef`, `AnalyteRef`) and pre-write XSD validation issue reporting.
- Addon validation modules under `src/addon_generator/validation/` for domain-level hard failures/warnings, protocol JSON Schema validation (`jsonschema`), AddOn XML XSD validation (`lxml`), and cross-file consistency checks that return structured issues (`severity`, `entity_keys`, `source_location`).
- Addon protocol JSON generation pipeline under `src/addon_generator/generators/protocol_generator.py` and `src/addon_generator/services/generation_service.py` that builds output strictly from canonical domain context plus explicit protocol fragments, with service entrypoints for GUI payload import, Excel import, domain validation, JSON/XML generation, and combined generation orchestration.
- Addon importer package under `src/addon_generator/importers/` with `gui_mapper.py` (UI payload to canonical `AddonModel`/`ProtocolContextModel`), `excel_importer.py` (legacy workbook-compatible row import baseline), and `xml_importer.py` (architecture-ready AddOn XML import) that can optionally capture loading/processing/dilution/reagent/calibrator/control context fragments without generating final XML/JSON in the importer layer.

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
- Addon-generation tests now include deterministic field-path/linkage behavior, matching-mode/alias-map coverage, deterministic ID assignment checks, domain and cross-file validator checks, import-to-canonical integration scenarios, and golden fixture assertions for stable `Analytes.xml` and `ProtocolFile.json` outputs.
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

# Protocol Generator GUI

Desktop wizard application for building a `ProtocolFile.json` from `protocol.schema.json`.

## Run locally

```bash
python -m pip install -e .
protocol-generator-gui
```

## Features

- Added deterministic runtime resource resolution via `addon_generator.runtime.resources.get_resource_path()`, and updated schema loading to use that helper so `protocol.schema.json` is resolved consistently in both source runs and PyInstaller bundles (`sys._MEIPASS`).
- Runtime user data is now stored in OS-specific application locations: Windows `%APPDATA%\AddOnAuthoringStudio` (drafts/settings) + `%LOCALAPPDATA%\AddOnAuthoringStudio\logs`, macOS `~/Library/Application Support/AddOnAuthoringStudio` + `~/Library/Logs/AddOnAuthoringStudio`, Linux `~/.config/AddOnAuthoringStudio` + `~/.local/state/AddOnAuthoringStudio/logs`; draft save defaults and app logging initialization now use these computed directories.
- The main shell now exposes a **Help** menu with `Check for Updates`, `Open Logs`, and `About`; update checks prompt users before staging installers, Open Logs opens the runtime log directory, and About displays app/build + draft/config schema versions from `addon_generator.__about__`.
- Added top-level **AddOn Data Entry** and **Data Review** menu workflows: users can choose `Enter Data Manually` or `Import Excel File`; manual mode now provides tabbed Basics/Kit Components/Dilutions/Analytes/Sample Prep entry with on-change autosave snapshots, and Data Review opens the Import Review editor for post-import/manual editing. Basics manual entry now focuses on kit/add-on metadata (Method ID/Version/Display Name removed; `Kit Name` added), the Kit Components tab now captures Product/Component/Parameter Set/Type/Container fields, and workbook-template import tolerates case/spacing variants in expected sheet names.
- Manual Sample Prep entry now removes the `Step Key` column, uses admin-configurable Action drop-down values, and constrains `Source`/`Destination` to unique `Kit Components` → `Component Name` values; the Admin menu now exposes dedicated per-list submenus for Kit Type, Container Type, Unit of Measurement, and Sample Prep Action vocabularies.
- Canonical app/build metadata now lives in `src/addon_generator/__about__.py` (`__app_name__`, `__version__`, `__company__`, `__draft_format_version__`, `__config_schema_version__`); UI shell title, package metadata payloads, and setuptools project version derive from this single source.
- App status model now exposes computed readiness/staleness/dirty indicators (`validation`, `preview`, `export`, `draft`) plus badge contributions; shell status refresh uses these dimensions to drive Validation/Preview/Export badges and a four-part status banner that updates across edit→validate→preview→export→save/restore transitions.
- Preview pipeline now returns structured metadata (`method_id`, `method_version`, assay/analyte/sample-prep/dilution counts, validation status, preview timestamp, export-readiness), captures generation timestamps/errors in `PreviewState`, and renders stale/current + readiness/error context in the Preview screen with copyable monospaced tab content.
- Validation service now classifies findings into Import/Domain/Cross-file/Schema/XSD/Export Blockers/Warnings/Info categories, emits severity/category counters plus export-blocked state, and stores grouped results with validation timestamps in UI `ValidationState` for shell badge/status refresh.
- Export workflow now includes destination browsing, explicit validate-before-export action, validation-gated export attempts, and an in-screen result panel that reports success/failure status, destination, written file paths, and cleanup guidance on partial failures.
- Validation view now uses a split issue browser/details panel with grouped category headers, severity/category/search filters, structured issue navigation targets to Method/Assays/Analytes/Sample Prep/Dilutions/Import Review, and state-driven export-readiness messaging sourced from `validation_state`.
- GUI test coverage now includes dedicated unit flows for Sample Prep, Dilutions, Import Review, and sidebar-badge refresh behavior, plus an expanded authoring integration scenario for conflict resolution and stale-preview lifecycle verification.
- New business-oriented PySide6 UI foundation under `src/addon_generator/ui/` with a `QMainWindow` shell, section navigation, stacked domain editors (Method/Assays/Analytes/Sample Prep/Dilutions/Import Review/Validation/Preview/Export), reusable widgets, UI state containers, and thin service adapters that orchestrate import→merge→validate→preview→export through backend services.
- Draft persistence now supports save/load/restore of editor selection, preview/validation state, and imported method identity metadata to continue unresolved work across sessions.
- Draft persistence now round-trips full `InputDTOBundle` content (assays/analytes/units/sample-prep/dilutions/fragments/vocab/provenance), tracks dirty + last-saved/restore metadata, persists preview payload/staleness + export settings, and prompts before destructive restore/close when unsaved changes are present.
- MainShell now wires toolbar actions and screen controls through injected UI service adapters (import/merge/validate/preview/export/draft), updates status/issue badges, disables export on validation blockers, and restores section selection from draft state.
- Toolbar draft actions now support user-selected save/recover paths (`Save Status`, `Recover from Draft`), and the Admin menu now includes a dedicated `Field Mapping` screen where users can maintain multiple mapping templates with target-field expressions (input/default/custom/concat).
- Admin → Field Mapping now validates row expressions inline with a dedicated Status column (`✅ Valid`, `❌ Error: ...`, `⚠️ Disabled row: ...`), enforces token/concat/delimiter syntax checks on edit, and blocks template save/activation when enabled rows are invalid.
- Admin → Field Mapping target/token pickers now group options by source domain (`Analytes.xml`, `AddOn.xml`, `ProtocolFile.json`, method/assay/analyte input groups), support searchable type-ahead filtering, and include per-option tooltips while preserving legacy serialized values in saved templates.
- Admin → Field Mapping template controls now include `Rename`, enforce template-name validation (trimmed, non-empty, unique, and reserved `Default` protection), auto-resolve duplicate clone/new names (`<name> Copy`, `<name> Copy 2`, ...), and require delete confirmation with active-template usage context.
- Recovering a draft now reapplies restored Admin drop-down configuration values (`Type`, `Container Type`, analyte `Unit of Measurement`, sample prep `Action`) to manual-entry editor combos immediately, without requiring users to open each Admin configuration dialog first.
- Draft recovery now supports a combined recovery JSON shape that includes canonical draft state plus an optional `manual_entry_snapshot`; when present, manual-entry method/kit components/dilutions/sample-prep payloads are merged into the restored bundle so recovery files remain compatible across status-draft and manual autosave sources.
- Admin → Field Mapping now auto-sizes the `Target Field` column and target selector widgets to content so long mapping targets remain visible without truncation; manual-entry table row hydration now clears stale combo/widget state before applying new rows so Product/Component/Parameter Set/Assay values do not shift across columns when editing repeatedly.
- Admin → Field Mapping now includes a read-only multi-tab preview pane (`Analytes.xml`, `AddOn.xml`, `ProtocolFile.json`) with resolved target/value pairs generated from in-memory `AppState` source data, placeholder rendering for missing sources (`<missing:...>`), warning tooltips (`No source value for input:...`), and an explicit `Refresh Preview` action for large templates.
- Import toolbar actions now prompt with native file pickers when no `excel_path`/`xml_path` is preconfigured, then persist the selected path into editor export settings before running the import flow.
- Sample Prep editor now uses a screen-scoped view model with stable step IDs, table/detail synchronization, per-field provenance metadata, explicit row mutation actions (add/delete/move/duplicate/reset), and validation surfacing for required fields and unsupported actions while routing all edits through editor overrides + merge recomputation.
- Dilutions editor now uses a screen-scoped view model with stable dilution IDs, split table/detail editing, per-field provenance/effective-value metadata, optional reference-used context badges, mutation actions (add/delete/duplicate/reset), and explicit status surfacing for incomplete or invalid-ratio schemes through override + merge recomputation.
- Import Review now uses a dedicated review-row model and split table/detail UI with conflict/override/missing/imported-only filters, row-level resolution actions (accept imported/keep override/revert default/clear override), provenance + normalization detail panel, and jump-to-owner navigation that re-targets section/entity context while forcing merge recomputation and stale preview/validation updates.
- AppState now derives stable badge counts for Sample Prep, Dilutions, Import Review, and Validation; MainShell refresh applies those counts to navigation indices 3-6 and editor/review mutations now trigger immediate status refresh so badges stay synchronized after local edits and conflict resolution.
- UI merge/import state now carries structured sample-prep and dilution override caches, persistent selection IDs, per-field manual-edit markers, flattened import-review rows, and richer provenance labels/location text for sample-prep and dilution review/detail rendering while keeping validation trigger boundaries unchanged.
- Coverage note: the addon coverage gate currently excludes `src/addon_generator/ui/**` for headless backend CI jobs; GUI behavior is validated by dedicated UI tests (`tests/unit/ui/`, `tests/integration/test_ui_authoring_flow.py`) and should move into a Qt-enabled CI lane.
- UI Qt tests now perform runtime-safe module-level skips when Qt shared libraries (for example `libEGL.so.1`) are unavailable on CI runners, avoiding hard collection failures while preserving GUI checks on capable environments.
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
- Generation validation is now phase-ordered (domain/structural → linkage → projection/schema/cross-file) and final issue lists are deterministically sorted by severity, phase, code, path, and provenance so linkage/root-cause failures appear before downstream fallout.
- Addon protocol JSON generation pipeline under `src/addon_generator/generators/protocol_generator.py` and `src/addon_generator/services/generation_service.py` that builds output strictly from canonical domain context plus explicit protocol fragments, with service entrypoints for GUI payload import, Excel import, domain validation, JSON/XML generation, and combined generation orchestration.
- Addon protocol merge resolution now emits deterministic field-level provenance (`field_provenance`), required-field conflict/unresolved summaries, and enforces explicit precedence for overrides (`GUI > imported fragments > config defaults > built-in defaults`) for UI/validation consumption.
- Addon fragment domain models now define metadata, loading, and rendering contracts and protocol generation deterministically selects workflow/assay fragments by assay family, reagent, dilution, instrument, and config context before merge resolution.
- Addon protocol fragment resolution is now plugin-style via `src/addon_generator/fragments/registry.py`, with concern-specific resolvers (default/sample-prep/dilution) that contribute section fragments before centralized deterministic merge ordering.
- Added a dedicated workflow assembly stage at `src/addon_generator/fragments/assembler.py` that runs after resolver collection to normalize loading/processing schema shape, enforce deterministic ordering, and assign stable sequential `GroupIndex`/`StepIndex` plus duration defaults.
- Protocol JSON assembly now preserves direct GUI-provided workflow section arrays (`LoadingWorkflowSteps`, `ProcessingWorkflowSteps`) while still supporting fragment-wrapper selection metadata for advanced import paths.
- Addon importer package under `src/addon_generator/importers/` with `gui_mapper.py` (UI payload to canonical `AddonModel`/`ProtocolContextModel`), `excel_importer.py` (layout-aware worksheet parsing with deterministic column registries, type coercion, layout-version detection, and structured diagnostics for missing columns/duplicate rows and workbook-open failures using stable taxonomy IDs such as `invalid-workbook-format`/`workbook-open-failed`), and `xml_importer.py` (AddOn XML import that validates against `AddOn.xsd` before mapping to the same canonical entities used by GUI/Excel paths) while keeping generation side effects outside the importer layer.
- Manual AddOn entry now preserves kit series/product values through GUI mapping, auto-sizes Kit Components columns to avoid truncated headers, and provides Admin-configurable drop-down vocabularies for kit `Type`, `Container Type (if Liquid)`, analyte `Unit of Measurement`, and analyte `Assay` options derived from unique Kit Components `Parameter Set Name` values.
- Assay identity mapping now treats `protocol_type`, `protocol_display_name`, and `xml_name` as independent canonical fields; cross-field fallback is centralized in a single normalizer and only applied when a caller/config explicitly opts in (for example XML import deriving protocol fields from XML assay name).
- Addon Excel workbook-template import support under `src/addon_generator/importers/excel/` with a coordinating `workbook_parser.py` and header-driven sheet parsers (`basics_parser.py`, `sampleprep_parser.py`, `dilutions_parser.py`, `analytes_parser.py`) that detect table starts by labels, stop on blank rows, treat `AddOn CheckList` as read-only/ignored, use `Hidden_Lists` vocabularies for normalization/validation, and enforce deterministic sheet-specific duplicate-row detection (assay identity in Basics, analyte-per-assay identity in Analytes, unique dilution names, duplicate sample-prep order/action pairs) with duplicate-key metadata diagnostics before mapping to DTO bundles.
- Workbook-template QA fixtures now include production-shape and edge-case scenarios under `tests/fixtures/workbooks/`, with golden artifact assertions for `Analytes.xml` and `ProtocolFile.json` in integration coverage to keep workbook-import pipeline outputs stable.
- CI quality gates now prioritize addon pipeline paths by running workbook parser + addon generation integration tests before the full-suite coverage gate (`addon_generator` fail-under 75).
- Canonical validation/generation boundaries now enforce explicit assay↔analyte constraints, including hard failures for assays without analytes and ambiguous analyte-to-assay linkage (normalized-name collisions across assay keys).
- Canonical import processing now supports multi-unit expansion (e.g., `"mg/dL; mmol/L"`) and unit-name normalization for consistent downstream XML/domain handling.
- Protocol generation now applies conditional multi-assay behavior by generating per-assay processing groups and using a schema-valid `SamplesLayoutType` (`SAMPLES_LAYOUT_SPLIT` fallback or configured default) when multiple assays are present.
- Generation service package builder now exports deterministic addon bundles under `<method-id>-<method-version>/` containing `ProtocolFile.json`, `Analytes.xml`, and `package-metadata.json`, with configurable collision policies (`error`/`increment`), overwrite enforcement, and temp-write then atomic-move semantics for robust destination handling.

## Build desktop bundles (spec-driven)

```powershell
./scripts/build_windows.ps1
```

```bash
./scripts/build_macos.sh
./scripts/build_linux.sh
```

All platform scripts call `python -m PyInstaller` against `build/pyinstaller/addon_authoring.spec` and produce one-folder (`COLLECT`) bundles.
The Windows build script also runs `python -m pip install -e .` first so desktop dependencies like PySide6 are available to PyInstaller during analysis.

The shared spec uses `src/addon_generator/ui/app.py` as the entry point and bundles runtime resources required by authoring/generation, including `protocol.schema.json`, `AddOn.xsd`, `config/mapping.v1.yaml`, fragment resources, canonical UI resources under `src/addon_generator/resources`, and deploy metadata/icon folders under `deploy/`.

`build_windows_exe.ps1` remains as a compatibility wrapper that forwards to `scripts/build_windows.ps1`.

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
- Canonical normalization now trims imported text values, collapses optional empty strings (`""`) to `None`, normalizes empty containers, and exposes canonical addon comparison helpers that intentionally exclude source-only metadata (for example `source_metadata.provenance`) so XML/Excel parity checks stay stable across importer-specific provenance differences.
- Generation/recovery hardening now treats nullable DTO source metadata collections as empty during bundle reconstruction, enforces strict mapping-only handling for `hidden_vocab`/`provenance`, and omits empty loading-step `StepParameters` in workflow assembly, preventing `NoneType` import regressions and schema-invalid fragment payloads.
- Workbook-template Basics parsing now preserves method identity metadata while computing duplicate assay keys, preventing tuple-vs-mapping crashes during template import flows.
- Workbook-template import now tolerates sparse blank rows in component sheets, falls back `Xml Assay Name` from `Protocol Display Name` when absent, and retains unlinked v2 records so domain linkage validators report precise cross-file diagnostics instead of collapsing into missing-method fallout.
- V2 row normalization now only materializes assay definitions when assay identity fields are present, so analyte-only dangling assay keys remain dangling and are surfaced by domain validators as linkage errors.
- Domain validation now reports direct analyte linkage errors before downstream assay coverage fallout for stable, root-cause-first diagnostics in invalid workbook scenarios.
- Generation issue sorting now keeps validation emission order inside each severity/phase class (instead of code alphabetization), preserving root-cause-first diagnostics in integration reports.
- V2 workbook normalization no longer creates placeholder analytes from unit-only rows, preserving precise invalid-unit diagnostics (`unknown-analyte-key`) and avoiding secondary noise issues.
- Excel row normalization now restores assay XML-name fallback from protocol type for flat layouts and v2 sheet parsing now evaluates duplicate-row diagnostics per sheet even when earlier sheets already emitted errors.
- Excel flat-row normalization now also restores missing assay display labels from XML/protocol identity fallback paths to keep canonical parity with XML imports when assay display columns are absent.
- Canonical addon comparison now case-normalizes assay label fields, treats empty strings as null-equivalent values, and ignores source-specific metadata so Excel/XML import parity checks compare only canonical entities.
- Generation projection checks now evaluate cross-file consistency before protocol JSON schema validation so domain/linkage issue ordering remains root-cause-first for invalid fixture scenarios.
- Workflow fragment assembly now keeps deterministic processing-step ordering with `StepIndex` precedence while still omitting empty `StepParameters` payloads and enforcing required duration defaults on generated processing steps.

- Added updater foundation under `src/addon_generator/update/` + `src/addon_generator/ui/services/update_service.py` with local-version discovery (`__about__.__version__`), HTTPS release-manifest fetch/parse, semantic-version comparison, platform artifact selection, SHA256 verification, installer launch, and restart handoff file generation; update-service failures are now returned as structured UI error payloads (`code`/`message`) and emitted through runtime logging for centralized diagnostics.
- Added deployment manifest assets at `deploy/manifests/update.schema.json` and `deploy/manifests/update.json`, plus `scripts/make_release_manifest.py` to build signed-channel manifests (version/channel/published-at/artifact URLs/SHA256) directly from produced installer artifacts.

# Implementation Plan (Executable Tasks)

This plan translates `doc/backlog.md` into execution-ready tasks with concrete deliverables, code touchpoints, and validation commands.

## Planning assumptions
- Prioritize backlog order: **P1 (E1, E2, E5)**, then **P2 (E3, E4, E6)**, then **P3 (E7, E8)**.
- Every implementation task includes tests and docs/changelog updates before completion.
- Use feature branches and merge only when task acceptance checks pass.

---

## Phase 1 — P1 Foundations (Import + GUI + Semantic validation)

### Task 1.1 — Production Excel importer (E1.1)
**Implementation steps**
1. Build worksheet-specific parsers under `src/addon_generator/importers/excel_importer.py` (or split into submodules).
2. Add deterministic column mapping registry and required-column enforcement.
3. Add normalization/coercion utilities for text/boolean/numeric/empty values.
4. Add duplicate-row and missing-column diagnostics with structured issue metadata.
5. Add workbook-layout version detection logic (if multiple layouts are present).

**Tests**
- Add/update `tests/unit/test_importers.py` with:
  - valid production-like workbook parse,
  - missing required columns,
  - duplicate detection,
  - coercion edge cases.
- Add integration coverage in `tests/integration/test_addon_generation_pipeline.py` for importer → canonical model path.

**Executable checks**
- `pytest tests/unit/test_importers.py -q`
- `pytest tests/integration/test_addon_generation_pipeline.py -q`

---

### Task 1.2 — XML import + XSD validation (E1.2)
**Implementation steps**
1. Extend `src/addon_generator/importers/xml_importer.py` to validate against `AddOn.xsd` pre-conversion.
2. Convert valid XML into the same canonical model entities used by GUI/Excel.
3. Keep XML import isolated from generation logic (import-only responsibilities).

**Tests**
- Add valid/invalid XML importer tests in `tests/unit/test_importers.py`:
  - success case,
  - schema-invalid XML case,
  - canonical-equivalence checks vs overlapping Excel fixtures.

**Executable checks**
- `pytest tests/unit/test_importers.py -q`

---

### Task 1.3 — Source merge rules and provenance (E1.3)
**Implementation steps**
1. Implement deterministic merge module (GUI > imported > config default > built-in default).
2. Track field-level provenance and conflicts in merge output.
3. Surface unresolved/conflicting fields for GUI consumption.

**Tests**
- Add unit tests for precedence, provenance, and deterministic output.
- Add one end-to-end integration test validating reproducible merged model.

**Executable checks**
- `pytest tests/unit/test_generation_service.py -q`
- `pytest tests/integration/test_addon_generation_pipeline.py -q`

---

### Task 1.4 — New GUI shell + editors + preview/export (E2.1–E2.5)
**Implementation steps**
1. Refactor `src/protocol_generator_gui/main.py` into task-oriented flow:
   - method setup,
   - assay/analyte setup,
   - import preview/conflicts,
   - validation,
   - output preview/export.
2. Bind GUI state to canonical DTO/model adapters; add serialize/restore draft support.
3. Add method editor fields + validation hooks.
4. Add assay/analyte editor with relationship integrity checks.
5. Add output preview panels for `Analytes.xml` and `ProtocolFile.json`.

**Tests**
- Extend `tests/test_wizard_logic.py`, `tests/integration/test_wizard_flow.py`, and `tests/test_validation.py` for navigation gating, required fields, conflict visibility, and export blocking.

**Executable checks**
- `pytest tests/test_wizard_logic.py tests/integration/test_wizard_flow.py tests/test_validation.py -q`

---

### Task 1.5 — Semantic validation layer completion (E5.1–E5.3)
**Implementation steps**
1. Extend `src/addon_generator/validation/cross_file_validator.py` for method identity, assay/analyte linkage, and duplicate key checks.
2. Extend `src/addon_generator/validation/domain_validator.py` for unsupported combinations, missing units, empty assay lists, alias ambiguity, and version format constraints.
3. Add mapping config validation enhancements in mapping validators/loaders.

**Tests**
- Add/expand tests in `tests/unit/test_addon_validators.py` and `tests/unit/mapping/test_mapping_components.py`.

**Executable checks**
- `pytest tests/unit/test_addon_validators.py tests/unit/mapping/test_mapping_components.py -q`

---

## Phase 2 — P2 Domain completion (Fragments + business rules + packaging)

### Task 2.1 — Fragment library + selection rules (E3.1–E3.4)
**Implementation steps**
1. Define fragment models in `src/addon_generator/domain/fragments.py` for metadata/loading/processing.
2. Move hard-coded generation placeholders to fragment-driven resolution in protocol generators.
3. Add selection rules by assay family/reagent/dilution/instrument/config.

**Tests**
- Add focused unit tests for fragment selection determinism and rendered workflow validity.

**Executable checks**
- `pytest tests/unit/test_protocol_json_generator.py tests/unit/test_addon_domain.py -q`

---

### Task 2.2 — Business rule completion (E4.1–E4.4)
**Implementation steps**
1. Encode assay↔analyte constraints, alias handling, and ambiguity failures.
2. Complete unit normalization + multi-unit support.
3. Implement conditional protocol sections and multi-assay behavior.

**Tests**
- Add regression tests for conditional sections and multi-assay linkage.

**Executable checks**
- `pytest tests/unit/test_addon_determinism_and_linkage.py tests/integration/test_addon_generation_pipeline.py -q`

---

### Task 2.3 — Export/package hardening (E6.1–E6.3)
**Implementation steps**
1. Add package builder in generation service for expected folder/artifact structure.
2. Implement deterministic naming/version rules and collision handling.
3. Add safe temp-write + move semantics and overwrite policies.

**Tests**
- Add integration tests for package layout determinism and overwrite behavior.

**Executable checks**
- `pytest tests/integration/test_addon_generation_pipeline.py -q`

---

## Phase 3 — P3 Safety net + maintainability (Regression + docs)

### Task 3.1 — Fixture corpus and golden/regression suites (E7.1–E7.4)
**Implementation steps**
1. Expand fixture set in `tests/fixtures/` for real-world and invalid patterns.
2. Add golden-output tests for exact XML/JSON outputs.
3. Add workbook-variant import regression tests.
4. Ensure coverage reports target `src/addon_generator` primarily.

**Executable checks**
- `pytest -q`
- `pytest --cov=src/addon_generator --cov-report=term-missing`

---

### Task 3.2 — Documentation completion (E8.1–E8.4)
**Implementation steps**
1. Update `doc/developer-guide.md` with import→model→generation architecture and extension guides.
2. Update `doc/user-guide.md` for import, edit, validate, export flows.
3. Add mapping config and canonical model references.
4. Keep `doc/changelog.md` updated per completed increments.

**Executable checks**
- `pytest -q` (doc-linked workflows remain validated by test suite)

---

## Cross-cutting Definition of Ready/Done per task

### Ready checklist
- Scope maps to backlog task IDs.
- Required fixtures identified.
- Capability/routing/API impact identified (if applicable).

### Done checklist
- Implementation merged with matching tests.
- `doc/changelog.md` updated with Added/Changed/Fixed entry.
- Relevant docs updated (`core/doc/readme.md`, `doc/user-guide.md`, `doc/developer-guide.md`, or plugin docs).
- Test commands above pass locally.
- No deterministic-output regressions.

---

## Recommended execution order (short form)
1. **E1.1 → E1.2 → E1.3** (solid canonical ingestion)
2. **E2.1–E2.5** (usable workflow UI)
3. **E5.1–E5.3** (semantic safety gates)
4. **E3 + E4 + E6** (domain completeness and packaging)
5. **E7 + E8** (regression armor and maintainability)

# Code/Logic Error Audit — March 19, 2026

## Scope
Ran the repository test suite to identify current code/logic regressions.

## Command
- `pytest -q`

## Result Summary
- **23 failed**
- **270 passed**
- **30 skipped**
- **6 warnings**
- Coverage gate still passes (**91.30%** vs required 75%).

## Primary Failure Clusters

### 1) Excel/Basics parsing identity regressions
Symptoms in tests indicate assay identity fields are being populated with unexpected values:
- `protocol_type` appears to be set to assay key values (e.g., `assay:min`) in some flows.
- Basics sheet parsing appears to prefer `assay_abbreviation` where tests expect `parameter_set_number` for assay keys.

Representative failing tests:
- `tests/integration/test_addon_generation_pipeline.py::test_excel_import_pipeline_flow_with_sheeted_layout`
- `tests/unit/test_basics_parser.py::{...multiple failures...}`

Likely code areas:
- `src/addon_generator/importers/excel/basics_parser.py`
- `src/addon_generator/importers/excel_importer.py`

---

### 2) Protocol JSON assay assembly not preserving expected structure/overrides
`AssayInformation` output differs from golden expectations and schema-oriented assembly tests:
- Golden comparisons show unexpected minimal `{"Type": ...}` records where richer expected structures should appear.
- Wizard JSON assembly tests fail schema validation due missing required assay properties.

Representative failing tests:
- `tests/unit/test_json_assembly.py::{...3 failures...}`
- `tests/integration/test_addon_generation_pipeline.py::test_workbook_template_scenarios_match_golden_outputs[...]`

Likely code areas:
- `src/addon_generator/generators/protocol_json_generator.py`
- `src/addon_generator/fragments/assembler.py`

---

### 3) UI service dependency injection / test seam breakage
Unit tests patch `service._service` but runtime path appears to instantiate or route around that seam:
- Errors include missing `_service` attribute in export service tests.
- Validation tests trigger real generation paths and fail with attribute errors when dummy objects are passed.

Representative failing tests:
- `tests/unit/ui/test_export_service.py::{...3 failures...}`
- `tests/unit/ui/test_validation_service.py::{...3 failures...}`

Likely code areas:
- `src/addon_generator/ui/services/export_service.py`
- `src/addon_generator/ui/services/validation_service.py`

---

### 4) XML method version and deterministic linkage expectation mismatch
A determinism test expects blank `<MethodVersion>` while generated XML currently emits method version content.

Representative failing test:
- `tests/unit/test_addon_determinism_and_linkage.py::test_method_linkage_and_ids_are_deterministic`

Likely code area:
- `src/addon_generator/generators/analytes_xml_generator.py`

---

### 5) Assay grouping normalization side-effects in preview/export parity
Preview/export grouping test shows casing/group-key normalization mismatch (e.g., `chemistry` vs `Chemistry` buckets).

Representative failing test:
- `tests/unit/ui/test_ui_state_and_services.py::test_preview_and_export_keep_default_ruleset_assay_grouping_for_manual_analytes`

Likely code area:
- `src/addon_generator/services/generation_service.py`

## Recommended Next Steps
1. Fix Basics parser key precedence and header mapping behavior first, then rerun parser + pipeline tests.
2. Fix assay merge/precedence logic in protocol JSON assembly and rerun JSON assembly + golden tests.
3. Restore stable injection seams in UI services (`_service` usage expectations) and rerun UI unit tests.
4. Reconcile `<MethodVersion>` expected behavior (test vs implementation) and align spec/tests.
5. Re-run full suite and refresh this audit after each cluster fix.

## Resolution Update — March 19, 2026 (post-fix)

- Re-ran the full suite after implementing the parser, protocol-assembly, UI-service seam, XML output, and fixture/golden updates.
- Current status:
  - **293 passed**
  - **30 skipped**
  - **0 failed**
  - Coverage gate still passing (**91.28%**).

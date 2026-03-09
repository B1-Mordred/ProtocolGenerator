# Integration workbook fixtures

This directory groups workbook fixture sets used by importer/generation integration tests.

## Structure

- `index.json`: scenario catalog, intent metadata, and expected pipeline outcomes.
- `workbooks/<scenario>/workbook.json`: declarative worksheet content used to build an `.xlsx` at test runtime.
- `workbooks/malformed-workbook/not-a-workbook.xlsx`: intentionally invalid workbook payload.

## Scenarios

- `minimal-valid`: baseline valid workbook.
- `single-assay`: one assay, multiple analytes.
- `multi-assay`: two assays for multi-group processing behavior.
- `multi-analyte`: one assay with many analytes.
- `alias-driven-mapping`: unit alias normalization and split coverage (`mg/dl; ug/ml`).
- `invalid-cross-file-mapping`: analyte references unknown assay key.
- `invalid-units`: unit references unknown analyte key.
- `malformed-workbook`: unreadable `.xlsx` binary.

Expected outcomes are encoded in `index.json` and consumed by `tests/fixture_loader.py`.


## Golden snapshot workflow

Addon generation integration tests compare canonicalized generator output against committed golden files under `tests/fixtures/golden/addon-generation/<scenario>/`.

When generator output changes intentionally:

1. Regenerate fixture outputs from representative GUI payload scenarios:
   ```bash
   PYTHONPATH=src python scripts/update_addon_generation_goldens.py
   ```
2. Run the focused integration snapshot test and review diffs:
   ```bash
   pytest -q -o addopts='' tests/integration/test_addon_generation_pipeline.py -k golden
   ```
3. Include updated golden files in the same commit so changes remain reviewable in PR diffs.

Notes:
- `ProtocolFile.json` snapshots are stored as sorted, indented JSON with trailing newline for stable byte-for-byte comparisons.
- `Analytes.xml` assertions use canonical XML parse/serialize comparison to avoid false negatives from formatting-only differences.

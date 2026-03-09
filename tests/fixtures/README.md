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

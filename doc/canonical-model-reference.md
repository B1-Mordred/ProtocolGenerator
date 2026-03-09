# Canonical Model Reference

This document defines the canonical addon domain model used between importers and generators.

## 1) Purpose

The canonical model provides a stable internal contract so multiple import sources (Excel/XML/GUI) can converge into one representation before generation.

Primary definition: `src/addon_generator/domain/models.py`.

## 2) Root aggregate: `AddonModel`

`AddonModel` fields:

- `addon_id: int` — AddOn root identifier.
- `method: MethodModel | None` — method-level identity and display metadata.
- `assays: list[AssayModel]` — assay entities.
- `analytes: list[AnalyteModel]` — analyte entities.
- `units: list[AnalyteUnitModel]` — analyte-unit entities.
- `sample_tube_types: list[dict[str, Any]]` — optional protocol context payloads.
- `measurement_sample_lists: list[dict[str, Any]]` — optional protocol context payloads.
- `run_results_export_path: str | None` — optional protocol metadata.
- `protocol_context: ProtocolContextModel | None` — optional protocol fragment container.
- `source_metadata: dict[str, Any]` — importer provenance/source annotations.

## 3) Entity reference

### 3.1 `MethodModel`

Identity and display metadata projected into XML and protocol JSON:

- Required identity: `key`, `method_id`, `method_version`
- Optional display metadata includes `display_name`, `main_title`, `sub_title`, `order_number`, `series_name`, `product_name`, `product_number`, `legacy_protocol_id`.

### 3.2 `AssayModel`

Assay identity and cross-output linkage fields:

- Core identity: `key`
- Projection/linkage fields: `xml_id`, `protocol_type`, `xml_name`, `addon_ref`
- UX/source fields: `source_row_id`, `display_name`, `protocol_display_name`
- Relationship and extension fields: `aliases`, `analyte_keys`, `metadata`

### 3.3 `AnalyteModel`

Analyte identity, assay linkage, and projection metadata:

- Required: `key`, `name`, `assay_key`
- Projection fields: `xml_id`, `assay_ref`, `assay_information_type`
- Relationship/extension fields: `unit_keys`, `metadata`

### 3.4 `AnalyteUnitModel`

Analyte unit identity and analyte linkage:

- Required: `key`, `name`, `analyte_key`
- Projection fields: `xml_id`, `analyte_ref`
- Extension fields: `metadata`

### 3.5 `ProtocolContextModel`

Container for protocol JSON fragments and method overrides:

- `method_information_overrides`
- `assay_fragments`
- `loading_fragments`
- `processing_fragments`
- `dilution_fragments`
- `reagent_fragments`
- `calibrator_fragments`
- `control_fragments`

## 4) Identity and linkage semantics

- `key` fields are canonical internal identities (source-independent).
- `*_id`/`*_ref` fields are projection-layer identifiers used in generated outputs.
- Linkage is enforced through:
  - `AnalyteModel.assay_key` → `AssayModel.key`
  - `AnalyteUnitModel.analyte_key` → `AnalyteModel.key`
- Deterministic numeric IDs are assigned by mapping + resolver rules before generation.

## 5) Lifecycle through the pipeline

1. Importers parse source payloads into canonical entities.
2. Resolver assigns deterministic IDs and method/assay projections.
3. Validators assert canonical and cross-projection consistency.
4. Generators emit schema-shaped artifacts.

## 6) Extension guidance

When adding fields/entities:

1. Extend canonical dataclasses first.
2. Update importer mapping to populate new fields.
3. Update generators only for projection-relevant fields.
4. Add or update validator rules for new invariants.
5. Extend tests and fixtures for deterministic output and validation coverage.

## 7) Related references

- [Developer Guide](./developer-guide.md)
- [Mapping Config Reference](./mapping-config-reference.md)

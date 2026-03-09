# Developer Guide

This guide documents the end-to-end architecture for addon generation, from importers to canonical model to generated artifacts. It also defines extension boundaries, validator internals, and implementation workflows for adding new assay families and protocol fragments.

## 1) End-to-end flow: import → canonical model → generation

The addon pipeline uses a strict three-stage flow:

1. **Import stage** (source-specific parsing)
   - Excel: `src/addon_generator/importers/excel_importer.py`
   - XML: `src/addon_generator/importers/xml_importer.py`
   - GUI payload: `src/addon_generator/importers/gui_mapper.py`
2. **Canonical stage** (normalized domain model)
   - `AddonModel` and child entities in `src/addon_generator/domain/models.py`
3. **Generation stage** (artifact projection)
   - `Analytes.xml`: `src/addon_generator/generators/analytes_xml_generator.py`
   - `ProtocolFile.json`: `src/addon_generator/generators/protocol_json_generator.py`

`GenerationService` in `src/addon_generator/services/generation_service.py` orchestrates this flow and is the preferred entry point for integration code.

### Runtime sequence (generation)

1. Build/load canonical `AddonModel` using importer APIs.
2. Resolve mapping config and deterministic IDs via `LinkResolver`.
3. Run domain + cross-file + schema/XSD validators.
4. Generate XML and protocol JSON projections.
5. Return artifacts plus structured issues and merge provenance report.

## 2) Canonical model boundaries and extension rules

The canonical model is the contract between importers and generators. Importers may be source-specific; generators must remain source-agnostic.

- **Importer boundary:** normalize source data into canonical entities; do not emit generation-format payloads.
- **Canonical boundary:** all business identity/linkage semantics live in `AddonModel` graph.
- **Generator boundary:** only read canonical model + mapping/default config; do not parse source-specific formats.
- **Validator boundary:** validators report structured issues and should not mutate canonical state.

For full entity reference, see [Canonical Model Reference](./canonical-model-reference.md).
For mapping-path and matching config behavior, see [Mapping Config Reference](./mapping-config-reference.md).

## 3) Generator internals

### 3.1 `Analytes.xml` generator internals

`generate_analytes_addon_xml`:

- Requires `AddonModel.method`.
- Emits AddOn root with method identity.
- Groups analytes by `assay_key`, units by `analyte_key`.
- Sorts assays/analytes/units deterministically (ID-first, then key fallback).
- Performs XSD validation before writing output path.
- Returns XML + `ValidationIssueCollection` (warnings/errors) rather than throwing for validation issues.

### 3.2 `ProtocolFile.json` generator internals

`generate_protocol_json`:

- Uses `LinkResolver` projection APIs for method/assay mappings.
- Merges method information from GUI/imported/config/built-in defaults with provenance tracking.
- Produces merge report containing unresolved/conflicting required fields.
- Emits protocol sections and optional context fragments from `ProtocolContextModel`.

### 3.3 Service orchestration

`GenerationService.generate_all`:

- Assigns IDs once through resolver.
- Runs validators in layers (domain, cross-file, protocol schema, XSD).
- Returns a single structured `GenerationResult` containing artifacts, issues, warnings, mapping snapshot, and merge diagnostics.

## 4) Validator architecture

Validation is layered to isolate concerns and improve diagnostics:

1. **Domain validator** (`validation/domain_validator.py`)
   - Entity-level canonical invariants (required fields, duplicates, alias normalization, linkage assumptions).
2. **Cross-file validator** (`validation/cross_file_validator.py`)
   - Consistency between protocol projection and analytes projection.
3. **Protocol schema validator** (`validation/protocol_schema_validator.py`)
   - JSON Schema conformance for protocol JSON.
4. **XSD validator** (`validation/xsd_validator.py`)
   - XML schema conformance for `Analytes.xml`.

All validator outputs are normalized into issue collections with metadata (severity, rule identifiers, and contextual paths/fields where available).

## 5) Extension points

### 5.1 Import extension points

- Add new source importers under `src/addon_generator/importers/`.
- Convert source records to canonical entities only.
- Reuse shared normalization/parsing helpers where possible.

### 5.2 Mapping extension points

- Extend `config/mapping.v1.yaml` with new safe mapping keys.
- Update mapping loader/path validation when adding new validated field-path keys.
- Keep matching modes and fallback rules deterministic.

### 5.3 Generation extension points

- Add projection logic to generators without embedding source-specific assumptions.
- Keep sort order deterministic for stable outputs and test fixtures.
- Extend `ProtocolContextModel` when new fragment families are needed.

### 5.4 Validation extension points

- Add new validators for orthogonal concerns.
- Keep each validator pure (read-only canonical/projection input).
- Return structured issues, not ad-hoc exceptions for expected validation failures.

## 6) Workflow: add a new assay family

Use this workflow when introducing a new assay type/category with distinct mapping or projection behavior.

1. **Define canonical semantics**
   - Confirm assay identity keys, aliases, and required metadata in canonical terms.
   - Update `AssayModel.metadata` usage docs when needed.
2. **Importer updates**
   - Map source fields for the new family into canonical assay/analyte relationships.
   - Add coercion/normalization rules and diagnostics for missing/invalid family-specific fields.
3. **Mapping config updates**
   - Add mapping keys in `config/mapping.v1.yaml` if family-specific projections are required.
   - Update mapping loader validation for any new required field-path keys.
4. **Resolver updates**
   - Extend `LinkResolver` matching/projection behavior if linkage strategy differs.
5. **Generator updates**
   - Ensure XML/JSON output includes family-specific projections while preserving deterministic ordering.
6. **Validator updates**
   - Add/extend rules for family-specific invariants (identity uniqueness, linkage completeness, name/alias conflicts).
7. **Tests**
   - Add unit tests for importer mapping, resolver logic, and validators.
   - Add integration fixture/golden coverage for full pipeline outputs.
8. **Docs**
   - Update this guide, canonical reference, and mapping reference if contract changed.

## 7) Workflow: add a new fragment template

Use this when introducing a new protocol context fragment category (for example a new processing fragment template type).

1. **Model layer**
   - Add a typed container/list in `ProtocolContextModel` if a new fragment family is needed.
2. **Importer layer**
   - Populate canonical fragment entries from supported sources (GUI/Excel/XML where applicable).
3. **Merge/provenance logic**
   - Update protocol generator merge selection rules if fragment fields participate in precedence.
4. **Generator projection**
   - Add fragment emission in protocol JSON structure at the correct section path.
5. **Validation**
   - Add schema/domain checks for required fragment attributes and supported value ranges.
6. **Fixtures/tests**
   - Add unit tests for merge/projection behavior and edge cases.
   - Add integration fixtures proving end-to-end output shape.
7. **Documentation**
   - Document fragment schema and precedence behavior in canonical/mapping references as needed.

## 8) Related references

- [Mapping Config Reference](./mapping-config-reference.md)
- [Canonical Model Reference](./canonical-model-reference.md)
- `doc/implementation-plan.md` (execution/task context)

## 9) Contribution checklist

- Keep docs aligned with runtime behavior and generated artifact structure.
- Add/update tests when logic changes.
- Update `doc/changelog.md` for user-visible behavior or contract updates.
For mapping-loader/validator-consumed config sections, field-path rules, matching modes, fallback behavior, and ID assignment semantics, see `doc/mapping-config-reference.md`.

For canonical addon entities, required vs optional fields, identity/defaulting semantics, and projection-to-output rules, see `doc/canonical-model-reference.md`.

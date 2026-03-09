# Mapping Config Reference (`config/mapping.v1.yaml`)

This reference documents the mapping config contract consumed by:

- `src/addon_generator/mapping/config_loader.py` (load + structural validation)
- `src/addon_generator/mapping/field_path.py` (field-path syntax/lookup behavior)
- `src/addon_generator/mapping/link_resolver.py` (ID assignment + assay cross-file checks)
- `src/addon_generator/generators/protocol_json_generator.py` (`protocol_defaults` fallbacks)

## 1) Top-level sections

`version` (required)
- Type: integer
- Required value: `1`

`ids` (required)
- Type: object
- Required child sections: `assay`, `analyte`, `analyte_unit`
- `ids.addon` may exist in YAML for readability, but loader/validators currently do not consume it.

`method_mapping` (required)
- Type: object
- Required child sections: `protocol`, `analytes_xml`

`assay_mapping` (required)
- Type: object
- Required child sections: `internal_identity`, `protocol`, `analytes_xml`
- Optional child section: `cross_file_match` (defaults to `{}`; mode defaults to `exact`)

`analyte_mapping` (required)
- Type: object
- Required child section: `analytes_xml`

`unit_mapping` (required)
- Type: object
- Required child section: `analytes_xml`

`protocol_defaults` (optional)
- Type: object when present
- Used by protocol JSON generation defaults/fallback logic.

## 2) Valid field paths

All mapping path values validated as field paths must follow `parse_field_path` rules:

- Must be a non-empty, trimmed string.
- Dot notation for object keys: `method.method_id`
- Bracket notation for list indices: `a.b[0].c`
- Indices must be non-negative digits inside `[]`.
- Empty segments / malformed brackets are invalid.

Lookup behavior (`get_field_value`) for a valid field path:

- Missing key, wrong container type, or out-of-range index returns the supplied default (`None` if omitted).
- Strings/bytes are not treated as indexable sequences in path traversal.

### Field-path keys that are currently validated

`method_mapping`
- `protocol.id`
- `protocol.version`
- `analytes_xml.method_id`
- `analytes_xml.method_version`

`assay_mapping`
- `internal_identity`
- `protocol.type`
- `analytes_xml.name`
- `cross_file_match.protocol_field` (required only in `explicit_key` mode)
- `cross_file_match.analytes_xml_field` (required only in `explicit_key` mode)

`analyte_mapping.analytes_xml`
- `id`
- `name`
- `assay_ref`

`unit_mapping.analytes_xml`
- `id`
- `name`
- `analyte_ref`

Note: additional YAML keys (for example `assay_mapping.protocol.display_name` or `analyte_mapping.analytes_xml.assay_information_type`) may exist and be consumed elsewhere, but they are not syntax-validated by `validate_mapping_config`.

## 3) Section-by-section value shapes

## `ids`

Required sub-objects and constraints:

- `ids.assay.strategy`: must be the literal string `sequential`
- `ids.assay.start`: non-negative integer
- `ids.analyte.strategy`: must be `sequential`
- `ids.analyte.start`: non-negative integer
- `ids.analyte_unit.strategy`: must be `sequential`
- `ids.analyte_unit.start`: non-negative integer

## `method_mapping`

- `method_mapping.protocol`: object
  - `id`: non-empty field-path string
  - `version`: non-empty field-path string
- `method_mapping.analytes_xml`: object
  - `method_id`: non-empty field-path string
  - `method_version`: non-empty field-path string

## `assay_mapping`

- `assay_mapping.internal_identity`: non-empty field-path string
- `assay_mapping.protocol`: object
  - `type`: non-empty field-path string
- `assay_mapping.analytes_xml`: object
  - `name`: non-empty field-path string
- `assay_mapping.cross_file_match`: object (optional)
  - `mode`: one of `exact | normalized | alias_map | explicit_key` (default `exact`)
  - if `mode == alias_map`:
    - `alias_map`: required non-empty object
    - each key/value must be non-empty string
  - if `mode == explicit_key`:
    - `protocol_field`: required valid field path
    - `analytes_xml_field`: required valid field path

## `analyte_mapping`

- `analyte_mapping.analytes_xml`: object
  - `id`: non-empty field-path string
  - `name`: non-empty field-path string
  - `assay_ref`: non-empty field-path string

## `unit_mapping`

- `unit_mapping.analytes_xml`: object
  - `id`: non-empty field-path string
  - `name`: non-empty field-path string
  - `analyte_ref`: non-empty field-path string

## `protocol_defaults`

- If present, must be an object.
- `protocol_defaults.loading_workflow_steps` is additionally type-checked as a list when provided.
- Other nested defaults are consumed by protocol generation as plain dictionaries/lists and are not schema-validated at mapping-load time.

## 4) Fallback and precedence behavior

## Mapping-load fallback

- `assay_mapping.cross_file_match` defaults to `{}` if omitted.
- `assay_mapping.cross_file_match.mode` defaults to `exact` if omitted.
- `protocol_defaults` defaults to `{}` if omitted.

## Protocol JSON generation fallback (`protocol_defaults` + runtime sources)

For `MethodInformation` fields, precedence is:

1. GUI overrides
2. Imported protocol fragments
3. Generated values from canonical addon model
4. Config defaults (`protocol_defaults.method_information`)
5. Built-in hard defaults

For section payloads (`AssayInformation`, `LoadingWorkflowSteps`, `ProcessingWorkflowSteps`), precedence is:

1. GUI fragment/direct payload
2. Imported section payload
3. Config defaults (`protocol_defaults.*`)
4. Built-in defaults

Required single-field fallback helper behavior:

- `_resolve_required_default(primary, fallback, hard_default)` chooses first non-empty (after string trim check) among primary → fallback → hard default.

## 5) Alias handling and matching modes

`assay_mapping.cross_file_match.mode` controls linkage semantics expectations:

- `exact`: protocol assay type must equal XML assay name exactly.
- `normalized`: values are compared after normalization (`normalize_for_matching`).
- `alias_map`: loader validates alias-map shape; runtime linkage currently does not apply alias substitutions in `LinkResolver.validate_cross_file_linkage`.
- `explicit_key`: loader validates explicit key-field paths; runtime linkage currently compares protocol type vs XML name and does not yet switch to explicit-field extraction in `LinkResolver.validate_cross_file_linkage`.

Because of current implementation, only `exact` and `normalized` are actively enforced during cross-file linkage validation.

## 6) ID generation rules

Deterministic IDs are assigned by `LinkResolver.assign_ids(...)` using starts from `ids`:

- `assay_start = ids.assay.start`
- `analyte_start = ids.analyte.start`
- `unit_start = ids.analyte_unit.start`

Strategy is fixed to sequential (enforced by loader). Non-sequential strategies are rejected at config validation time.

## 7) Minimal valid config skeleton

```yaml
version: 1

ids:
  assay:
    strategy: sequential
    start: 0
  analyte:
    strategy: sequential
    start: 0
  analyte_unit:
    strategy: sequential
    start: 0

method_mapping:
  protocol:
    id: method.method_id
    version: method.method_version
  analytes_xml:
    method_id: method.method_id
    method_version: method.method_version

assay_mapping:
  internal_identity: assay.key
  protocol:
    type: assay.protocol_type
  analytes_xml:
    name: assay.xml_name
  cross_file_match:
    mode: exact

analyte_mapping:
  analytes_xml:
    id: analyte.xml_id
    name: analyte.name
    assay_ref: analyte.assay_ref

unit_mapping:
  analytes_xml:
    id: unit.xml_id
    name: unit.name
    analyte_ref: unit.analyte_ref
```

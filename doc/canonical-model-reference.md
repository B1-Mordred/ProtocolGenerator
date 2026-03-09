# Canonical Model Reference

This document defines the **canonical addon domain model** used by importers, validators, and generators.

Scope:
- Canonical entities under `src/addon_generator/domain/models.py`.
- Identity and linkage behavior from `src/addon_generator/domain/ids.py`.
- Required/optional constraints from `src/addon_generator/validation/domain_validator.py`.
- Projection behavior to `Analytes.xml` and `ProtocolFile.json` generators.

## 1) Canonical root aggregate

## `AddonModel`

`AddonModel` is the aggregate root for generation and validation.

| Field | Required | Type | Default | Notes |
|---|---|---|---|---|
| `addon_id` | Optional | `int` | `0` | XML `<AddOn><Id>` value; currently assigned to `0` by deterministic ID assignment. |
| `method` | **Required** | `MethodModel \| None` | `None` | Must be present for generation; missing method is a validation error. |
| `assays` | **Required (non-empty)** | `list[AssayModel]` | `[]` | At least one assay required. |
| `analytes` | Conditionally required | `list[AnalyteModel]` | `[]` | Each assay must have at least one linked analyte. |
| `units` | Conditionally required | `list[AnalyteUnitModel]` | `[]` | Each analyte must have at least one linked unit. |
| `sample_tube_types` | Optional | `list[dict[str, Any]]` | `[]` | Reserved canonical payload area. |
| `measurement_sample_lists` | Optional | `list[dict[str, Any]]` | `[]` | Reserved canonical payload area. |
| `run_results_export_path` | Optional | `str \| None` | `None` | Optional runtime/export metadata. |
| `protocol_context` | Optional | `ProtocolContextModel \| None` | `None` | GUI/context overrides and fragment definitions. |
| `source_metadata` | Optional | `dict[str, Any]` | `{}` | Metadata for fragment selection (assay family/reagent/dilution/instrument/config). |

## 2) Core canonical entities

## `MethodModel`

Identity for method-level output in both XML and protocol JSON.

| Field | Required | Type | Default | Constraints / behavior |
|---|---|---|---|---|
| `key` | Required | `str` | n/a | Canonical key (not projected directly). |
| `method_id` | **Required** | `str` | n/a | Must be non-empty; projected to Protocol `MethodInformation.Id` and XML `MethodId`. |
| `method_version` | **Required** | `str` | n/a | Must be non-empty and include at least one numeric character. |
| `display_name` | Optional | `str \| None` | `None` | Warning if empty; defaulted during protocol projection. |
| `main_title` | Optional | `str \| None` | `None` | Defaulted during protocol projection. |
| `sub_title` | Optional | `str \| None` | `None` | Defaulted during protocol projection. |
| `order_number` | Optional | `str \| None` | `None` | Defaulted during protocol projection. |
| `series_name`/`product_name`/`product_number`/`legacy_protocol_id` | Optional | `str \| None` | `None` | Currently canonical-only metadata (no direct generator projection in current pipeline). |

## `AssayModel`

Assay canonical entity used for both protocol assay information and XML assay nodes.

| Field | Required | Type | Default | Constraints / behavior |
|---|---|---|---|---|
| `key` | **Required** | `str` | n/a | Must be unique across assays. |
| `xml_id` | Optional (assigned) | `int \| None` | `None` | Assigned by deterministic ID pass when not set; must be unique if provided. |
| `source_row_id` | Optional | `str \| None` | `None` | Import provenance metadata. |
| `display_name` | Optional | `str \| None` | `None` | Canonical metadata. |
| `protocol_type` | Optional-but-expected | `str \| None` | `None` | Used as protocol `AssayInformation.Type`; also cross-file match candidate. |
| `protocol_display_name` | Optional | `str \| None` | `None` | Preferred display name for protocol assay information. |
| `xml_name` | Optional | `str \| None` | `None` | XML `<Assay><Name>` fallback target. |
| `addon_ref` | Optional (assigned) | `int \| None` | `None` | Defaults to addon ID (`0`) when unresolved. |
| `aliases` | Optional | `list[str]` | `[]` | Alias set must not collide across assays after casefold/trim normalization. |
| `analyte_keys` | Optional | `list[str]` | `[]` | Canonical relationship metadata. |
| `metadata` | Optional | `dict[str, Any]` | `{}` | Extensible metadata. |

## `AnalyteModel`

Analyte canonical entity linked to one assay.

| Field | Required | Type | Default | Constraints / behavior |
|---|---|---|---|---|
| `key` | **Required** | `str` | n/a | Must be unique across analytes. |
| `name` | **Required** | `str` | n/a | Must be non-empty; projected to XML `<Analyte><Name>`. |
| `assay_key` | **Required** | `str` | n/a | Must reference an existing assay key. |
| `xml_id` | Optional (assigned) | `int \| None` | `None` | Assigned deterministically when missing. |
| `assay_ref` | Optional (assigned) | `int \| None` | `None` | Populated from linked assay XML ID. |
| `assay_information_type` | Optional | `str \| None` | `None` | If provided and assay has `protocol_type`, must match after normalization. |
| `unit_keys` | Optional | `list[str]` | `[]` | Canonical relationship metadata. |
| `metadata` | Optional | `dict[str, Any]` | `{}` | Extensible metadata. |

## `AnalyteUnitModel`

Unit canonical entity linked to one analyte.

| Field | Required | Type | Default | Constraints / behavior |
|---|---|---|---|---|
| `key` | **Required** | `str` | n/a | Must be unique across units. |
| `name` | **Required** | `str` | n/a | Projected to XML `<AnalyteUnit><Name>`. |
| `analyte_key` | **Required** | `str` | n/a | Must reference an existing analyte key. |
| `xml_id` | Optional (assigned) | `int \| None` | `None` | Assigned deterministically when missing. |
| `analyte_ref` | Optional (assigned) | `int \| None` | `None` | Populated from linked analyte XML ID. |
| `metadata` | Optional | `dict[str, Any]` | `{}` | Extensible metadata. |

## `ProtocolContextModel`

Optional context and override container used for protocol projection.

| Field | Required | Type | Default | Projection use |
|---|---|---|---|---|
| `method_information_overrides` | Optional | `dict[str, Any]` | `{}` | Highest-precedence method field overrides. |
| `assay_fragments` | Optional | `list[dict[str, Any]]` | `[]` | Source for `AssayInformation` if present. |
| `loading_fragments` | Optional | `list[dict[str, Any]]` | `[]` | Source for `LoadingWorkflowSteps` if present. |
| `processing_fragments` | Optional | `list[dict[str, Any]]` | `[]` | Source for `ProcessingWorkflowSteps` if present. |
| `dilution_fragments`/`reagent_fragments`/`calibrator_fragments`/`control_fragments` | Optional | `list[dict[str, Any]]` | `[]` | Canonical context pools for fragment-driven workflows. |

## 3) Identity semantics

Deterministic identity assignment is performed by `assign_deterministic_ids`:

- `addon.addon_id` is set to `0`.
- Assays are sorted by `assay.key`; `xml_id` assigned from configured `assay_start`; `addon_ref` set to `addon_id`.
- Analytes are sorted by `(assay_key, name, key)`; `xml_id` assigned from configured `analyte_start`; `assay_ref` set via assay key→ID lookup.
- Units are sorted by `(analyte_key, name, key)`; `xml_id` assigned from configured `unit_start`; `analyte_ref` set via analyte key→ID lookup.

This guarantees deterministic IDs and link references for stable diffs and reproducible outputs.

## 4) Required/optional + constraints summary

Domain validation enforces these core invariants:

- `method` must exist.
- `method.method_id` and `method.method_version` are required; version must contain at least one digit.
- At least one assay is required.
- Assay/analyte/unit `key` values must be unique per entity type.
- If explicit `assay.xml_id` values are present, they must be unique.
- Every assay must have at least one analyte.
- Every analyte must reference a valid assay (`assay_key`) and have non-empty `name`.
- Every analyte must have at least one linked unit.
- Every unit must reference a valid analyte (`analyte_key`).
- Assay aliases (including assay key) must be globally unambiguous after normalization.
- A normalized analyte name cannot map to multiple assays (prevents ambiguous linkage).
- If both `analyte.assay_information_type` and assay `protocol_type` exist, they must normalize to the same value.

## 5) Defaulting behavior

### MethodInformation defaulting (`ProtocolFile.json`)

For each method field, projection precedence is:

1. GUI/context override (`protocol_context.method_information_overrides`)
2. Imported protocol fragment (`protocol_fragments.MethodInformation`)
3. Generated canonical value
4. Config default (`protocol_defaults.method_information`)
5. Built-in default

Required method fields tracked in merge report: `Id`, `DisplayName`, `Version`, `MainTitle`, `SubTitle`, `OrderNumber`.

Built-in hard defaults include:
- `DisplayName="Method"`
- `MainTitle="Main"`
- `SubTitle="Sub"`
- `OrderNumber="O-1"`
- `MaximumNumberOfSamples=1`
- `MaximumNumberOfProcessingCycles=1`
- `MaximumNumberOfAssays=max(1, len(assays))`
- `SamplesLayoutType="SAMPLES_LAYOUT_COMBINED"` (or forced separate for multi-assay)
- `MethodInformationType="REGULAR"`

### Section defaulting (`AssayInformation`, `LoadingWorkflowSteps`, `ProcessingWorkflowSteps`)

Section precedence is:

1. GUI/context fragments
2. Imported protocol fragments
3. Config defaults
4. Built-in defaults

Special behavior:
- `AssayInformation` falls back to at least one `{ "Type": "A", "DisplayName": "Assay" }` record.
- `ProcessingWorkflowSteps` becomes per-assay grouped entries when multiple assays are present (using first config step template + `GroupIndex`/`GroupDisplayName`).
- If a non-empty section is required and no source has values, generator forces empty list (`[]`) rather than null.

## 6) Projection rules to generated outputs

## A) `Analytes.xml`

`generate_analytes_addon_xml` projects canonical entities as:

- Root:
  - `<AddOn><Id>` ← `addon.addon_id`
  - `<MethodId>` ← `method.method_id`
  - `<MethodVersion>` ← `method.method_version`
- For each assay (sorted by `(xml_id, key)`):
  - `<Assay><Id>` ← `assay.xml_id` (fallback `0`)
  - `<Name>` ← `assay.xml_name` fallback `assay.protocol_type` fallback `""`
  - `<AddOnRef>` ← `assay.addon_ref` fallback `addon.addon_id`
- For each analyte under that assay (sorted by `(xml_id, key)`):
  - `<Analyte><Id>` ← `analyte.xml_id` (fallback `0`)
  - `<Name>` ← `analyte.name`
  - `<AssayRef>` ← `analyte.assay_ref` (fallback `0`)
  - Optional `<AssayInformationType>` emitted only when set
- For each unit under analyte (sorted by `(xml_id, key)`):
  - `<AnalyteUnit><Id>` ← `unit.xml_id` (fallback `0`)
  - `<Name>` ← `unit.name`
  - `<AnalyteRef>` ← `unit.analyte_ref` (fallback `0`)

After serialization, XML is validated against XSD; file write only occurs when there are no validation errors.

## B) `ProtocolFile.json`

`ProtocolJsonGenerator.generate` emits:

- `MethodInformation` from canonical method projection + merge/default precedence.
- `AssayInformation` from canonical assays or selected fragments.
  - Each canonical assay maps to `{"Type": assay.protocol_type or assay.xml_name, "DisplayName": assay.protocol_display_name or assay.xml_name or "Assay"}` merged with config defaults.
  - Ambiguous normalized assay types raise `ValueError`.
- `LoadingWorkflowSteps` from resolved fragments or configured defaults.
- `ProcessingWorkflowSteps` from resolved fragments or configured defaults, with multi-assay expansion as described above.

Merge report includes per-field provenance (`source`, `value`, `conflict`, `conflict_sources`) and unresolved/conflicting required method fields.

## 7) Cross-file identity semantics

Cross-file projection and validation expectations:

- Method identity must match between outputs:
  - XML `MethodId` == protocol `MethodInformation.Id`
  - XML `MethodVersion` == protocol `MethodInformation.Version`
- Assay/analyte/unit XML IDs must be unique.
- `AssayRef` and `AnalyteRef` references must resolve.
- Assay protocol type/name matching mode (`exact` or `normalized`) is enforced by mapping config during linkage validation.

These constraints are validated by cross-file validation to ensure generated artifacts remain linked and coherent.

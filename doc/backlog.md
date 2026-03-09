# Codex Backlog — Remaining Work to Reach Desired AddOn Authoring Functionality

## Purpose

This backlog defines the remaining implementation work needed to turn the now-working `addon_generator` core into the full desired solution:

- new GUI centered on business inputs and fragments
- robust Excel/XML import ingestion
- configurable and maintainable mapping
- domain-complete protocol generation
- production-grade validation, export, and regression safety

---

# Epic E1 — Production Import Pipeline

## Goal
Support the real input sources used by the team and normalize them into the canonical AddOn model reliably.

---

## Task E1.1 — Implement production Excel importer

### Objective
Build importer support for the real workbook structure, not just minimal fixtures.

### Deliverables
- stable workbook reader
- sheet-level parsers
- column mapping registry
- type coercion and normalization
- missing-column diagnostics
- duplicate-row diagnostics

### Implementation notes
- Prefer a dedicated parsing layer per worksheet rather than one large importer.
- Add a normalization module for strings, booleans, numerics, and empty-cell handling.
- Make column detection deterministic and fail fast when required columns are missing.
- Support workbook version detection if multiple workbook layouts exist.

### Acceptance criteria
- real workbook can be parsed into the canonical model
- importer reports actionable errors for malformed input
- importer supports deterministic precedence for repeated values
- importer is covered by regression tests using representative workbook fixtures

---

## Task E1.2 — Add XML import for AddOn-shaped input

### Objective
Allow import of XSD-aligned input XML into the canonical model.

### Deliverables
- XML parser
- XSD validation before import
- canonical-model conversion layer

### Implementation notes
- Validate XML against `AddOn.xsd` before conversion.
- Convert parsed XML into the same canonical entities used by Excel and GUI input.
- Keep XML import independent of protocol generation.

### Acceptance criteria
- valid AddOn XML imports successfully
- invalid XML fails with clear validation messages
- imported XML and imported Excel can produce equivalent canonical model instances where data overlaps

---

## Task E1.3 — Implement source-merging rules

### Objective
Support mixed input sources:
- Excel
- GUI
- optional XML

### Deliverables
- merge strategy module
- precedence rules
- conflict reporting

### Required precedence
1. explicit GUI override
2. imported source value
3. config default
4. built-in default

### Implementation notes
- Track field provenance in the merge result.
- Expose conflict details for the GUI preview layer.
- Keep merging deterministic and side-effect free.

### Acceptance criteria
- conflicts are visible and deterministic
- resulting canonical model is reproducible
- merge behavior is covered by unit tests and at least one integration test

---

# Epic E2 — New GUI

## Goal
Replace schema-shaped editing with a task-oriented UI that feeds the canonical model.

---

## Task E2.1 — Build new GUI shell

### Objective
Create a new application flow around:
- method setup
- assay setup
- analyte setup
- import preview
- validation
- export

### Deliverables
- app shell
- navigation structure
- state container bound to canonical model or input DTOs

### Implementation notes
- Do not expose raw `ProtocolFile.json` fields as primary editing controls.
- Organize the UI around domain concepts and user tasks.
- Keep generation actions routed through the service layer, not directly through widgets.

### Acceptance criteria
- user can create an addon without touching protocol-schema fields directly
- GUI state can be serialized/restored for draft workflows
- navigation supports validation-aware progression

---

## Task E2.2 — Add method editor

### Objective
Support authoring and editing of method-level identity and metadata.

### Minimum fields
- method id
- method version
- display name
- optional metadata used for protocol projection

### Acceptance criteria
- method identity is editable and previewable
- identity linkage to both outputs is visible
- validation prevents empty required method identity fields

---

## Task E2.3 — Add assay/analyte editor

### Objective
Support authoring of assays, analytes, and analyte units.

### Required capabilities
- assay list
- analyte list per assay
- unit assignment
- aliases if needed
- preview of resolved output-facing fields

### Acceptance criteria
- user can create/edit assay-analyte relationships visually
- orphan relationships are blocked
- duplicate/ambiguous mappings are flagged before generation

---

## Task E2.4 — Add import preview and conflict resolution UI

### Objective
Allow users to inspect imported values, overrides, and conflicts before generation.

### Required display areas
- imported values
- overridden values
- unresolved fields
- validation errors/warnings

### Acceptance criteria
- user can inspect and resolve import conflicts before generation
- unresolved required fields are clearly highlighted
- field provenance is visible where practical

---

## Task E2.5 — Add output preview/export UI

### Objective
Show generation results and allow export from the application.

### Required capabilities
- preview generated `Analytes.xml`
- preview generated `ProtocolFile.json`
- show validation status
- choose export target/folder

### Acceptance criteria
- one-click generation and export works from the GUI
- validation failures block export with actionable messages
- previews reflect the latest merged canonical model state

---

# Epic E3 — Protocol Fragment Library

## Goal
Move protocol generation from minimal valid defaults to maintainable fragment-based business logic.

---

## Task E3.1 — Define fragment model

### Objective
Create protocol-side fragment types for:
- method metadata defaults
- assay metadata defaults
- loading workflow fragments
- processing workflow fragments

### Implementation notes
- Keep protocol-only concerns out of the XSD-shaped input model.
- Store fragment definitions in config or structured resources where possible.
- Make fragment selection deterministic.

### Acceptance criteria
- protocol generator consumes reusable fragments, not hard-coded placeholders
- fragment types are documented and testable in isolation

---

## Task E3.2 — Implement loading workflow templates

### Objective
Build reusable templates for common loading patterns.

### Acceptance criteria
- different assay families can resolve to different loading step sets
- step indexes and parameters are deterministic
- generated loading steps validate against protocol schema

---

## Task E3.3 — Implement processing workflow templates

### Objective
Build reusable group/step templates for common processing patterns.

### Acceptance criteria
- generator can compose complete valid workflow groups from fragment definitions
- generated processing groups validate against protocol schema
- index ordering and durations are deterministic

---

## Task E3.4 — Add fragment selection rules

### Objective
Select fragments based on:
- assay family
- reagent characteristics
- dilution behavior
- instrument options
- config

### Acceptance criteria
- protocol structure changes correctly based on canonical business input
- fragment selection behavior is covered by focused tests

---

# Epic E4 — Business Rule Completion

## Goal
Encode the real assay/analyte/protocol rules used in practice.

---

## Task E4.1 — Assay-to-analyte rule set

### Objective
Implement rules for:
- one assay to many analytes
- one analyte to one assay
- naming normalization
- alias handling

### Acceptance criteria
- real assay/analyte relationships from production data are supported
- ambiguous relationships fail clearly

---

## Task E4.2 — Unit handling

### Objective
Support:
- multiple units per analyte where needed
- normalization of unit names
- duplicate prevention

### Acceptance criteria
- unit definitions are correct and deterministic in XML output
- unsupported or malformed unit definitions are rejected before export

---

## Task E4.3 — Optional/conditional protocol sections

### Objective
Implement rules for:
- conditional loading steps
- conditional processing groups
- assay-specific metadata fields
- dilution factors
- reagent-linked fragments

### Acceptance criteria
- protocol output reflects real domain behavior, not only generic defaults
- conditional logic is covered by regression tests

---

## Task E4.4 — Multi-assay method support

### Objective
Ensure method-level protocol generation behaves correctly when multiple assays are present.

### Acceptance criteria
- assay ordering, grouping, and protocol-level maxima are consistent and valid
- multiple assays can coexist without broken cross-file linkage

---

# Epic E5 — Semantic Validation Layer

## Goal
Prevent operationally wrong outputs that still pass schema validation.

---

## Task E5.1 — Cross-file consistency validator

### Objective
Validate:
- method identity equality across outputs
- assay projection consistency
- analyte-to-assay integrity
- duplicate external match keys

### Acceptance criteria
- generation fails clearly on cross-file inconsistencies
- validator messages identify the exact conflicting entities

---

## Task E5.2 — Domain validator

### Objective
Validate:
- duplicate analyte names where disallowed
- unsupported assay combinations
- missing units
- empty assay lists
- invalid version format if required
- invalid aliases or ambiguous mappings

### Acceptance criteria
- invalid business input is caught before export
- domain validation is independent of schema validation

---

## Task E5.3 — Mapping config validator

### Objective
Validate:
- unknown field paths
- invalid fallback chains
- duplicate aliases
- impossible projections
- non-unique external match fields

### Acceptance criteria
- bad config fails fast at startup or load time
- config validation errors are actionable for maintainers

---

# Epic E6 — Export and Packaging

## Goal
Produce the final addon artifact set in the format the downstream system expects.

---

## Task E6.1 — Add export package builder

### Objective
Bundle:
- `ProtocolFile.json`
- `Analytes.xml`
- optional metadata/config artifacts
- folder/package structure

### Acceptance criteria
- export layout matches deployment expectations exactly
- package contents are deterministic for the same input

---

## Task E6.2 — Deterministic naming/versioning

### Objective
Implement file/folder naming rules derived from:
- method id
- method version
- config
- timestamp only if explicitly required

### Acceptance criteria
- export results are predictable and reproducible
- naming collisions are handled safely

---

## Task E6.3 — Overwrite and destination handling

### Objective
Support:
- export path selection
- overwrite confirmation
- safe temp-write then move

### Acceptance criteria
- export is robust and does not silently corrupt existing files
- failures leave the destination in a consistent state

---

# Epic E7 — Regression Corpus and Test Expansion

## Goal
Protect the system against rule drift and future mapping changes.

---

## Task E7.1 — Build fixture corpus

### Objective
Add representative fixtures for:
- minimal valid input
- single-assay method
- multi-assay method
- multi-analyte assay
- alias-driven mapping
- invalid cross-file mapping
- invalid units
- malformed import workbook

### Acceptance criteria
- fixture set covers real-world patterns, not just toy examples
- fixtures are documented and organized by purpose

---

## Task E7.2 — Golden-output tests

### Objective
For selected fixtures, assert exact generated:
- `Analytes.xml`
- `ProtocolFile.json`

### Acceptance criteria
- intentional output changes are explicit and reviewable
- stable inputs produce stable outputs

---

## Task E7.3 — Import regression tests

### Objective
Test importer behavior against workbook variants and edge cases.

### Acceptance criteria
- importer failures are reproducible and informative
- workbook layout changes are caught by CI

---

## Task E7.4 — Coverage modernization

### Objective
Update coverage config so it measures `src/addon_generator`, not mainly legacy code.

### Acceptance criteria
- coverage report reflects the new pipeline accurately
- coverage gate is meaningful for ongoing development

---

# Epic E8 — Documentation and Maintainer Experience

## Goal
Make the system understandable and maintainable without reverse-engineering.

---

## Task E8.1 — Mapping config reference

### Objective
Document:
- every top-level section
- valid field paths
- fallback behavior
- alias rules
- ID generation rules

### Acceptance criteria
- maintainers can modify mapping config safely using documentation alone

---

## Task E8.2 — Canonical model reference

### Objective
Document:
- entity definitions
- required vs optional fields
- identity semantics
- projection rules

### Acceptance criteria
- developers can extend the canonical model without guessing intended semantics

---

## Task E8.3 — Developer guide

### Objective
Document:
- how import flows into canonical model
- how generators work
- how validators work
- how to add a new assay family
- how to add a new fragment template

### Acceptance criteria
- a new developer can add a supported assay family without reverse-engineering the codebase

---

## Task E8.4 — User guide

### Objective
Document:
- how to import data
- how to edit addon inputs
- how to validate
- how to export

### Acceptance criteria
- a domain user can operate the system using the guide alone

---

# Recommended Priority Order

## Priority P1
- E1 — Production Import Pipeline
- E2 — New GUI
- E5 — Semantic Validation Layer

These are the biggest remaining gaps between a working backend and a usable tool.

## Priority P2
- E3 — Protocol Fragment Library
- E4 — Business Rule Completion
- E6 — Export and Packaging

These make the system domain-complete and production-ready.

## Priority P3
- E7 — Regression Corpus and Test Expansion
- E8 — Documentation and Maintainer Experience

These make the solution safe to evolve and maintain.

---

# Suggested Codex Execution Plan

## Phase A
Implement production importer plus merge rules.

## Phase B
Build the new GUI around the canonical model.

## Phase C
Expand semantic validation and protocol fragment selection.

## Phase D
Implement final export packaging.

## Phase E
Expand regression fixtures, coverage, and documentation.

---

# Definition of Done

The desired functionality is reached when all of the following are true:

- users can create an addon entirely through the new GUI and/or import file
- the system builds one canonical model
- `Analytes.xml` and `ProtocolFile.json` are generated from that same model
- outputs are schema-valid
- outputs are semantically consistent
- export packaging matches downstream expectations
- real-world fixtures pass regression tests
- mapping/config behavior is documented and maintainable

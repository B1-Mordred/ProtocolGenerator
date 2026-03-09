# Developer Guide

This document describes the architecture and implementation strategy of the Protocol Generator GUI.

## 1) Architecture overview

The app is a Tkinter desktop wizard with a schema-driven form engine.

- **UI shell:** `ProtocolWizardApp` in `src/protocol_generator_gui/main.py`
- **Dynamic form primitives:** `PropertyEditor` and `StepEditor`
- **Schema adapters:** `src/protocol_generator_gui/schema_utils.py`
- **Validation engine:** `src/protocol_generator_gui/validation.py`
- **Wizard UX logic helpers:** `src/protocol_generator_gui/wizard_logic.py`
- Mapping config contract reference for addon generation: `doc/mapping-config-reference.md`
- **Persistence/autosave:** `src/protocol_generator_gui/persistence.py`

Runtime flow:

1. Load `protocol.schema.json`.
2. Derive StepType→StepParameters maps from schema `allOf` rules.
3. Render forms dynamically for required/advanced properties.
4. Validate on every change and update per-step indicators.
5. Persist temporary drafts and save target JSON atomically.
6. Export `ProtocolFile.json` only after successful validation.

## 2) Module layout

```text
src/protocol_generator_gui/
  __init__.py
  main.py               # Tk app shell, widgets, interactions
  schema_utils.py       # schema loading, refs, step mapping
  wizard_logic.py       # progress summary, help text, field categorization
  validation.py         # schema validation entry points
  persistence.py        # autosave, draft recovery, atomic writes

tests/
  unit/                 # focused logic tests
  integration/          # cross-module workflow tests
  test_*.py             # additional suite coverage
```

## 3) Schema-mapping strategy

### Loading schema

- `load_schema` reads `protocol.schema.json` into memory.
- `$ref` paths are resolved by `resolve_ref`/`dereference` for schema traversal.

### Mapping StepType to parameter schema

- `extract_step_type_map` walks each `allOf` branch.
- It extracts `if.properties.StepType.const` as the discriminator.
- It binds that discriminator to `then.properties.StepParameters`.

This powers dynamic step editors:

- **Step 2 Loading** uses `loading_step_types(schema)`.
- **Step 3 Processing** uses `processing_step_types(schema)`.

### Required-first rendering

`categorize_schema_fields` partitions properties into:

- Required fields (always visible)
- Advanced options (hidden until user enables **Show advanced options**)

## 4) Validation pipeline

Validation is intentionally continuous and user-visible:

1. Any variable change in `PropertyEditor` triggers `on_change`.
2. `on_change` builds assembled protocol data via `protocol_data()`.
3. `validate_protocol` returns a list of `(path, message)` errors.
4. Errors are split into General, Loading, and Processing scopes.
5. Step badges show `✓` or `✗ (N)`.
6. Main status shows either `Valid` or first-error context.
7. `_focus_first_invalid` attempts to focus the first invalid General field.

Export path:

- `export_protocol` re-runs validation.
- If invalid: show **Validation failed** dialog and abort export.
- If valid: write pretty-printed `ProtocolFile.json`.

## 5) Persistence and autosave lifecycle

- Autosave is scheduled with a debounce (`autosave_delay_ms = 400`).
- Pending jobs are cancellable via `Esc` (`on_escape_cancel`).
- `save_now` always writes temp draft first.
- If save path exists, data is also persisted atomically to target file.
- On startup `_attempt_recovery` can restore last temp draft.

## 6) Test strategy

The test strategy emphasizes deterministic logic coverage and user workflow safety.

### Unit tests

Cover isolated logic branches:

- schema parsing/ref handling and StepType extraction
- required/advanced field partition behavior
- validation edge cases and error messages
- JSON assembly and step metadata behavior

### Integration tests

Exercise wizard-level workflows:

- step transition guards (save-path requirement)
- loading/processing add/edit/reorder/delete behavior
- autosave behavior tied to state changes

### Quality gate

- `pytest` + `pytest-cov`
- Coverage fail-under set to **85%**
- Tkinter shell module (`main.py`) omitted from coverage gate to prioritize pure logic modules

Run locally:

```bash
python -m pip install -e .[dev]
pytest
```

## 7) Contribution checklist

- Keep docs and command examples aligned with visible UI labels:
  - **Save As**, **Export ProtocolFile.json**, **Step 1 General**, **Step 2 Loading**, **Step 3 Processing**
- Add/update tests when logic changes.
- Update `doc/changelog.md` for user-visible behavior changes.


## 8) Addon mapping config reference

For mapping-loader/validator-consumed config sections, field-path rules, matching modes, fallback behavior, and ID assignment semantics, see `doc/mapping-config-reference.md`.

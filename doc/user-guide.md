# User Guide

This guide explains the full **Protocol Generator GUI** workflow for creating and exporting a valid `ProtocolFile.json`: import, edit, validate, preview, and export.

## 1) Before you start

- Install and launch the app from the repository root:

```bash
python -m pip install -e .
protocol-generator-gui
```

- Keep `protocol.schema.json` in the repository root unchanged unless your team intentionally updates the protocol schema.
- Prepare any existing protocol JSON draft you may want to import/reopen during setup.

## 2) UI tour (current labels)

Top toolbar:

- **Save As**
- **Export ProtocolFile.json**
- Progress text (`Stage X/5 | Completed: Y/5 | Unresolved errors: Z`)
- Validation status (`Valid`, `Errors: N (...)`, or `Not validated`)
- Autosave status (`Autosave idle`, `Saving…`, `Saved at HH:MM`, `Saved draft at HH:MM`, `Autosave cancelled`, `Save failed`, etc.)

Tabs:

1. **1. Method setup**
2. **2. Assay/analyte setup**
3. **3. Import preview/conflicts**
4. **4. Validation**
5. **5. Output preview/export**

> Important: You must set a file path with **Save As** before moving past tab 1. If you try to continue first, the app prompts **Save location required**.

## 3) End-to-end workflow

### Stage 1 — Method setup

Use this tab to fill:

- `MethodInformation`
- `AssayInformation[0]`

How to work efficiently:

- Fill all fields shown under **Required fields** first.
- Expand **Show advanced options** only for optional or less-common fields.
- Click **Save As** as soon as you have a valid destination path so autosave writes to your intended file.

### Stage 2 — Assay/analyte setup

This stage configures workflow steps used by protocol execution.

For both loading and processing editors:

- Use **Add**, **Delete**, **Move Up**, **Move Down** to manage steps.
- Choose each row’s `StepType` from the dropdown.
- Complete generated `StepParameters` for that `StepType`.
- Confirm safety prompts when reordering/removing rows (**Confirm reorder**, **Confirm delete**).

Typical loading `StepType` values include:

- `LoadCounterweight`
- `LoadMfxCarriers`
- `LoadReagentCarrier`
- `LoadCalibratorAndControlCarrier`

Typical processing `StepType` values include:

- `AliquotTransfer`
- `CounterweightTransfer`
- `SingleTransfer`
- `StartCentrifuge`
- `StartHeaterShaker`
- `UnloadCentrifuge`
- `UnloadHeaterShaker`

### Stage 3 — Import preview/conflicts

Use this tab after bringing in existing or previously saved data.

What you see:

- Conflict count and field-by-field conflict entries.
- Imported/current comparison context.
- A summary of unresolved conflicts that can block later progression/export.

Recommended workflow:

1. Review each conflict entry.
2. Resolve required conflicts first.
3. Re-check the unresolved count before proceeding.

### Stage 4 — Validation

This tab consolidates validation feedback before export.

Validation includes:

- Schema validation errors
- Method editor checks
- Assay/analyte relationship warnings

Use it as your final checklist:

- No unresolved required-field errors
- No type/format errors
- No critical relationship issues

### Stage 5 — Output preview/export

This tab shows:

- **ProtocolFile.json preview** (first section of generated output)
- Output readiness messages and blockers

Export steps:

1. Confirm status is **Valid** and blockers are cleared.
2. Click **Export ProtocolFile.json**.
3. Choose the destination directory.
4. Confirm success dialog **Export complete**.

Generated artifact name:

- `ProtocolFile.json` (written into the selected folder)

## 4) Worked examples

### Example A — Start from scratch and export

1. In **1. Method setup**, enter required method/assay fields.
2. Click **Save As** and select `my_protocol_draft.json`.
3. In **2. Assay/analyte setup**, add required loading and processing steps.
4. Open **4. Validation** and fix any listed errors.
5. Open **5. Output preview/export**, confirm preview/messages are clean.
6. Click **Export ProtocolFile.json** and choose an export folder.
7. Verify `<folder>/ProtocolFile.json` exists.

### Example B — Recover and finish an interrupted session

1. Relaunch the app after an unexpected close.
2. At **Recover draft**, choose **Yes**.
3. Continue edits in any stage.
4. Re-run validation in **4. Validation**.
5. Export from **5. Output preview/export**.

### Example C — Resolve an import conflict blocker

1. Go to **3. Import preview/conflicts**.
2. Locate required-field conflicts.
3. Resolve conflicts so required fields are no longer unresolved.
4. Revisit **4. Validation** and **5. Output preview/export** to confirm export readiness.

## 5) Troubleshooting (validation/export blockers)

### Blocker: "Save location required" when switching tabs

Cause:

- No save path selected yet.

Fix:

- Return to **1. Method setup** and click **Save As**.

### Blocker: Validation status shows `Errors: N (...)`

Common causes:

- Missing required fields in `MethodInformation` or `AssayInformation[0]`
- Missing `StepParameters` required by selected `StepType`
- Invalid types/formats (for example number vs string mismatches)

Fix:

- Use **4. Validation** for exact path/message details.
- Jump back to the relevant stage and correct the flagged fields.

### Blocker: Export button action shows **Validation failed**

Cause:

- Final schema validation still finds unresolved errors.

Fix:

1. Read the first listed error paths in the dialog.
2. Fix those fields in the corresponding stage.
3. Re-check **4. Validation** and retry export.

### Blocker: Output preview messages indicate not ready

Cause:

- Unresolved conflicts or missing export target requirements.

Fix:

- Resolve conflicts in **3. Import preview/conflicts**.
- Ensure required values are complete and valid.

### Blocker: Autosave says **Save failed**

Possible causes:

- Destination path unavailable
- Permission or disk issues

Fix:

- Use **Save As** to choose a writable location.
- Retry after confirming free disk space and directory access.

## 6) Autosave and recovery behavior

- Every change schedules autosave with a short debounce.
- Press **Esc** to cancel a pending autosave cycle.
- Before a save location is chosen, the app writes a temporary draft.
- On restart, if a temp draft exists, the app prompts **Recover draft**.

## 7) Example exported structure (`ProtocolFile.json`)

```json
{
  "MethodInformation": {
    "MethodName": "Run-042",
    "ProtocolVersion": "1.0"
  },
  "AssayInformation": [
    {
      "AssayName": "Assay-A"
    }
  ],
  "LoadingWorkflowSteps": [
    {
      "StepType": "LoadCounterweight",
      "StepParameters": {
        "TipLabwareType": "TipType-A",
        "AspirationLiquidClassName": "Water",
        "RequiredCounterweightPlates": [],
        "RequiredCounterweightWater": {}
      }
    }
  ],
  "ProcessingWorkflowSteps": [
    {
      "GroupDisplayName": "Default Group",
      "GroupIndex": 0,
      "GroupSteps": []
    }
  ]
}
```

## Field Mapping now affects export output

Field Mapping templates in **Admin → Field Mapping** are now applied during validation/export (not just preview text).

- Only **enabled rows** from the **active template** run.
- Supported execution targets include `ProtocolFile.json` (`MethodInformation.Id`, `MethodInformation.Version`, analyte names) and `Analytes.xml` analyte/unit names.
- If multiple enabled rows map to the same output field, the exporter uses **last-write-wins** deterministically and emits a validation warning entry.
- Validation status now reports how many mapping rows were **applied** vs **skipped**.


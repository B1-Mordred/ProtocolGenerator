from __future__ import annotations

from typing import Any

from addon_generator.importers.excel_importer import ImportDiagnostic
from addon_generator.input_models.dtos import SamplePrepStepInputDTO


def parse_sampleprep_sheet(sheet: Any, *, vocab: dict[str, set[str]], diagnostics: list[ImportDiagnostic]) -> list[SamplePrepStepInputDTO]:
    rows = list(sheet.iter_rows())
    header_row, header_map = _find_header(rows)
    if header_row is None:
        return []

    steps: list[SamplePrepStepInputDTO] = []
    valid_actions = {v.casefold(): v for v in vocab.get("SamplePrepAction", set())}
    seen_steps: set[tuple[str, str]] = set()

    for row_idx in range(header_row + 1, len(rows) + 1):
        row = rows[row_idx - 1]
        order = _text(row[header_map["order"]].value)
        action = _text(row[header_map["action"]].value)
        if not order and not action:
            continue
        normalized_action = action
        if action and valid_actions:
            canonical = valid_actions.get(action.casefold())
            if canonical is None:
                diagnostics.append(ImportDiagnostic(rule_id="invalid-vocabulary", message="Unknown sample prep action", sheet=sheet.title, row=row_idx, column="Action", value=action))
            else:
                normalized_action = canonical
        identity = (_identity_token(order), _identity_token(normalized_action or action))
        if identity in seen_steps:
            diagnostics.append(
                ImportDiagnostic(
                    rule_id="duplicate-row",
                    message="Duplicate sample prep step",
                    sheet=sheet.title,
                    row=row_idx,
                    value={"order": order, "action": normalized_action or action, "duplicate_key": f"{order}|{normalized_action or action}"},
                )
            )
            continue
        seen_steps.add(identity)
        step_key = f"sampleprep:{order or row_idx}"
        steps.append(SamplePrepStepInputDTO(key=step_key, label=normalized_action or None, metadata={"order": order, "raw_action": action}))
    return steps


def _find_header(rows: list[Any]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        labels = {_text(c.value).casefold(): i for i, c in enumerate(row) if _text(c.value)}
        if "order" in labels and "action" in labels:
            return idx, {"order": labels["order"], "action": labels["action"]}
    return None, {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()



def _identity_token(value: str) -> str:
    return value.strip().casefold()

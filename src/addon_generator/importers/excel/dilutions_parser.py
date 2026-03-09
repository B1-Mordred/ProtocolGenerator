from __future__ import annotations

from typing import Any

from addon_generator.importers.excel_importer import ImportDiagnostic
from addon_generator.input_models.dtos import DilutionSchemeInputDTO


def parse_dilutions_sheet(sheet: Any, *, diagnostics: list[ImportDiagnostic]) -> list[DilutionSchemeInputDTO]:
    rows = list(sheet.iter_rows())
    header_row, header_map = _find_header(rows)
    if header_row is None:
        return []

    schemes: list[DilutionSchemeInputDTO] = []
    seen_names: set[str] = set()
    for row_idx in range(header_row + 1, len(rows) + 1):
        row = rows[row_idx - 1]
        name = _text(row[header_map["name"]].value)
        ratio = _text(row[header_map["ratio"]].value)
        if not name and not ratio:
            break
        if not name:
            diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Dilution scheme name is required", sheet=sheet.title, row=row_idx, column="Name"))
            continue
        identity = _identity_token(name)
        if identity in seen_names:
            diagnostics.append(
                ImportDiagnostic(
                    rule_id="duplicate-row",
                    message="Duplicate dilution scheme",
                    sheet=sheet.title,
                    row=row_idx,
                    value={"name": name, "duplicate_key": name},
                )
            )
            continue
        seen_names.add(identity)
        schemes.append(DilutionSchemeInputDTO(key=f"dilution:{name}", label=name, metadata={"ratio": ratio}))
    return schemes


def _find_header(rows: list[Any]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        labels = {_text(c.value).casefold(): i for i, c in enumerate(row) if _text(c.value)}
        if "name" in labels and "ratio" in labels:
            return idx, {"name": labels["name"], "ratio": labels["ratio"]}
    return None, {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()



def _identity_token(value: str) -> str:
    return value.strip().casefold()

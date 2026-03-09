from __future__ import annotations

from typing import Any

from addon_generator.importers.excel_importer import ImportDiagnostic
from addon_generator.input_models.dtos import AnalyteInputDTO, UnitInputDTO


class AnalytesParseResult:
    def __init__(self, analytes: list[AnalyteInputDTO], units: list[UnitInputDTO]):
        self.analytes = analytes
        self.units = units


def parse_analytes_sheet(sheet: Any, *, vocab: dict[str, set[str]], diagnostics: list[ImportDiagnostic]) -> AnalytesParseResult:
    rows = list(sheet.iter_rows())
    header_row, headers = _find_header(rows)
    if header_row is None:
        diagnostics.append(ImportDiagnostic(rule_id="missing-header", message="Analytes headers not found", sheet=sheet.title))
        return AnalytesParseResult([], [])

    analytes: list[AnalyteInputDTO] = []
    units: list[UnitInputDTO] = []
    known_units = {u.casefold(): u for u in vocab.get("Units", set())}

    seen_analytes: set[tuple[str, str]] = set()

    for row_idx in range(header_row + 1, len(rows) + 1):
        row = rows[row_idx - 1]
        analyte_name = _text(row[headers["analyte"]].value)
        unit_name = _text(row[headers["unit"]].value)
        parameter_set = _text(row[headers["parameter_set"]].value)
        assay_key = _text(row[headers.get("assay_key", headers["analyte"])].value)
        if not any((analyte_name, unit_name, parameter_set, assay_key)):
            break
        analyte_key = f"analyte:{analyte_name or row_idx}"
        identity = (_identity_token(analyte_name or analyte_key), _identity_token(assay_key))
        if identity in seen_analytes:
            diagnostics.append(
                ImportDiagnostic(
                    rule_id="duplicate-row",
                    message="Duplicate analyte row",
                    sheet=sheet.title,
                    row=row_idx,
                    value={
                        "analyte": analyte_name,
                        "assay_key": assay_key,
                        "duplicate_key": f"{analyte_name or analyte_key}|{assay_key}",
                    },
                )
            )
            continue
        seen_analytes.add(identity)
        analytes.append(
            AnalyteInputDTO(
                key=analyte_key,
                name=analyte_name,
                assay_key=assay_key,
                assay_information_type=parameter_set or None,
            )
        )
        if unit_name:
            normalized_unit = known_units.get(unit_name.casefold(), unit_name)
            if known_units and unit_name.casefold() not in known_units:
                diagnostics.append(ImportDiagnostic(rule_id="invalid-vocabulary", message="Unknown unit", sheet=sheet.title, row=row_idx, column="Unit", value=unit_name))
            units.append(UnitInputDTO(key=f"{analyte_key}:unit", name=normalized_unit, analyte_key=analyte_key))

    return AnalytesParseResult(analytes, units)


def _find_header(rows: list[Any]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        labels = {_text(c.value).casefold(): i for i, c in enumerate(row) if _text(c.value)}
        if "analyte" in labels and "unit" in labels and "parameter set" in labels:
            mapped = {"analyte": labels["analyte"], "unit": labels["unit"], "parameter_set": labels["parameter set"]}
            if "assay key" in labels:
                mapped["assay_key"] = labels["assay key"]
            return idx, mapped
    return None, {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()



def _identity_token(value: str) -> str:
    return value.strip().casefold()

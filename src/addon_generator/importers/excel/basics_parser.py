from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.importers.excel_importer import ImportDiagnostic
from addon_generator.input_models.dtos import AssayInputDTO, MethodInputDTO

IDENTITY_LABELS = {
    "method id": "method_id",
    "method version": "method_version",
    "method display name": "display_name",
    "display name": "display_name",
}

COMPONENT_HEADERS = {"assay key": "key", "protocol type": "protocol_type", "protocol display name": "protocol_display_name", "xml assay name": "xml_name"}


@dataclass(slots=True)
class BasicsParseResult:
    method: MethodInputDTO
    assays: list[AssayInputDTO]


def parse_basics_sheet(sheet: Any, *, diagnostics: list[ImportDiagnostic]) -> BasicsParseResult:
    identity: dict[str, str] = {}
    rows = list(sheet.iter_rows())

    for row_idx, row in enumerate(rows, start=1):
        label = _text(row[0].value).casefold() if row else ""
        if label in IDENTITY_LABELS:
            identity[IDENTITY_LABELS[label]] = _text(row[1].value) if len(row) > 1 else ""

    method_id = identity.get("method_id", "")
    method_version = identity.get("method_version", "")
    if not method_id:
        diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Method Id is required", sheet=sheet.title, column="Method Id"))
    if not method_version:
        diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Method Version is required", sheet=sheet.title, column="Method Version"))

    header_row_idx, header_map = _find_component_header_row(rows)
    assays: list[AssayInputDTO] = []
    if header_row_idx is None:
        diagnostics.append(ImportDiagnostic(rule_id="missing-component-table", message="Could not find component table headers", sheet=sheet.title))
    else:
        for row_idx in range(header_row_idx + 1, len(rows) + 1):
            row = rows[row_idx - 1]
            key = _text(row[header_map["key"]].value)
            protocol = _text(row[header_map["protocol_type"]].value)
            display = _text(row[header_map.get("protocol_display_name", header_map["protocol_type"])].value)
            xml_name = _text(row[header_map.get("xml_name", header_map["protocol_type"])].value)
            if not any((key, protocol, display, xml_name)):
                break
            if not key:
                diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Assay key is required", sheet=sheet.title, row=row_idx, column="Assay Key"))
                continue
            assays.append(AssayInputDTO(key=key, protocol_type=protocol, protocol_display_name=display or None, xml_name=xml_name or protocol))

    method = MethodInputDTO(key=f"method:{method_id or 'unknown'}", method_id=method_id, method_version=method_version, display_name=identity.get("display_name") or None)
    return BasicsParseResult(method=method, assays=assays)


def _find_component_header_row(rows: list[Any]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        labels = {_text(cell.value).casefold(): i for i, cell in enumerate(row) if _text(cell.value)}
        if "assay key" in labels and "protocol type" in labels:
            mapped = {target: labels[src] for src, target in COMPONENT_HEADERS.items() if src in labels}
            return idx, mapped
    return None, {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()

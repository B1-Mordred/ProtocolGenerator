from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.models import normalize_assay_identity_fields
from addon_generator.importers.excel_importer import ImportDiagnostic
from addon_generator.input_models.dtos import AssayInputDTO, MethodInputDTO

IDENTITY_LABELS = {
    "method id": "method_id",
    "method version": "method_version",
    "method display name": "display_name",
    "display name": "display_name",
    "kit series": "series_name",
    "(basic) kit name": "display_name",
    "kit product number": "order_number",
    "addon series": "main_title",
    "addon product name": "sub_title",
    "addon product number": "product_number",
}

COMPONENT_HEADERS = {"assay key": "key", "protocol type": "protocol_type", "protocol display name": "protocol_display_name", "xml assay name": "xml_name"}
KIT_COMPONENT_HEADERS = {
    "product number": "product_number",
    "component name": "component_name",
    "parameter set number": "parameter_set_number",
    "assay abbreviation": "assay_abbreviation",
    'parameter set name (or "basic kit")': "parameter_set_name",
    "type": "type",
    "container type (if liquid)": "container_type",
}


@dataclass(slots=True)
class BasicsParseResult:
    method: MethodInputDTO
    assays: list[AssayInputDTO]
    assay_reference_lookup: dict[str, str]


def parse_basics_sheet(sheet: Any, *, diagnostics: list[ImportDiagnostic]) -> BasicsParseResult:
    identity: dict[str, str] = {}
    rows = list(sheet.iter_rows())

    for row_idx, row in enumerate(rows, start=1):
        for pair_start in range(0, len(row), 2):
            if pair_start + 1 >= len(row):
                continue
            label = _normalize_label(row[pair_start].value)
            if label in IDENTITY_LABELS:
                identity[IDENTITY_LABELS[label]] = _text(row[pair_start + 1].value)

    method_id = identity.get("method_id", "")
    method_version = identity.get("method_version", "")
    has_addon_identity = any(
        identity.get(key)
        for key in ("series_name", "display_name", "order_number", "main_title", "sub_title", "product_number")
    )
    if not method_id and not has_addon_identity:
        diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Method Id is required", sheet=sheet.title, column="Method Id"))
    if not method_version and not has_addon_identity:
        diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Method Version is required", sheet=sheet.title, column="Method Version"))

    header_row_idx, header_map = _find_component_header_row(rows)
    assays: list[AssayInputDTO] = []
    if header_row_idx is None:
        diagnostics.append(ImportDiagnostic(rule_id="missing-component-table", message="Could not find component table headers", sheet=sheet.title))
    else:
        seen_assays: set[tuple[str, str]] = set()
        for row_idx in range(header_row_idx + 1, len(rows) + 1):
            row = rows[row_idx - 1]

            key = _value(row, header_map, "key")
            protocol = _value(row, header_map, "protocol_type")
            display = _value(row, header_map, "protocol_display_name")
            xml_name = _value(row, header_map, "xml_name")

            product_number = _value(row, header_map, "product_number")
            component_name = _value(row, header_map, "component_name")
            parameter_set_number = _value(row, header_map, "parameter_set_number")
            assay_abbreviation = _value(row, header_map, "assay_abbreviation")
            parameter_set_name = _value(row, header_map, "parameter_set_name")
            assay_type = _value(row, header_map, "type")
            container_type = _value(row, header_map, "container_type")

            if not any((key, protocol, display, xml_name, product_number, component_name, parameter_set_number, assay_abbreviation, parameter_set_name, assay_type, container_type)):
                continue

            if not key:
                key = parameter_set_number or component_name
            if not key:
                diagnostics.append(ImportDiagnostic(rule_id="missing-required-field", message="Assay key is required", sheet=sheet.title, row=row_idx, column="Assay Key"))
                continue

            protocol_type, protocol_display_name, xml_name = normalize_assay_identity_fields(
                protocol_type=protocol or assay_type,
                protocol_display_name=display or component_name,
                xml_name=xml_name or parameter_set_name or component_name,
                fallback_order={"xml_name": ("protocol_display_name", "protocol_type")},
            )
            assay_identity = (_identity_token(key), _identity_token(protocol_type))
            if assay_identity in seen_assays:
                if _identity_token(protocol_type) not in {"calibrator", "control", "internal standard"}:
                    diagnostics.append(
                        ImportDiagnostic(
                            rule_id="duplicate-row",
                            message="Duplicate assay row",
                            sheet=sheet.title,
                            row=row_idx,
                            value={
                                "assay_key": key,
                                "protocol_type": protocol_type,
                                "duplicate_key": f"{key}|{protocol_type}",
                            },
                        )
                    )
                continue
            seen_assays.add(assay_identity)
            assays.append(
                AssayInputDTO(
                    key=key,
                    protocol_type=protocol_type,
                    protocol_display_name=protocol_display_name,
                    xml_name=xml_name,
                    metadata={
                        "product_number": product_number,
                        "component_name": component_name,
                        "parameter_set_number": parameter_set_number,
                        "assay_abbreviation": assay_abbreviation,
                        "parameter_set_name": parameter_set_name,
                        "type": assay_type,
                        "container_type": container_type,
                    },
                )
            )

    fallback_method_id = method_id or identity.get("order_number") or identity.get("product_number") or "unknown"
    fallback_method_version = method_version or "1.0"
    method = MethodInputDTO(
        key=f"method:{fallback_method_id}",
        method_id=fallback_method_id,
        method_version=fallback_method_version,
        display_name=identity.get("display_name") or None,
        main_title=identity.get("main_title") or None,
        sub_title=identity.get("sub_title") or None,
        order_number=identity.get("order_number") or None,
        series_name=identity.get("series_name") or None,
        product_number=identity.get("product_number") or None,
    )
    return BasicsParseResult(method=method, assays=assays, assay_reference_lookup=_build_assay_reference_lookup(assays))


def _build_assay_reference_lookup(assays: list[AssayInputDTO]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for assay in assays:
        key = assay.key.strip()
        if not key:
            continue
        candidates = {
            key,
            str((assay.metadata or {}).get("parameter_set_number") or "").strip(),
            str((assay.metadata or {}).get("parameter_set_name") or "").strip(),
            str((assay.metadata or {}).get("component_name") or "").strip(),
            str((assay.metadata or {}).get("assay_abbreviation") or "").strip(),
            str(assay.protocol_display_name or "").strip(),
            str(assay.xml_name or "").strip(),
        }
        for candidate in candidates:
            if candidate:
                lookup[candidate.casefold()] = key
    return lookup


def _find_component_header_row(rows: list[Any]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        labels = {_text(cell.value).casefold(): i for i, cell in enumerate(row) if _text(cell.value)}
        has_legacy_headers = "assay key" in labels and "protocol type" in labels
        has_kit_headers = "component name" in labels and "parameter set number" in labels
        if has_legacy_headers or has_kit_headers:
            mapped = {target: labels[src] for src, target in COMPONENT_HEADERS.items() if src in labels}
            mapped.update({target: labels[src] for src, target in KIT_COMPONENT_HEADERS.items() if src in labels})
            return idx, mapped
    return None, {}




def _value(row: Any, header_map: dict[str, int], key: str) -> str:
    if key not in header_map:
        return ""
    index = header_map[key]
    if index >= len(row):
        return ""
    return _text(row[index].value)

def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_label(value: Any) -> str:
    return _text(value).rstrip(":").casefold()


def _identity_token(value: Any) -> str:
    return _text(value).casefold()

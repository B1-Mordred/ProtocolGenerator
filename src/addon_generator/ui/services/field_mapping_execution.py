from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.serialization.xml_writer import serialize_xml_document

LEGACY_TARGET_ALIASES = {
    "Analytes.xml:Analyte@name": "Analytes.xml:Assays[].Analytes[].Analyte.Name",
    "Analytes.xml:Analyte@unit": "Analytes.xml:Assays[].Analytes[].Analyte.AnalyteUnits[].AnalyteUnit.Name",
    "AddOn.xml:MethodInformation/MethodName": "AddOn.xml:MethodInformation.MethodName",
    "AddOn.xml:MethodInformation/MethodId": "AddOn.xml:MethodInformation.MethodId",
    "ProtocolFile.json:method.id": "ProtocolFile.json:MethodInformation.Id",
    "ProtocolFile.json:method.version": "ProtocolFile.json:MethodInformation.Version",
    "ProtocolFile.json:analytes[].name": "ProtocolFile.json:AssayInformation[].Analytes[].Name",
}


@dataclass(slots=True)
class FieldMappingExecutionResult:
    protocol_json: dict[str, Any]
    analytes_xml: str
    report: dict[str, Any]


def apply_field_mappings(
    *,
    protocol_json: dict[str, Any],
    analytes_xml: str,
    dto_bundle: InputDTOBundle | None,
    field_mapping_settings: dict[str, Any] | None,
) -> FieldMappingExecutionResult:
    protocol = deepcopy(protocol_json)
    xml_root = ET.fromstring(analytes_xml)
    report: dict[str, Any] = {
        "active_template": "",
        "applied": [],
        "skipped": [],
        "warnings": [],
    }

    template_rows = _active_template_rows(field_mapping_settings or {})
    report["active_template"] = str((field_mapping_settings or {}).get("active_template") or "")
    if not template_rows:
        return FieldMappingExecutionResult(protocol_json=protocol, analytes_xml=analytes_xml, report=report)

    context = _bundle_context(dto_bundle)
    last_writer_by_target: dict[str, int] = {}

    for index, row in enumerate(template_rows):
        if not bool(row.get("enabled", True)):
            report["skipped"].append({"row": index, "reason": "disabled"})
            continue

        target = _normalize_target(str(row.get("target") or "").strip())
        expression = str(row.get("expression") or "").strip()
        if not target or not expression:
            report["skipped"].append({"row": index, "reason": "missing-target-or-expression", "target": target})
            continue

        values, warnings = _resolve_expression(expression, context)
        for warning in warnings:
            report["warnings"].append(f"row {index}: {warning}")

        if not values:
            report["skipped"].append({"row": index, "reason": "no-values", "target": target})
            continue

        if target in last_writer_by_target:
            report["warnings"].append(
                f"row {index}: target '{target}' already written by row {last_writer_by_target[target]}; applying last-write-wins"
            )
        last_writer_by_target[target] = index

        applied_count, apply_warnings = _apply_target(target, values, protocol, xml_root)
        for warning in apply_warnings:
            report["warnings"].append(f"row {index}: {warning}")

        if applied_count == 0:
            report["skipped"].append({"row": index, "reason": "unsupported-or-empty-target", "target": target})
            continue

        report["applied"].append(
            {
                "row": index,
                "target": target,
                "value_count": len(values),
                "applied_count": applied_count,
                "selected_value": values[-1],
            }
        )

    return FieldMappingExecutionResult(protocol_json=protocol, analytes_xml=serialize_xml_document(xml_root), report=report)


def _active_template_rows(field_mapping_settings: dict[str, Any]) -> list[dict[str, Any]]:
    templates = field_mapping_settings.get("templates")
    if not isinstance(templates, dict):
        return []
    active = str(field_mapping_settings.get("active_template") or "")
    rows = templates.get(active)
    return rows if isinstance(rows, list) else []


def _bundle_context(dto_bundle: InputDTOBundle | None) -> dict[str, Any]:
    method = dto_bundle.method if dto_bundle else None
    return {
        "method": {
            "kit_series": str(method.series_name or "") if method else "",
            "kit_name": str(method.product_name or "") if method else "",
            "kit_product_number": str(method.product_number or "") if method else "",
            "addon_product_name": str(method.display_name or "") if method else "",
        },
        "assays": [
            {
                "component_name": str(assay.protocol_display_name or assay.protocol_type or ""),
                "parameter_set_name": str(assay.xml_name or ""),
            }
            for assay in (dto_bundle.assays if dto_bundle else [])
        ],
        "analytes": [{"name": str(analyte.name or "")} for analyte in (dto_bundle.analytes if dto_bundle else [])],
    }


def _normalize_target(target: str) -> str:
    return LEGACY_TARGET_ALIASES.get(target, target)


def _resolve_expression(expression: str, context: dict[str, Any]) -> tuple[list[str], list[str]]:
    if expression.startswith("concat(") and expression.endswith(")"):
        return _resolve_concat(expression, context)
    return _resolve_token(expression, context)


def _resolve_concat(expression: str, context: dict[str, Any]) -> tuple[list[str], list[str]]:
    content = expression[len("concat(") : -1].strip()
    parts = _split_arguments(content)
    delimiter = ""
    tokens = parts
    if parts and parts[0].startswith("delimiter"):
        _, _, raw = parts[0].partition("=")
        cleaned = raw.strip()
        if len(cleaned) >= 2 and cleaned[0] in ("'", '"') and cleaned[-1] == cleaned[0]:
            delimiter = cleaned[1:-1]
        tokens = parts[1:]

    resolved_values: list[list[str]] = []
    warnings: list[str] = []
    for token in tokens:
        values, token_warnings = _resolve_token(token, context)
        if values:
            resolved_values.append(values)
        warnings.extend(token_warnings)

    row_count = max((len(values) for values in resolved_values), default=1)
    out: list[str] = []
    for idx in range(row_count):
        pieces = [values[idx] if idx < len(values) else values[-1] for values in resolved_values]
        out.append(delimiter.join(pieces))
    return out, warnings


def _resolve_token(token: str, context: dict[str, Any]) -> tuple[list[str], list[str]]:
    value = token.strip()
    if value.startswith("default:"):
        return [value[len("default:") :]], []
    if value.startswith("custom:"):
        return [value[len("custom:") :]], []
    if value.startswith("input:"):
        return _resolve_input(value[len("input:") :].strip(), context)
    return [], [f"unsupported token '{value}'"]


def _resolve_input(path: str, context: dict[str, Any]) -> tuple[list[str], list[str]]:
    cursor: list[object] = [context]
    for segment in [segment for segment in path.split(".") if segment]:
        is_list = segment.endswith("[]")
        key = segment[:-2] if is_list else segment
        next_cursor: list[object] = []
        for current in cursor:
            if not isinstance(current, dict):
                continue
            raw = current.get(key)
            if raw is None:
                continue
            if is_list and isinstance(raw, list):
                next_cursor.extend(raw)
            else:
                next_cursor.append(raw)
        cursor = next_cursor

    values = [str(item).strip() for item in cursor if str(item).strip()]
    if not values:
        return [], [f"No source value for input:{path}"]
    return values, []


def _apply_target(target: str, values: list[str], protocol: dict[str, Any], xml_root: ET.Element) -> tuple[int, list[str]]:
    warnings: list[str] = []
    if target == "ProtocolFile.json:MethodInformation.Id":
        method = protocol.setdefault("MethodInformation", {})
        method["Id"] = values[-1]
        if len(values) > 1:
            warnings.append("multiple values resolved for scalar target; used last value")
        return 1, warnings
    if target == "ProtocolFile.json:MethodInformation.Version":
        method = protocol.setdefault("MethodInformation", {})
        method["Version"] = values[-1]
        if len(values) > 1:
            warnings.append("multiple values resolved for scalar target; used last value")
        return 1, warnings
    if target == "ProtocolFile.json:AssayInformation[].Analytes[].Name":
        analyte_nodes = [
            analyte
            for assay in protocol.get("AssayInformation", [])
            if isinstance(assay, dict)
            for analyte in assay.get("Analytes", [])
            if isinstance(analyte, dict)
        ]
        for idx, node in enumerate(analyte_nodes):
            node["Name"] = values[idx] if idx < len(values) else values[-1]
        return len(analyte_nodes), warnings
    if target == "Analytes.xml:Assays[].Analytes[].Analyte.Name":
        analyte_name_nodes = xml_root.findall("./Assays/Assay/Analytes/Analyte/Name")
        for idx, node in enumerate(analyte_name_nodes):
            node.text = values[idx] if idx < len(values) else values[-1]
        return len(analyte_name_nodes), warnings
    if target == "Analytes.xml:Assays[].Analytes[].Analyte.AnalyteUnits[].AnalyteUnit.Name":
        unit_name_nodes = xml_root.findall("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit/Name")
        for idx, node in enumerate(unit_name_nodes):
            node.text = values[idx] if idx < len(values) else values[-1]
        return len(unit_name_nodes), warnings
    return 0, [f"unsupported target '{target}'"]


def _split_arguments(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    for char in value:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            continue
        if char == "(":
            depth += 1
            current.append(char)
            continue
        if char == ")":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts

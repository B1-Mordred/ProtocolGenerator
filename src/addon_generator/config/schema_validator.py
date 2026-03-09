from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from addon_generator.config.models import (
    AddonIdConfig,
    AliasMapsConfig,
    AnalyteAnalytesXmlMapping,
    AnalyteMappingConfig,
    AssayAnalytesXmlMapping,
    AssayMappingConfig,
    AssayProtocolMapping,
    CrossFileMatchConfig,
    ExportPackagingConfig,
    FragmentDefaultsConfig,
    IdGenerationConfig,
    MappingConfigModel,
    MethodAnalytesXmlMapping,
    MethodMappingConfig,
    MethodProtocolMapping,
    SequentialIdConfig,
    UnitAnalytesXmlMapping,
    UnitMappingConfig,
    WorkbookParsingRulesConfig,
)
from addon_generator.mapping.field_path import parse_field_path


class MappingConfigError(ValueError):
    pass


def _ensure_mapping(value: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MappingConfigError(f"{path} must be an object")
    return value


def _ensure_list(value: Any, *, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise MappingConfigError(f"{path} must be a list")
    return value


def _ensure_string(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MappingConfigError(f"{path} must be a non-empty string")
    return value


def _ensure_bool(value: Any, *, path: str) -> bool:
    if not isinstance(value, bool):
        raise MappingConfigError(f"{path} must be a boolean")
    return value


def _ensure_samples_layout_type(value: Any, *, path: str) -> str:
    layout = _ensure_string(value, path=path)
    allowed = {"SAMPLES_LAYOUT_COMBINED", "SAMPLES_LAYOUT_SPLIT"}
    if layout not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise MappingConfigError(f"{path} must be one of: {allowed_values}")
    return layout


def _ensure_non_negative_int(value: Any, *, path: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise MappingConfigError(f"{path} must be a non-negative integer")
    return value


def _ensure_allowed_keys(value: dict[str, Any], *, path: str, allowed: set[str]) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        allowed_items = ", ".join(sorted(allowed))
        unknown_items = ", ".join(unknown)
        raise MappingConfigError(f"Unknown key(s) under {path}: {unknown_items}. Allowed keys: {allowed_items}")


def _validate_field_path(path: str, *, source: str) -> None:
    try:
        parse_field_path(path)
    except ValueError as exc:
        raise MappingConfigError(f"Invalid field path for {source}: {path}. Use dot notation like 'a.b[0].c'.") from exc


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _prepare_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in content.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    return lines


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        cur_indent, text = lines[index]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise MappingConfigError("Invalid YAML indentation")
        if text.startswith("- "):
            break
        if ":" not in text:
            raise MappingConfigError(f"Invalid YAML mapping entry: {text}")
        key, rest = text.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        index += 1
        if rest == "":
            if index >= len(lines) or lines[index][0] <= cur_indent:
                result[key] = {}
            else:
                next_indent, next_text = lines[index]
                if next_text.startswith("- "):
                    value, index = _parse_list(lines, index, next_indent)
                else:
                    value, index = _parse_mapping(lines, index, next_indent)
                result[key] = value
        else:
            result[key] = _parse_scalar(rest)
    return result, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        cur_indent, text = lines[index]
        if cur_indent < indent:
            break
        if cur_indent != indent or not text.startswith("- "):
            break
        item_text = text[2:].strip()
        index += 1

        if item_text == "":
            if index >= len(lines) or lines[index][0] <= cur_indent:
                result.append(None)
            else:
                next_indent, next_text = lines[index]
                if next_text.startswith("- "):
                    item, index = _parse_list(lines, index, next_indent)
                else:
                    item, index = _parse_mapping(lines, index, next_indent)
                result.append(item)
            continue

        if ":" in item_text:
            key, rest = item_text.split(":", 1)
            entry: dict[str, Any] = {}
            rest = rest.strip()
            if rest:
                entry[key.strip()] = _parse_scalar(rest)
            else:
                entry[key.strip()] = {}
            while index < len(lines) and lines[index][0] > cur_indent:
                sub_indent, sub_text = lines[index]
                if sub_indent != cur_indent + 2:
                    break
                if sub_text.startswith("- "):
                    break
                sub_key, sub_rest = sub_text.split(":", 1)
                sub_key = sub_key.strip()
                sub_rest = sub_rest.strip()
                index += 1
                if sub_rest == "":
                    if index < len(lines) and lines[index][0] > sub_indent:
                        if lines[index][1].startswith("- "):
                            sub_value, index = _parse_list(lines, index, lines[index][0])
                        else:
                            sub_value, index = _parse_mapping(lines, index, lines[index][0])
                        entry[sub_key] = sub_value
                    else:
                        entry[sub_key] = {}
                else:
                    entry[sub_key] = _parse_scalar(sub_rest)
            result.append(entry)
        else:
            result.append(_parse_scalar(item_text))

    return result, index


def load_yaml_without_pyyaml(content: str) -> dict[str, Any]:
    lines = _prepare_lines(content)
    if not lines:
        raise MappingConfigError("Empty mapping config")
    if lines[0][1].startswith("- "):
        raise MappingConfigError("Config root must be an object")
    parsed, index = _parse_mapping(lines, 0, lines[0][0])
    if index != len(lines):
        raise MappingConfigError("Could not parse full YAML content")
    if not isinstance(parsed, dict):
        raise MappingConfigError("Config root must be an object")
    return parsed


def parse_mapping_config_dict(raw: dict[str, Any]) -> MappingConfigModel:
    _ensure_allowed_keys(
        raw,
        path="root",
        allowed={
            "version",
            "ids",
            "method_mapping",
            "assay_mapping",
            "analyte_mapping",
            "unit_mapping",
            "protocol_defaults",
            "export_packaging",
            "alias_maps",
            "workbook_parsing_rules",
        },
    )
    if raw.get("version") != 1:
        raise MappingConfigError("version must be 1")

    for key in ("ids", "method_mapping", "assay_mapping", "analyte_mapping", "unit_mapping"):
        if key not in raw:
            raise MappingConfigError(f"Missing mandatory section: {key}")

    ids_raw = _ensure_mapping(raw["ids"], path="ids")
    _ensure_allowed_keys(ids_raw, path="ids", allowed={"addon", "assay", "analyte", "analyte_unit"})
    addon_raw = _ensure_mapping(ids_raw.get("addon", {}), path="ids.addon")
    _ensure_allowed_keys(addon_raw, path="ids.addon", allowed={"fixed"})
    addon = AddonIdConfig(fixed=_ensure_non_negative_int(addon_raw.get("fixed", 0), path="ids.addon.fixed"))

    def _seq_id(section: str) -> SequentialIdConfig:
        section_raw = _ensure_mapping(ids_raw.get(section), path=f"ids.{section}")
        _ensure_allowed_keys(section_raw, path=f"ids.{section}", allowed={"strategy", "start"})
        strategy = section_raw.get("strategy")
        if strategy != "sequential":
            raise MappingConfigError(f"ids.{section}.strategy must be 'sequential'")
        return SequentialIdConfig(strategy="sequential", start=_ensure_non_negative_int(section_raw.get("start"), path=f"ids.{section}.start"))

    ids = IdGenerationConfig(addon=addon, assay=_seq_id("assay"), analyte=_seq_id("analyte"), analyte_unit=_seq_id("analyte_unit"))

    method_raw = _ensure_mapping(raw["method_mapping"], path="method_mapping")
    _ensure_allowed_keys(method_raw, path="method_mapping", allowed={"protocol", "analytes_xml"})
    method_protocol_raw = _ensure_mapping(method_raw.get("protocol"), path="method_mapping.protocol")
    _ensure_allowed_keys(method_protocol_raw, path="method_mapping.protocol", allowed={"id", "version"})
    method_xml_raw = _ensure_mapping(method_raw.get("analytes_xml"), path="method_mapping.analytes_xml")
    _ensure_allowed_keys(method_xml_raw, path="method_mapping.analytes_xml", allowed={"method_id", "method_version"})
    method_protocol_id = _ensure_string(method_protocol_raw.get("id"), path="method_mapping.protocol.id")
    method_protocol_version = _ensure_string(method_protocol_raw.get("version"), path="method_mapping.protocol.version")
    method_xml_id = _ensure_string(method_xml_raw.get("method_id"), path="method_mapping.analytes_xml.method_id")
    method_xml_version = _ensure_string(method_xml_raw.get("method_version"), path="method_mapping.analytes_xml.method_version")
    for source, value in {
        "method_mapping.protocol.id": method_protocol_id,
        "method_mapping.protocol.version": method_protocol_version,
        "method_mapping.analytes_xml.method_id": method_xml_id,
        "method_mapping.analytes_xml.method_version": method_xml_version,
    }.items():
        _validate_field_path(value, source=source)
    method_mapping = MethodMappingConfig(
        protocol=MethodProtocolMapping(id=method_protocol_id, version=method_protocol_version),
        analytes_xml=MethodAnalytesXmlMapping(method_id=method_xml_id, method_version=method_xml_version),
    )

    assay_raw = _ensure_mapping(raw["assay_mapping"], path="assay_mapping")
    _ensure_allowed_keys(assay_raw, path="assay_mapping", allowed={"internal_identity", "protocol", "analytes_xml", "cross_file_match"})
    assay_protocol_raw = _ensure_mapping(assay_raw.get("protocol"), path="assay_mapping.protocol")
    _ensure_allowed_keys(assay_protocol_raw, path="assay_mapping.protocol", allowed={"type", "display_name"})
    assay_xml_raw = _ensure_mapping(assay_raw.get("analytes_xml"), path="assay_mapping.analytes_xml")
    _ensure_allowed_keys(assay_xml_raw, path="assay_mapping.analytes_xml", allowed={"id", "name", "addon_ref"})
    cross_raw = _ensure_mapping(assay_raw.get("cross_file_match", {}), path="assay_mapping.cross_file_match")
    _ensure_allowed_keys(cross_raw, path="assay_mapping.cross_file_match", allowed={"mode", "alias_map", "protocol_field", "analytes_xml_field"})

    assay_identity = _ensure_string(assay_raw.get("internal_identity"), path="assay_mapping.internal_identity")
    assay_type = _ensure_string(assay_protocol_raw.get("type"), path="assay_mapping.protocol.type")
    assay_name = _ensure_string(assay_xml_raw.get("name"), path="assay_mapping.analytes_xml.name")
    for source, value in {
        "assay_mapping.internal_identity": assay_identity,
        "assay_mapping.protocol.type": assay_type,
        "assay_mapping.analytes_xml.name": assay_name,
        "assay_mapping.analytes_xml.id": _ensure_string(assay_xml_raw.get("id"), path="assay_mapping.analytes_xml.id"),
        "assay_mapping.analytes_xml.addon_ref": _ensure_string(assay_xml_raw.get("addon_ref"), path="assay_mapping.analytes_xml.addon_ref"),
    }.items():
        _validate_field_path(value, source=source)

    mode = cross_raw.get("mode", "exact")
    if mode not in {"exact", "normalized", "alias_map", "explicit_key"}:
        raise MappingConfigError(f"Unknown match mode: {mode}")
    alias_map: dict[str, str] | None = None
    protocol_field: str | None = None
    analytes_xml_field: str | None = None
    if mode == "alias_map":
        alias_map_raw = _ensure_mapping(cross_raw.get("alias_map"), path="assay_mapping.cross_file_match.alias_map")
        if not alias_map_raw:
            raise MappingConfigError("assay_mapping.cross_file_match.alias_map must not be empty")
        alias_map = {}
        for alias, target in alias_map_raw.items():
            a = _ensure_string(alias, path="assay_mapping.cross_file_match.alias_map key")
            t = _ensure_string(target, path=f"assay_mapping.cross_file_match.alias_map.{alias}")
            alias_map[a] = t
    if mode == "explicit_key":
        protocol_field = _ensure_string(cross_raw.get("protocol_field"), path="assay_mapping.cross_file_match.protocol_field")
        analytes_xml_field = _ensure_string(cross_raw.get("analytes_xml_field"), path="assay_mapping.cross_file_match.analytes_xml_field")
        _validate_field_path(protocol_field, source="assay_mapping.cross_file_match.protocol_field")
        _validate_field_path(analytes_xml_field, source="assay_mapping.cross_file_match.analytes_xml_field")

    assay_mapping = AssayMappingConfig(
        internal_identity=assay_identity,
        protocol=AssayProtocolMapping(type=assay_type, display_name=assay_protocol_raw.get("display_name")),
        analytes_xml=AssayAnalytesXmlMapping(
            id=_ensure_string(assay_xml_raw.get("id"), path="assay_mapping.analytes_xml.id"),
            name=assay_name,
            addon_ref=_ensure_string(assay_xml_raw.get("addon_ref"), path="assay_mapping.analytes_xml.addon_ref"),
        ),
        cross_file_match=CrossFileMatchConfig(mode=mode, alias_map=alias_map, protocol_field=protocol_field, analytes_xml_field=analytes_xml_field),
    )

    analyte_raw = _ensure_mapping(raw["analyte_mapping"], path="analyte_mapping")
    _ensure_allowed_keys(analyte_raw, path="analyte_mapping", allowed={"internal_identity", "analytes_xml"})
    analyte_xml_raw = _ensure_mapping(analyte_raw.get("analytes_xml"), path="analyte_mapping.analytes_xml")
    _ensure_allowed_keys(analyte_xml_raw, path="analyte_mapping.analytes_xml", allowed={"id", "name", "assay_ref", "assay_information_type"})
    analyte_identity = _ensure_string(analyte_raw.get("internal_identity"), path="analyte_mapping.internal_identity")
    analyte_id = _ensure_string(analyte_xml_raw.get("id"), path="analyte_mapping.analytes_xml.id")
    analyte_name = _ensure_string(analyte_xml_raw.get("name"), path="analyte_mapping.analytes_xml.name")
    analyte_assay_ref = _ensure_string(analyte_xml_raw.get("assay_ref"), path="analyte_mapping.analytes_xml.assay_ref")
    for source, value in {
        "analyte_mapping.internal_identity": analyte_identity,
        "analyte_mapping.analytes_xml.id": analyte_id,
        "analyte_mapping.analytes_xml.name": analyte_name,
        "analyte_mapping.analytes_xml.assay_ref": analyte_assay_ref,
    }.items():
        _validate_field_path(value, source=source)
    analyte_mapping = AnalyteMappingConfig(
        internal_identity=analyte_identity,
        analytes_xml=AnalyteAnalytesXmlMapping(
            id=analyte_id,
            name=analyte_name,
            assay_ref=analyte_assay_ref,
            assay_information_type=analyte_xml_raw.get("assay_information_type"),
        ),
    )

    unit_raw = _ensure_mapping(raw["unit_mapping"], path="unit_mapping")
    _ensure_allowed_keys(unit_raw, path="unit_mapping", allowed={"analytes_xml"})
    unit_xml_raw = _ensure_mapping(unit_raw.get("analytes_xml"), path="unit_mapping.analytes_xml")
    _ensure_allowed_keys(unit_xml_raw, path="unit_mapping.analytes_xml", allowed={"id", "name", "analyte_ref"})
    unit_id = _ensure_string(unit_xml_raw.get("id"), path="unit_mapping.analytes_xml.id")
    unit_name = _ensure_string(unit_xml_raw.get("name"), path="unit_mapping.analytes_xml.name")
    unit_analyte_ref = _ensure_string(unit_xml_raw.get("analyte_ref"), path="unit_mapping.analytes_xml.analyte_ref")
    for source, value in {
        "unit_mapping.analytes_xml.id": unit_id,
        "unit_mapping.analytes_xml.name": unit_name,
        "unit_mapping.analytes_xml.analyte_ref": unit_analyte_ref,
    }.items():
        _validate_field_path(value, source=source)
    unit_mapping = UnitMappingConfig(analytes_xml=UnitAnalytesXmlMapping(id=unit_id, name=unit_name, analyte_ref=unit_analyte_ref))

    protocol_defaults_raw = _ensure_mapping(raw.get("protocol_defaults", {}), path="protocol_defaults")
    _ensure_allowed_keys(protocol_defaults_raw, path="protocol_defaults", allowed={"method_information", "assay_information", "loading_workflow_steps", "processing_workflow_steps"})
    loading_steps = protocol_defaults_raw.get("loading_workflow_steps", [])
    processing_steps = protocol_defaults_raw.get("processing_workflow_steps", [])
    _ensure_list(loading_steps, path="protocol_defaults.loading_workflow_steps")
    _ensure_list(processing_steps, path="protocol_defaults.processing_workflow_steps")
    method_information_defaults = _ensure_mapping(protocol_defaults_raw.get("method_information", {}), path="protocol_defaults.method_information")
    if "SamplesLayoutType" in method_information_defaults:
        _ensure_samples_layout_type(method_information_defaults["SamplesLayoutType"], path="protocol_defaults.method_information.SamplesLayoutType")

    protocol_defaults = FragmentDefaultsConfig(
        method_information=method_information_defaults,
        assay_information=_ensure_mapping(protocol_defaults_raw.get("assay_information", {}), path="protocol_defaults.assay_information"),
        loading_workflow_steps=loading_steps,
        processing_workflow_steps=processing_steps,
    )

    export_packaging_raw = _ensure_mapping(raw.get("export_packaging", {}), path="export_packaging")
    _ensure_allowed_keys(export_packaging_raw, path="export_packaging", allowed={"include_protocol_file", "include_analytes_xml"})
    export_packaging = ExportPackagingConfig(
        include_protocol_file=_ensure_bool(export_packaging_raw.get("include_protocol_file", True), path="export_packaging.include_protocol_file"),
        include_analytes_xml=_ensure_bool(export_packaging_raw.get("include_analytes_xml", True), path="export_packaging.include_analytes_xml"),
    )

    alias_maps_raw = _ensure_mapping(raw.get("alias_maps", {}), path="alias_maps")
    _ensure_allowed_keys(alias_maps_raw, path="alias_maps", allowed={"assays", "analytes", "units"})
    alias_maps = AliasMapsConfig(
        assays=_ensure_mapping(alias_maps_raw.get("assays", {}), path="alias_maps.assays"),
        analytes=_ensure_mapping(alias_maps_raw.get("analytes", {}), path="alias_maps.analytes"),
        units=_ensure_mapping(alias_maps_raw.get("units", {}), path="alias_maps.units"),
    )

    workbook_rules_raw = _ensure_mapping(raw.get("workbook_parsing_rules", {}), path="workbook_parsing_rules")
    _ensure_allowed_keys(workbook_rules_raw, path="workbook_parsing_rules", allowed={"strict_headers", "trim_whitespace", "normalize_unicode"})
    workbook_parsing_rules = WorkbookParsingRulesConfig(
        strict_headers=_ensure_bool(workbook_rules_raw.get("strict_headers", True), path="workbook_parsing_rules.strict_headers"),
        trim_whitespace=_ensure_bool(workbook_rules_raw.get("trim_whitespace", True), path="workbook_parsing_rules.trim_whitespace"),
        normalize_unicode=_ensure_bool(workbook_rules_raw.get("normalize_unicode", False), path="workbook_parsing_rules.normalize_unicode"),
    )

    return MappingConfigModel(
        version=1,
        ids=ids,
        method_mapping=method_mapping,
        assay_mapping=assay_mapping,
        analyte_mapping=analyte_mapping,
        unit_mapping=unit_mapping,
        protocol_defaults=protocol_defaults,
        export_packaging=export_packaging,
        alias_maps=alias_maps,
        workbook_parsing_rules=workbook_parsing_rules,
    )


def load_mapping_config_model(path: str | Path) -> MappingConfigModel:
    content = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(content)
    except ModuleNotFoundError:
        data = load_yaml_without_pyyaml(content)
    if not isinstance(data, dict):
        raise MappingConfigError("Config root must be an object")
    return parse_mapping_config_dict(data)


def model_to_raw(model: MappingConfigModel) -> dict[str, Any]:
    return asdict(model)

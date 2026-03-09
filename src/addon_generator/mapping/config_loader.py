from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from addon_generator.mapping.field_path import parse_field_path


class MappingConfigError(ValueError):
    pass


@dataclass(slots=True)
class MappingConfig:
    raw: dict[str, Any]


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


def _validate_field_path(path: str, *, source: str) -> None:
    try:
        parse_field_path(path)
    except ValueError as exc:
        raise MappingConfigError(f"Invalid field path for {source}: {path}") from exc


def validate_mapping_config(raw: dict[str, Any]) -> MappingConfig:
    if raw.get("version") != 1:
        raise MappingConfigError("version must be 1")

    for key in ("ids", "method_mapping", "assay_mapping", "analyte_mapping", "unit_mapping"):
        if key not in raw:
            raise MappingConfigError(f"Missing mandatory section: {key}")

    ids = _ensure_mapping(raw["ids"], path="ids")
    for key in ("assay", "analyte", "analyte_unit"):
        section = _ensure_mapping(ids.get(key), path=f"ids.{key}")
        if section.get("strategy") != "sequential":
            raise MappingConfigError(f"ids.{key}.strategy must be 'sequential'")
        start = section.get("start")
        if not isinstance(start, int) or start < 0:
            raise MappingConfigError(f"ids.{key}.start must be a non-negative integer")

    assay_mapping_root = _ensure_mapping(raw["assay_mapping"], path="assay_mapping")
    cross_file_match = _ensure_mapping(assay_mapping_root.get("cross_file_match", {}), path="assay_mapping.cross_file_match")
    mode = cross_file_match.get("mode", "exact")
    if mode not in {"exact", "normalized", "alias_map", "explicit_key"}:
        raise MappingConfigError(f"Unknown match mode: {mode}")

    method_mapping = _ensure_mapping(raw["method_mapping"], path="method_mapping")
    method_protocol = _ensure_mapping(method_mapping.get("protocol"), path="method_mapping.protocol")
    method_xml = _ensure_mapping(method_mapping.get("analytes_xml"), path="method_mapping.analytes_xml")
    _validate_field_path(_ensure_string(method_protocol.get("id"), path="method_mapping.protocol.id"), source="method_mapping.protocol.id")
    _validate_field_path(_ensure_string(method_protocol.get("version"), path="method_mapping.protocol.version"), source="method_mapping.protocol.version")
    _validate_field_path(_ensure_string(method_xml.get("method_id"), path="method_mapping.analytes_xml.method_id"), source="method_mapping.analytes_xml.method_id")
    _validate_field_path(_ensure_string(method_xml.get("method_version"), path="method_mapping.analytes_xml.method_version"), source="method_mapping.analytes_xml.method_version")

    assay_mapping = assay_mapping_root
    protocol_defaults = raw.get("protocol_defaults", {})
    if protocol_defaults and not isinstance(protocol_defaults, dict):
        raise MappingConfigError("protocol_defaults must be an object")
    _validate_field_path(_ensure_string(assay_mapping.get("internal_identity"), path="assay_mapping.internal_identity"), source="assay_mapping.internal_identity")
    assay_protocol = _ensure_mapping(assay_mapping.get("protocol"), path="assay_mapping.protocol")
    assay_xml = _ensure_mapping(assay_mapping.get("analytes_xml"), path="assay_mapping.analytes_xml")
    _validate_field_path(_ensure_string(assay_protocol.get("type"), path="assay_mapping.protocol.type"), source="assay_mapping.protocol.type")
    _validate_field_path(_ensure_string(assay_xml.get("name"), path="assay_mapping.analytes_xml.name"), source="assay_mapping.analytes_xml.name")

    if mode == "alias_map":
        alias_map = _ensure_mapping(cross_file_match.get("alias_map"), path="assay_mapping.cross_file_match.alias_map")
        if not alias_map:
            raise MappingConfigError("assay_mapping.cross_file_match.alias_map must not be empty")
        for alias, target in alias_map.items():
            _ensure_string(alias, path="assay_mapping.cross_file_match.alias_map key")
            _ensure_string(target, path=f"assay_mapping.cross_file_match.alias_map.{alias}")
    elif mode == "explicit_key":
        _validate_field_path(_ensure_string(cross_file_match.get("protocol_field"), path="assay_mapping.cross_file_match.protocol_field"), source="assay_mapping.cross_file_match.protocol_field")
        _validate_field_path(_ensure_string(cross_file_match.get("analytes_xml_field"), path="assay_mapping.cross_file_match.analytes_xml_field"), source="assay_mapping.cross_file_match.analytes_xml_field")

    analyte_mapping = _ensure_mapping(raw["analyte_mapping"], path="analyte_mapping")
    analyte_xml = _ensure_mapping(analyte_mapping.get("analytes_xml"), path="analyte_mapping.analytes_xml")
    for field_name in ("id", "name", "assay_ref"):
        _validate_field_path(_ensure_string(analyte_xml.get(field_name), path=f"analyte_mapping.analytes_xml.{field_name}"), source=f"analyte_mapping.analytes_xml.{field_name}")

    unit_mapping = _ensure_mapping(raw["unit_mapping"], path="unit_mapping")
    unit_xml = _ensure_mapping(unit_mapping.get("analytes_xml"), path="unit_mapping.analytes_xml")
    for field_name in ("id", "name", "analyte_ref"):
        _validate_field_path(_ensure_string(unit_xml.get(field_name), path=f"unit_mapping.analytes_xml.{field_name}"), source=f"unit_mapping.analytes_xml.{field_name}")

    loading_steps = protocol_defaults.get("loading_workflow_steps")
    if loading_steps is not None:
        _ensure_list(loading_steps, path="protocol_defaults.loading_workflow_steps")

    return MappingConfig(raw=raw)


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


def _load_yaml_without_pyyaml(content: str) -> dict[str, Any]:
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


def load_mapping_config(path: str | Path) -> MappingConfig:
    content = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(content)
    except ModuleNotFoundError:
        data = _load_yaml_without_pyyaml(content)
    if not isinstance(data, dict):
        raise MappingConfigError("Config root must be an object")
    return validate_mapping_config(data)

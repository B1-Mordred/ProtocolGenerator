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


def _validate_field_path(path: str) -> None:
    try:
        parse_field_path(path)
    except ValueError as exc:
        raise MappingConfigError(f"Invalid field path: {path}") from exc


def validate_mapping_config(raw: dict[str, Any]) -> MappingConfig:
    if raw.get("version") != 1:
        raise MappingConfigError("version must be 1")

    for key in ("ids", "method_mapping", "assay_mapping", "analyte_mapping", "unit_mapping"):
        if key not in raw:
            raise MappingConfigError(f"Missing mandatory section: {key}")

    mode = raw["assay_mapping"].get("cross_file_match", {}).get("mode", "exact")
    if mode not in {"exact", "normalized", "alias_map", "explicit_key"}:
        raise MappingConfigError(f"Unknown match mode: {mode}")

    method_mapping = raw["method_mapping"]
    _validate_field_path(method_mapping["protocol"]["id"])
    _validate_field_path(method_mapping["protocol"]["version"])
    _validate_field_path(method_mapping["analytes_xml"]["method_id"])
    _validate_field_path(method_mapping["analytes_xml"]["method_version"])

    assay_mapping = raw["assay_mapping"]
    protocol_defaults = raw.get("protocol_defaults", {})
    if protocol_defaults and not isinstance(protocol_defaults, dict):
        raise MappingConfigError("protocol_defaults must be an object")
    _validate_field_path(assay_mapping["internal_identity"])
    _validate_field_path(assay_mapping["protocol"]["type"])
    _validate_field_path(assay_mapping["analytes_xml"]["name"])

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

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


def load_mapping_config(path: str | Path) -> MappingConfig:
    content = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(content)
    except ModuleNotFoundError:
        import json
        data = json.loads(content)
    if not isinstance(data, dict):
        raise MappingConfigError("Config root must be an object")
    return validate_mapping_config(data)

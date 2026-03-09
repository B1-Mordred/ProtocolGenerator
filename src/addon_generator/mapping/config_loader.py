from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


from .field_path import parse_field_path

_ALLOWED_MODES = {"exact", "normalized", "alias_map", "explicit_key"}


class MappingConfigError(ValueError):
    """Raised when the mapping configuration is unsafe or inconsistent."""


@dataclass(slots=True)
class ProjectionConfig:
    mode: str
    source_path: str
    target_path: str
    explicit_key_path: str | None = None
    alias_map: dict[str, str] | None = None


@dataclass(slots=True)
class MappingConfig:
    version: str
    defaults: dict[str, Any]
    id_strategies: dict[str, str]
    method: ProjectionConfig
    assay: ProjectionConfig
    analyte: ProjectionConfig


def _validate_projection(name: str, data: dict[str, Any]) -> ProjectionConfig:
    mode = data.get("mode", "normalized")
    if mode not in _ALLOWED_MODES:
        raise MappingConfigError(f"Unknown mode for {name}: {mode}")

    source_path = data.get("source_path")
    target_path = data.get("target_path")
    if not isinstance(source_path, str) or not isinstance(target_path, str):
        raise MappingConfigError(f"Projection {name} requires string source_path and target_path")

    try:
        parse_field_path(source_path)
        parse_field_path(target_path)
    except ValueError as exc:
        raise MappingConfigError(f"Invalid field path for {name}: {exc}") from exc

    if source_path == target_path and mode != "explicit_key":
        raise MappingConfigError(f"Ambiguous projection for {name}: source_path and target_path are identical")

    explicit_key_path = data.get("explicit_key_path")
    if explicit_key_path is not None:
        if not isinstance(explicit_key_path, str):
            raise MappingConfigError(f"explicit_key_path for {name} must be a string")
        try:
            parse_field_path(explicit_key_path)
        except ValueError as exc:
            raise MappingConfigError(f"Invalid explicit_key_path for {name}: {exc}") from exc

    alias_map_data = data.get("alias_map")
    alias_map: dict[str, str] | None = None
    if alias_map_data is not None:
        if mode != "alias_map":
            raise MappingConfigError(f"alias_map is only allowed when mode is alias_map ({name})")
        if not isinstance(alias_map_data, dict):
            raise MappingConfigError(f"alias_map for {name} must be an object")

        alias_map = {}
        for alias, canonical in alias_map_data.items():
            if not isinstance(alias, str) or not isinstance(canonical, str):
                raise MappingConfigError(f"alias_map for {name} only accepts string keys and values")
            if alias in alias_map and alias_map[alias] != canonical:
                raise MappingConfigError(f"Alias contradiction for {name}: {alias}")
            alias_map[alias] = canonical

        normalized_aliases = {}
        for alias, canonical in alias_map.items():
            folded = alias.casefold()
            if folded in normalized_aliases and normalized_aliases[folded] != canonical:
                raise MappingConfigError(
                    f"Alias contradiction for {name}: case-insensitive alias collision for {alias}"
                )
            normalized_aliases[folded] = canonical

    return ProjectionConfig(
        mode=mode,
        source_path=source_path,
        target_path=target_path,
        explicit_key_path=explicit_key_path,
        alias_map=alias_map,
    )


def validate_mapping_config(raw: dict[str, Any]) -> MappingConfig:
    if not isinstance(raw, dict):
        raise MappingConfigError("Mapping config root must be an object")

    version = raw.get("version")
    if version != "v1":
        raise MappingConfigError("Only mapping config version v1 is supported")

    defaults = raw.get("defaults", {})
    if not isinstance(defaults, dict):
        raise MappingConfigError("defaults must be an object")

    id_strategies = raw.get("id_strategies", {})
    if not isinstance(id_strategies, dict):
        raise MappingConfigError("id_strategies must be an object")

    projections = raw.get("projections")
    if not isinstance(projections, dict):
        raise MappingConfigError("projections must be an object")

    required = ["method", "assay", "analyte"]
    missing = [name for name in required if name not in projections]
    if missing:
        raise MappingConfigError(f"Missing projections: {', '.join(missing)}")

    method = _validate_projection("method", projections["method"])
    assay = _validate_projection("assay", projections["assay"])
    analyte = _validate_projection("analyte", projections["analyte"])

    return MappingConfig(
        version=version,
        defaults=defaults,
        id_strategies=id_strategies,
        method=method,
        assay=assay,
        analyte=analyte,
    )


def load_mapping_config(path: str | Path) -> MappingConfig:
    config_path = Path(path)
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise MappingConfigError("PyYAML is required to load YAML mapping config files") from exc

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return validate_mapping_config(raw)

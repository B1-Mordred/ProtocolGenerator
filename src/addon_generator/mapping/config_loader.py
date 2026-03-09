from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from addon_generator.config.models import MappingConfigModel
from addon_generator.config.schema_validator import (
    MappingConfigError,
    load_mapping_config_model,
    model_to_raw,
    parse_mapping_config_dict,
)


@dataclass(slots=True)
class MappingConfig:
    model: MappingConfigModel
    raw: dict[str, Any]


def validate_mapping_config(raw: dict[str, Any]) -> MappingConfig:
    model = parse_mapping_config_dict(raw)
    return MappingConfig(model=model, raw=model_to_raw(model))


def load_mapping_config(path: str | Path) -> MappingConfig:
    model = load_mapping_config_model(path)
    return MappingConfig(model=model, raw=model_to_raw(model))

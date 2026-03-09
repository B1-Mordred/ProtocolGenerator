import pytest

from addon_generator.mapping.config_loader import MappingConfigError, load_mapping_config, validate_mapping_config
from addon_generator.mapping.field_path import get_field_value, parse_field_path
from addon_generator.mapping.normalizers import normalize_for_matching


def test_field_path_resolution_and_normalize() -> None:
    assert len(parse_field_path("a.b[0].c")) == 4
    assert get_field_value({"a": {"b": [{"c": "x"}]}}, "a.b[0].c") == "x"
    assert normalize_for_matching("  A   B  ") == "a b"


def test_config_validation() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    assert cfg.raw["version"] == 1

    bad = {"version": 1}
    with pytest.raises(MappingConfigError):
        validate_mapping_config(bad)

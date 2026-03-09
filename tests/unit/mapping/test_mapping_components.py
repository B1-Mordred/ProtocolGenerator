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


def test_config_validation_rejects_invalid_semantics() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw

    bad_alias_mode = {
        **cfg,
        "assay_mapping": {
            **cfg["assay_mapping"],
            "cross_file_match": {"mode": "alias_map", "alias_map": {}},
        },
    }
    with pytest.raises(MappingConfigError, match="alias_map must not be empty"):
        validate_mapping_config(bad_alias_mode)

    bad_ids = {
        **cfg,
        "ids": {
            **cfg["ids"],
            "assay": {"strategy": "random", "start": -1},
        },
    }
    with pytest.raises(MappingConfigError, match="strategy"):
        validate_mapping_config(bad_ids)


def test_config_validation_requires_mapping_shapes() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    bad = {
        **cfg,
        "method_mapping": {"protocol": "method.method_id", "analytes_xml": cfg["method_mapping"]["analytes_xml"]},
    }
    with pytest.raises(MappingConfigError, match="method_mapping.protocol must be an object"):
        validate_mapping_config(bad)


def test_config_loader_parses_yaml_without_pyyaml(monkeypatch):
    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001, A002
        if name == "yaml":
            raise ModuleNotFoundError("yaml not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    cfg = load_mapping_config("config/mapping.v1.yaml")
    assert cfg.raw["version"] == 1
    assert cfg.raw["protocol_defaults"]["method_information"]["DisplayName"] == "Method"

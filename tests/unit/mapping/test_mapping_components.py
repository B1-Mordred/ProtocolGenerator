import pytest

from addon_generator.mapping.config_loader import MappingConfigError, load_mapping_config, validate_mapping_config
from addon_generator.mapping.field_path import get_field_value, parse_field_path
from addon_generator.mapping.normalizers import normalize_for_matching


def test_field_path_resolution_and_normalize() -> None:
    assert len(parse_field_path("a.b[0].c")) == 4
    assert get_field_value({"a": {"b": [{"c": "x"}]}}, "a.b[0].c") == "x"
    assert normalize_for_matching("  A   B  ") == "a b"


def test_config_validation_returns_typed_wrapper() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    assert cfg.model.version == 1
    assert cfg.raw["version"] == 1


def test_config_validation_requires_mandatory_sections() -> None:
    with pytest.raises(MappingConfigError, match="Missing mandatory section: ids"):
        validate_mapping_config({"version": 1})


def test_config_validation_rejects_unknown_keys() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    cfg["method_mapping"]["protocol"]["unknown_field"] = "bad"
    with pytest.raises(MappingConfigError, match=r"Unknown key\(s\) under method_mapping\.protocol"):
        validate_mapping_config(cfg)


def test_config_validation_rejects_bad_field_path_syntax() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    cfg["unit_mapping"]["analytes_xml"]["id"] = "unit.["
    with pytest.raises(MappingConfigError, match="Invalid field path"):
        validate_mapping_config(cfg)


def test_config_validation_rejects_invalid_enum_mode() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    cfg["assay_mapping"]["cross_file_match"]["mode"] = "fuzzy"
    with pytest.raises(MappingConfigError, match="Unknown match mode"):
        validate_mapping_config(cfg)


def test_config_validation_rejects_invalid_id_mode() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    cfg["ids"]["assay"]["strategy"] = "random"
    with pytest.raises(MappingConfigError, match="ids.assay.strategy"):
        validate_mapping_config(cfg)


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

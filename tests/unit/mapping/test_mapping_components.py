import pytest

from addon_generator.mapping.config_loader import MappingConfigError, load_mapping_config, validate_mapping_config
from addon_generator.mapping.field_path import get_field_value, parse_field_path
from addon_generator.mapping.normalizers import normalize_for_matching
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.domain.models import AddonModel, AssayModel
from addon_generator.domain.issues import IssueSeverity


def test_field_path_resolution_and_normalize() -> None:
    assert len(parse_field_path("a.b[0].c")) == 4
    assert get_field_value({"a": {"b": [{"c": "x"}]}}, "a.b[0].c") == "x"
    assert normalize_for_matching("  A   B  ") == "a b"


def test_config_validation_returns_typed_wrapper() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    assert cfg.model.version == 1
    assert cfg.raw["version"] == 1


def test_config_loader_accepts_windows_style_relative_path() -> None:
    cfg = load_mapping_config(r"config\mapping.v1.yaml")

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

def test_config_validation_rejects_invalid_samples_layout_type() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml").raw
    cfg["protocol_defaults"]["method_information"]["SamplesLayoutType"] = "SAMPLES_LAYOUT_SEPARATE"
    with pytest.raises(MappingConfigError, match="protocol_defaults.method_information.SamplesLayoutType"):
        validate_mapping_config(cfg)


def test_link_resolver_does_not_default_xml_name_from_protocol_type() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    projection = LinkResolver(cfg).resolve_assay_projection(
        AssayModel(key="assay:1", protocol_type="PROTO-ONLY", xml_name=None, protocol_display_name="Display")
    )

    assert projection.protocol_type == "PROTO-ONLY"
    assert projection.protocol_display_name == "Display"
    assert projection.xml_name == ""


def test_link_resolver_applies_explicit_projection_fallbacks_when_configured() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    cfg.raw["assay_mapping"]["projection_fallbacks"] = {"xml_name": ("protocol_type",)}
    projection = LinkResolver(cfg).resolve_assay_projection(
        AssayModel(key="assay:1", protocol_type="PROTO-ONLY", xml_name=None)
    )

    assert projection.xml_name == "PROTO-ONLY"


def test_link_resolver_cross_file_mismatch_includes_actionable_remediation() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    cfg.raw["assay_mapping"]["cross_file_match"]["mode"] = "exact"
    addon = AddonModel(
        assays=[AssayModel(key="assay:1", protocol_type="CHEM", xml_name="IA")],
        analytes=[],
        units=[],
    )

    issues = LinkResolver(cfg).validate_cross_file_linkage(addon)

    assert len(issues) == 1
    assert issues[0].code == "assay-cross-file-mismatch"
    assert issues[0].severity == IssueSeverity.ERROR
    assert "Set XML assay name equal to Type" in str(issues[0].details.get("recommended_action", ""))


def test_link_resolver_alias_map_mode_accepts_alias_equivalence() -> None:
    cfg = load_mapping_config("config/mapping.v1.yaml")
    cfg.raw["assay_mapping"]["cross_file_match"] = {
        "mode": "alias_map",
        "alias_map": {
            "CHEM": "chemistry",
            "Chem": "chemistry",
        },
    }
    addon = AddonModel(
        assays=[AssayModel(key="assay:1", protocol_type="CHEM", xml_name="Chem")],
        analytes=[],
        units=[],
    )

    issues = LinkResolver(cfg).validate_cross_file_linkage(addon)

    assert issues == []


def test_schema_validator_import_does_not_raise_circular_import() -> None:
    import importlib
    import sys

    for module_name in (
        "addon_generator.mapping",
        "addon_generator.mapping.config_loader",
        "addon_generator.mapping.field_path",
        "addon_generator.config.schema_validator",
    ):
        sys.modules.pop(module_name, None)

    module = importlib.import_module("addon_generator.config.schema_validator")

    assert hasattr(module, "MappingConfigError")

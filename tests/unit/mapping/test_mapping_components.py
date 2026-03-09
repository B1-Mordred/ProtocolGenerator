import pytest

from addon_generator.mapping.config_loader import MappingConfigError, validate_mapping_config
from addon_generator.mapping.field_path import get_field_value, parse_field_path
from addon_generator.mapping.link_resolver import (
    assign_ids,
    resolve_analyte_projection,
    resolve_assay_projection,
    resolve_method_projection,
    validate_cross_file_linkage,
)
from addon_generator.mapping.normalizers import case_fold, collapse_whitespace, normalize_for_matching, trim


@pytest.fixture
def base_raw_config():
    return {
        "version": "v1",
        "defaults": {"matching_mode": "normalized"},
        "id_strategies": {"method": "sequential"},
        "projections": {
            "method": {"mode": "exact", "source_path": "source.name", "target_path": "target.name"},
            "assay": {"mode": "normalized", "source_path": "source.name", "target_path": "target.name"},
            "analyte": {
                "mode": "explicit_key",
                "source_path": "source.name",
                "target_path": "target.name",
                "explicit_key_path": "source.key",
            },
        },
    }


def test_parse_and_get_field_value():
    payload = {"a": {"b": [{"c": "ok"}]}}
    assert len(parse_field_path("a.b[0].c")) == 4
    assert get_field_value(payload, "a.b[0].c") == "ok"
    assert get_field_value(payload, "a.b[1].c", default="missing") == "missing"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  A   B  ", "a b"),
        ("TeSt", "test"),
    ],
)
def test_normalizers(raw, expected):
    assert normalize_for_matching(raw) == expected
    assert trim(" a ") == "a"
    assert collapse_whitespace("a   b") == "a b"
    assert case_fold("Ä") == "ä"


def test_config_validation_rejects_unknown_mode(base_raw_config):
    base_raw_config["projections"]["method"]["mode"] = "weird"
    with pytest.raises(MappingConfigError, match="Unknown mode"):
        validate_mapping_config(base_raw_config)


def test_config_validation_rejects_bad_field_path(base_raw_config):
    base_raw_config["projections"]["method"]["source_path"] = " bad.path"
    with pytest.raises(MappingConfigError, match="Invalid field path"):
        validate_mapping_config(base_raw_config)


def test_config_validation_rejects_alias_contradiction(base_raw_config):
    base_raw_config["projections"]["assay"] = {
        "mode": "alias_map",
        "source_path": "source.name",
        "target_path": "target.name",
        "alias_map": {"CBC": "Complete Blood Count", "cbc": "Cell Blood Count"},
    }
    with pytest.raises(MappingConfigError, match="Alias contradiction"):
        validate_mapping_config(base_raw_config)


def test_matching_modes_and_explicit_key_resolution(base_raw_config):
    cfg = validate_mapping_config(base_raw_config)

    method = {"source": {"name": "Method-A"}}
    method_candidates = [{"target": {"name": "Method-A"}}, {"target": {"name": "Method-B"}}]
    assert resolve_method_projection(method, method_candidates, cfg.method) == method_candidates[0]

    assay_source = {"source": {"name": "  cbc "}}
    alias_cfg_raw = base_raw_config.copy()
    alias_cfg_raw["projections"] = dict(base_raw_config["projections"])
    alias_cfg_raw["projections"]["assay"] = {
        "mode": "alias_map",
        "source_path": "source.name",
        "target_path": "target.name",
        "alias_map": {"CBC": "Complete Blood Count"},
    }
    alias_cfg = validate_mapping_config(alias_cfg_raw)
    assay_candidates = [{"target": {"name": "Complete Blood Count"}}]
    assert resolve_assay_projection(assay_source, assay_candidates, alias_cfg.assay) == assay_candidates[0]

    analyte_source = {"source": {"name": "NA", "key": "K-1"}}
    analyte_candidates = [{"source": {"key": "K-1"}}, {"source": {"key": "K-2"}}]
    assert resolve_analyte_projection(analyte_source, analyte_candidates, cfg.analyte) == analyte_candidates[0]


def test_assign_ids_and_cross_file_validation(base_raw_config):
    cfg = validate_mapping_config(base_raw_config)

    rows = [{"name": "a"}, {"name": "b"}]
    assert [r["id"] for r in assign_ids(rows)] == [1, 2]

    keyed_rows = [{"source": {"key": "a"}}, {"source": {"key": "a"}}, {"source": {"key": "b"}}]
    assign_ids(keyed_rows, strategy="explicit_key", explicit_key_field="source.key")
    assert [r["id"] for r in keyed_rows] == [1, 1, 2]

    methods = [{"source": {"name": "A"}}]
    assays = [{"source": {"name": "A"}}]
    analytes = [{"source": {"name": "A", "key": "X"}}]
    issues = validate_cross_file_linkage(
        methods=methods,
        assays=assays,
        analytes=analytes,
        method_projection=cfg.method,
        assay_projection=cfg.assay,
        analyte_projection=cfg.analyte,
    )
    assert len(issues) == 3

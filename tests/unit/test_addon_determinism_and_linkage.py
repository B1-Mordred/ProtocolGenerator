from __future__ import annotations

import pytest

from addon_generator.domain.ids import DeterministicIdAssigner, make_stable_key
from addon_generator.domain.models import AddonModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.mapping.config_loader import validate_mapping_config
from addon_generator.mapping.field_path import get_field_value, parse_field_path
from addon_generator.mapping.link_resolver import assign_ids, resolve_assay_projection, validate_cross_file_linkage
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain_context


def _mapping_config(mode: str = "normalized") -> dict[str, object]:
    return {
        "version": "v1",
        "defaults": {"matching_mode": mode},
        "id_strategies": {"method": "sequential"},
        "projections": {
            "method": {"mode": mode, "source_path": "source.name", "target_path": "target.name"},
            "assay": {"mode": mode, "source_path": "source.name", "target_path": "target.name"},
            "analyte": {
                "mode": "explicit_key",
                "source_path": "source.name",
                "target_path": "target.name",
                "explicit_key_path": "source.key",
            },
        },
    }


def test_field_path_resolution_handles_nested_tokens() -> None:
    payload = {"items": [{"result": {"value": "ok"}}]}

    tokens = parse_field_path("items[0].result.value")

    assert [token.key if token.key is not None else token.index for token in tokens] == ["items", 0, "result", "value"]
    assert get_field_value(payload, "items[0].result.value") == "ok"
    assert get_field_value(payload, "items[0].result.missing", default="fallback") == "fallback"


def test_matching_modes_alias_and_explicit_key_mapping() -> None:
    exact_cfg = validate_mapping_config(_mapping_config(mode="exact"))
    normalized_cfg = validate_mapping_config(_mapping_config(mode="normalized"))

    source = {"source": {"name": "  cBc  "}}
    candidate = {"target": {"name": "CBC"}}
    assert resolve_assay_projection(source, [candidate], exact_cfg.assay) is None
    assert resolve_assay_projection(source, [candidate], normalized_cfg.assay) == candidate

    alias_cfg_raw = _mapping_config()
    alias_cfg_raw["projections"]["assay"] = {
        "mode": "alias_map",
        "source_path": "source.name",
        "target_path": "target.name",
        "alias_map": {"CBC": "Complete Blood Count"},
    }
    alias_cfg = validate_mapping_config(alias_cfg_raw)
    aliased_source = {"source": {"name": "cbc"}}
    aliased_candidate = {"target": {"name": "Complete Blood Count"}}
    assert resolve_assay_projection(aliased_source, [aliased_candidate], alias_cfg.assay) == aliased_candidate


def test_deterministic_ids_and_domain_cross_file_validators() -> None:
    assigner = DeterministicIdAssigner()
    first = assigner.assign("assay", "Chemistry")
    second = assigner.assign("assay", "Chemistry")
    third = assigner.assign("assay", "Hematology")

    assert first == second
    assert first[1] == 1 and third[1] == 2
    assert first[0] == make_stable_key("assay", "Chemistry", 1)

    rows = [{"source": {"key": "a"}}, {"source": {"key": "a"}}, {"source": {"key": "b"}}]
    assign_ids(rows, strategy="explicit_key", explicit_key_field="source.key")
    assert [row["id"] for row in rows] == [1, 1, 2]

    context = ProtocolContextModel(
        addon=AddonModel(
            methods=[
                MethodModel(key="method:1", method_id=1, display_name="Chemistry"),
                MethodModel(key="method:2", method_id=1, display_name="chemistry"),
            ],
            assays=[AssayModel(key="assay:1", assay_id=2, name="Panel")],
        )
    )
    domain_result = validate_domain_context(context)
    assert domain_result.is_valid is False
    assert {issue.code for issue in domain_result.issues.issues} >= {"duplicate-id", "non-unique-cross-match-field"}

    cross_file_result = validate_cross_file_consistency(
        context,
        {"MethodInformation": {"Id": "999", "Version": ""}, "AssayInformation": [{"Type": "Missing"}]},
    )
    assert cross_file_result.is_valid is False
    assert {issue.code for issue in cross_file_result.issues.issues} >= {
        "method-linkage-mismatch",
        "method-linkage-version-missing",
        "broken-assay-reference",
    }


def test_mapping_level_cross_file_linkage_reports_unmatched_entities() -> None:
    cfg = validate_mapping_config(_mapping_config(mode="exact"))

    issues = validate_cross_file_linkage(
        methods=[{"source": {"name": "MethodA"}}],
        assays=[{"source": {"name": "AssayA"}}],
        analytes=[{"source": {"name": "AnalyteA", "key": "A-1"}}],
        method_projection=cfg.method,
        assay_projection=cfg.assay,
        analyte_projection=cfg.analyte,
    )

    assert len(issues) == 3
    assert {issue.entity for issue in issues} == {"method", "assay", "analyte"}


@pytest.mark.parametrize("bad_path", ["", " a.b", "a[xyz]"])
def test_field_path_rejects_invalid_syntax(bad_path: str) -> None:
    with pytest.raises(ValueError):
        parse_field_path(bad_path)

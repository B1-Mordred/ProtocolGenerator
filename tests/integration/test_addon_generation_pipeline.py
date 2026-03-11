import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from addon_generator.__about__ import about_payload
from addon_generator.services.generation_service import GenerationService
from fixture_loader import fixture_metadata, materialize_workbook_fixture


GOLDEN_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "addon-generation"


def _canonical_json_string(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def _canonical_xml_string(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    return ET.tostring(root, encoding="unicode")


def test_generation_pipeline_produces_linked_outputs() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    result = service.generate_all(addon)

    assert result.protocol_json["MethodInformation"]["Id"] == "M-1"
    assert result.protocol_json["MethodInformation"]["Version"] == "1.0"
    assert result.protocol_json["LoadingWorkflowSteps"]
    assert result.protocol_json["ProcessingWorkflowSteps"]
    assert "<MethodId>M-1</MethodId>" in result.analytes_xml_string
    assert result.issues == []


def test_excel_import_pipeline_flow_with_sheeted_layout(tmp_path) -> None:
    path = materialize_workbook_fixture("minimal-valid", tmp_path)

    service = GenerationService()
    addon = service.import_from_excel(str(path))
    result = service.generate_all(addon)

    assert addon.method is not None and addon.method.method_id == "FX-MIN"
    assert addon.assays[0].protocol_type == "CHEM"
    assert addon.analytes[0].assay_key == "assay:min"
    assert addon.units[0].analyte_key == "analyte:min"
    assert result.protocol_json["MethodInformation"]["Id"] == "FX-MIN"
    assert result.issues == []


def test_generation_pipeline_reproducible_merged_output() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-R",
            "method_version": "3.0",
            "MethodInformation": {"DisplayName": "GUI Preferred"},
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    fragments = {"MethodInformation": {"DisplayName": "Imported", "SubTitle": "Imported Sub"}}

    run1 = service.generate_protocol_json(addon, fragments)
    run2 = service.generate_protocol_json(addon, fragments)

    assert run1.payload == run2.payload
    assert run1.merge_report == run2.merge_report
    assert run1.payload["MethodInformation"]["DisplayName"] == "GUI Preferred"
    assert run1.payload["MethodInformation"]["SubTitle"] == "Imported Sub"


def test_generation_pipeline_applies_field_mapping_template_to_exported_artifacts() -> None:
    service = GenerationService()
    payload = {
        "method_id": "M-MAP",
        "method_version": "1.0",
        "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
        "analytes": [
            {"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"},
            {"key": "analyte:2", "name": "TSH", "assay_key": "assay:1"},
        ],
        "units": [
            {"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"},
            {"key": "unit:2", "name": "uIU/mL", "analyte_key": "analyte:2"},
        ],
    }
    addon = service.import_from_gui_payload(payload)
    # Rebuild DTO bundle from addon to mirror export-time execution context.
    dto_bundle = service._dto_bundle_from_addon(addon)
    if dto_bundle.method:
        dto_bundle.method.product_number = "PX-9"
        dto_bundle.method.product_name = "Mapped Kit"

    result = service.generate_all(
        addon,
        dto_bundle=dto_bundle,
        field_mapping_settings={
            "active_template": "Default",
            "templates": {
                "Default": [
                    {"enabled": True, "target": "ProtocolFile.json:MethodInformation.Id", "expression": "default:Mapped-Method"},
                    {"enabled": True, "target": "Analytes.xml:Assays[].Analytes[].Analyte.Name", "expression": "concat(input:analytes[].name, default:-M)"},
                ]
            },
        },
    )

    assert result.protocol_json["MethodInformation"]["Id"] == "Mapped-Method"
    names = [node.text for node in ET.fromstring(result.analytes_xml_string).findall("./Assays/Assay/Analytes/Analyte/Name")]
    assert names == ["GLU-M", "TSH-M"]
    assert len(result.field_mapping_report.get("applied", [])) == 2



def test_generation_pipeline_reports_ambiguity_errors() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-ERR",
            "method_version": "1.0",
            "assays": [
                {"key": "assay:1", "protocol_type": "A", "xml_name": "A"},
                {"key": "assay:2", "protocol_type": "B", "xml_name": "B"},
            ],
            "analytes": [
                {"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"},
                {"key": "analyte:2", "name": "glu", "assay_key": "assay:2"},
            ],
            "units": [
                {"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"},
                {"key": "unit:2", "name": "mg/dL", "analyte_key": "analyte:2"},
            ],
        }
    )

    result = service.generate_all(addon)

    assert any(issue.code == "ambiguous-analyte-assay-linkage" for issue in result.issues)


def test_generation_pipeline_multi_assay_processing_groups() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-2A",
            "method_version": "2.0",
            "assays": [
                {"key": "assay:chem", "protocol_type": "CHEM", "xml_name": "CHEM", "protocol_display_name": "Chem"},
                {"key": "assay:immuno", "protocol_type": "IMM", "xml_name": "IMM", "protocol_display_name": "Immuno"},
            ],
            "analytes": [
                {"key": "a1", "name": "GLU", "assay_key": "assay:chem"},
                {"key": "a2", "name": "TSH", "assay_key": "assay:immuno"},
            ],
            "units": [
                {"key": "u1", "name": "mg/dL", "analyte_key": "a1"},
                {"key": "u2", "name": "uIU/mL", "analyte_key": "a2"},
            ],
        }
    )

    result = service.generate_all(addon)

    assert result.protocol_json["MethodInformation"]["SamplesLayoutType"] == "SAMPLES_LAYOUT_SPLIT"
    assert len(result.protocol_json["ProcessingWorkflowSteps"]) == 2
    assert {step["GroupDisplayName"] for step in result.protocol_json["ProcessingWorkflowSteps"]} == {"Chem", "Immuno"}


def test_package_builder_emits_deterministic_layout(tmp_path) -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-PKG",
            "method_version": "1.2",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    first = service.build_package(addon, tmp_path)
    second = service.build_package(addon, tmp_path, collision_policy="increment")

    assert first.package_name == "M-PKG-1.2"
    assert second.package_name == "M-PKG-1.2-2"

    first_files = sorted(path.name for path in first.package_root.iterdir())
    second_files = sorted(path.name for path in second.package_root.iterdir())
    assert first_files == ["Analytes.xml", "ProtocolFile.json", "package-metadata.json"]
    assert second_files == first_files

    assert first.artifacts["ProtocolFile.json"].read_text(encoding="utf-8") == second.artifacts["ProtocolFile.json"].read_text(encoding="utf-8")
    assert first.artifacts["Analytes.xml"].read_text(encoding="utf-8") == second.artifacts["Analytes.xml"].read_text(encoding="utf-8")

    metadata = json.loads(first.artifacts["package-metadata.json"].read_text(encoding="utf-8"))
    assert metadata["app"] == about_payload()


def test_package_builder_overwrite_and_collision_policy(tmp_path) -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-OW",
            "method_version": "9",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    first = service.build_package(addon, tmp_path)
    (first.package_root / "stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(FileExistsError):
        service.build_package(addon, tmp_path)

    overwritten = service.build_package(addon, tmp_path, overwrite=True)
    assert overwritten.package_root == first.package_root
    assert (overwritten.package_root / "stale.txt").exists() is False


def test_package_builder_rejects_unknown_collision_policy(tmp_path) -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M", "method_version": "1", "assays": [], "analytes": [], "units": []})

    with pytest.raises(ValueError):
        service.build_package(addon, tmp_path, collision_policy="rename")


@pytest.mark.parametrize(
    ("scenario", "payload"),
    [
        (
            "basic-gui",
            {
                "method_id": "M-1",
                "method_version": "1.0",
                "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
                "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
                "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
            },
        ),
        (
            "multi-assay-groups",
            {
                "method_id": "M-2A",
                "method_version": "2.0",
                "assays": [
                    {"key": "assay:chem", "protocol_type": "CHEM", "xml_name": "CHEM", "protocol_display_name": "Chem"},
                    {"key": "assay:immuno", "protocol_type": "IMM", "xml_name": "IMM", "protocol_display_name": "Immuno"},
                ],
                "analytes": [
                    {"key": "a1", "name": "GLU", "assay_key": "assay:chem"},
                    {"key": "a2", "name": "TSH", "assay_key": "assay:immuno"},
                ],
                "units": [
                    {"key": "u1", "name": "mg/dL", "analyte_key": "a1"},
                    {"key": "u2", "name": "uIU/mL", "analyte_key": "a2"},
                ],
            },
        ),
        (
            "gui-fragments-deterministic",
            {
                "method_id": "M-R",
                "method_version": "3.0",
                "MethodInformation": {"DisplayName": "GUI Preferred"},
                "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
                "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
                "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
            },
        ),
    ],
)
def test_generation_pipeline_matches_golden_artifacts(scenario: str, payload: dict) -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(payload)
    result = service.generate_all(addon)

    expected_json = (GOLDEN_ROOT / scenario / "ProtocolFile.json").read_text(encoding="utf-8")
    expected_xml = (GOLDEN_ROOT / scenario / "Analytes.xml").read_text(encoding="utf-8")

    assert _canonical_json_string(result.protocol_json) == expected_json
    assert _canonical_xml_string(result.analytes_xml_string) == _canonical_xml_string(expected_xml)


@pytest.mark.parametrize("scenario", ["single-assay", "multi-assay", "multi-analyte"])
def test_excel_fixture_scenarios_generate_without_errors(tmp_path, scenario: str) -> None:
    service = GenerationService()
    workbook_path = materialize_workbook_fixture(scenario, tmp_path)

    addon = service.import_from_excel(str(workbook_path))
    result = service.generate_all(addon)

    assert result.issues == []


def test_excel_fixture_invalid_scenarios_surface_expected_errors(tmp_path) -> None:
    service = GenerationService()

    for scenario in ("invalid-cross-file-mapping", "invalid-units"):
        workbook_path = materialize_workbook_fixture(scenario, tmp_path)
        addon = service.import_from_excel(str(workbook_path))
        result = service.generate_all(addon)
        expected = fixture_metadata(scenario)["expected"]["error_codes"]
        actual_codes = [issue.code for issue in result.issues]

        assert set(expected).issubset(set(actual_codes))
        expected_positions = [actual_codes.index(code) for code in expected]
        assert expected_positions == sorted(expected_positions)


def test_generation_pipeline_orders_domain_issues_before_projection_fallout() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-ORDER",
            "method_version": "",
            "assays": [
                {"key": "assay:a", "protocol_type": "A", "xml_name": "A"},
                {"key": "assay:b", "protocol_type": "B", "xml_name": "B"},
            ],
            "analytes": [
                {"key": "analyte:1", "name": "GLU", "assay_key": "assay:a"},
                {"key": "analyte:2", "name": "glu", "assay_key": "assay:b"},
            ],
            "units": [
                {"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"},
                {"key": "unit:2", "name": "mg/dL", "analyte_key": "analyte:2"},
            ],
        }
    )
    addon.source_metadata = {}

    result = service.generate_all(addon)
    issue_codes = [issue.code for issue in result.issues]

    assert "missing-method-version" in issue_codes
    assert "missing-method-identity" in issue_codes
    assert issue_codes.index("missing-method-version") < issue_codes.index("missing-method-identity")


@pytest.mark.parametrize("scenario", ["production-shape", "header-offset-and-checklist"])
def test_workbook_template_scenarios_match_golden_outputs(tmp_path, scenario: str) -> None:
    service = GenerationService()
    workbook_path = materialize_workbook_fixture(scenario, tmp_path)

    addon = service.import_from_excel(str(workbook_path))
    result = service.generate_all(addon)

    expected_json = (GOLDEN_ROOT / scenario / "ProtocolFile.json").read_text(encoding="utf-8")
    expected_xml = (GOLDEN_ROOT / scenario / "Analytes.xml").read_text(encoding="utf-8")

    assert _canonical_json_string(result.protocol_json) == expected_json
    assert _canonical_xml_string(result.analytes_xml_string) == _canonical_xml_string(expected_xml)

def test_generation_pipeline_deterministic_fragment_registry_merge_ordering() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-FRAG",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )
    addon.source_metadata = {"assay_family": "chem", "reagent": "r1", "dilution": "1:2"}
    addon.protocol_context.reagent_fragments = [
        {"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"StepName": "ZZZ"}]},
    ]
    addon.protocol_context.loading_fragments = [
        {"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"StepName": "AAA"}]},
    ]
    addon.protocol_context.dilution_fragments = [
        {"selector": {"assay_family": "chem", "dilution": "1:2"}, "payload": [{"GroupDisplayName": "B"}]},
    ]
    addon.protocol_context.processing_fragments = [
        {"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"GroupDisplayName": "A"}]},
    ]

    result1 = service.generate_protocol_json(addon).payload
    result2 = service.generate_protocol_json(addon).payload

    assert result1 == result2
    assert result1["LoadingWorkflowSteps"] == [{"StepName": "AAA"}, {"StepName": "ZZZ"}]
    assert result1["ProcessingWorkflowSteps"] == [{"GroupDisplayName": "A"}, {"GroupDisplayName": "B"}]

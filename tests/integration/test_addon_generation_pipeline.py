import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

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

    assert result.protocol_json["MethodInformation"]["SamplesLayoutType"] == "SAMPLES_LAYOUT_SEPARATE"
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
        expected = set(fixture_metadata(scenario)["expected"]["error_codes"])
        codes = {issue.code for issue in result.issues}
        assert expected.issubset(codes)

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

from addon_generator.input_models.dtos import AnalyteInputDTO, AssayInputDTO, InputDTOBundle, MethodInputDTO
from addon_generator.ui.services.field_mapping_execution import apply_field_mappings


def _bundle() -> InputDTOBundle:
    return InputDTOBundle(
        source_type="gui",
        method=MethodInputDTO(
            key="method:1",
            method_id="M-1",
            method_version="1.0",
            product_name="Kit-Z",
            product_number="P-42",
        ),
        assays=[AssayInputDTO(key="assay:1", protocol_type="A", xml_name="PS1")],
        analytes=[
            AnalyteInputDTO(key="analyte:1", name="GLU", assay_key="assay:1"),
            AnalyteInputDTO(key="analyte:2", name="TSH", assay_key="assay:1"),
        ],
    )


def test_apply_field_mappings_applies_active_template_to_protocol_and_xml() -> None:
    protocol = {
        "MethodInformation": {"Id": "M-1", "Version": "1.0"},
        "AssayInformation": [{"Analytes": [{"Name": "GLU"}, {"Name": "TSH"}]}],
    }
    analytes_xml = """<?xml version='1.0' encoding='utf-8'?><AddOn><Assays><Assay><Analytes><Analyte><Name>GLU</Name><AnalyteUnits><AnalyteUnit><Name>mg/dL</Name></AnalyteUnit></AnalyteUnits></Analyte><Analyte><Name>TSH</Name><AnalyteUnits><AnalyteUnit><Name>uIU/mL</Name></AnalyteUnit></AnalyteUnits></Analyte></Analytes></Assay></Assays></AddOn>"""
    settings = {
        "active_template": "Default",
        "templates": {
            "Default": [
                {"enabled": True, "target": "ProtocolFile.json:MethodInformation.Id", "expression": "input:method.kit_product_number"},
                {"enabled": True, "target": "ProtocolFile.json:AssayInformation[].Analytes[].Name", "expression": "input:analytes[].name"},
                {"enabled": True, "target": "Analytes.xml:Assays[].Analytes[].Analyte.Name", "expression": "concat(input:analytes[].name, default:-mapped)"},
            ]
        },
    }

    result = apply_field_mappings(protocol_json=protocol, analytes_xml=analytes_xml, dto_bundle=_bundle(), field_mapping_settings=settings)

    assert result.protocol_json["MethodInformation"]["Id"] == "P-42"
    assert [a["Name"] for a in result.protocol_json["AssayInformation"][0]["Analytes"]] == ["GLU", "TSH"]

    xml_names = [node.text for node in ET.fromstring(result.analytes_xml).findall("./Assays/Assay/Analytes/Analyte/Name")]
    assert xml_names == ["GLU-mapped", "TSH-mapped"]
    assert len(result.report["applied"]) == 3


def test_apply_field_mappings_uses_last_write_wins_and_reports_skips() -> None:
    protocol = {"MethodInformation": {"Id": "M-1", "Version": "1.0"}, "AssayInformation": []}
    analytes_xml = "<?xml version='1.0' encoding='utf-8'?><AddOn><Assays/></AddOn>"
    settings = {
        "active_template": "Default",
        "templates": {
            "Default": [
                {"enabled": True, "target": "ProtocolFile.json:MethodInformation.Id", "expression": "default:First"},
                {"enabled": True, "target": "ProtocolFile.json:MethodInformation.Id", "expression": "default:Last"},
                {"enabled": False, "target": "ProtocolFile.json:MethodInformation.Version", "expression": "default:2.0"},
            ]
        },
    }

    result = apply_field_mappings(protocol_json=protocol, analytes_xml=analytes_xml, dto_bundle=_bundle(), field_mapping_settings=settings)

    assert result.protocol_json["MethodInformation"]["Id"] == "Last"
    serialized = json.dumps(result.report)
    assert "last-write-wins" in serialized
    assert any(item["reason"] == "disabled" for item in result.report["skipped"])

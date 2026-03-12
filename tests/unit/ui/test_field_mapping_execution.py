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


def test_apply_field_mappings_enforces_exclusive_lock_on_owned_targets() -> None:
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

    assert result.protocol_json["MethodInformation"]["Id"] == "First"
    serialized = json.dumps(result.report)
    assert "target-owned-by-active-template" in serialized
    assert result.report["ignored"] == [
        {
            "row": 1,
            "target": "ProtocolFile.json:MethodInformation.Id",
            "reason": "target-owned-by-active-template",
            "owner_row": 0,
        }
    ]
    assert any(item["reason"] == "disabled" for item in result.report["skipped"])


def test_apply_field_mappings_keeps_last_write_wins_for_unlocked_targets() -> None:
    protocol = {"MethodInformation": {"Id": "M-1", "Version": "1.0"}, "AssayInformation": [{"Analytes": [{"Name": "A"}]}]}
    analytes_xml = "<?xml version='1.0' encoding='utf-8'?><AddOn><Assays><Assay><Analytes><Analyte><Name>A</Name></Analyte></Analytes></Assay></Assays></AddOn>"
    settings = {
        "active_template": "Default",
        "templates": {
            "Default": [
                {"enabled": True, "target": "ProtocolFile.json:AssayInformation[].Analytes[].Name", "expression": "default:First"},
                {"enabled": True, "target": "ProtocolFile.json:AssayInformation[].Analytes[].Name", "expression": "default:Last"},
            ]
        },
    }

    result = apply_field_mappings(protocol_json=protocol, analytes_xml=analytes_xml, dto_bundle=_bundle(), field_mapping_settings=settings)

    assert result.protocol_json["AssayInformation"][0]["Analytes"][0]["Name"] == "Last"
    assert any("last-write-wins" in warning for warning in result.report["warnings"])


def test_apply_field_mappings_supports_new_locked_targets_and_ignores_conflicts() -> None:
    protocol = {
        "MethodInformation": {"Id": "M-1", "Version": "1.0"},
        "AssayInformation": [{"Type": "Legacy"}, {"Type": "Legacy-2"}],
    }
    analytes_xml = "<?xml version='1.0' encoding='utf-8'?><AddOn><MethodId>ORIG</MethodId><MethodVersion>0</MethodVersion><Assays><Assay><Name>A1</Name></Assay><Assay><Name>A2</Name></Assay></Assays></AddOn>"
    settings = {
        "active_template": "Default",
        "templates": {
            "Default": [
                {"enabled": True, "target": "Analytes.xml:MethodId", "expression": "default:XML-ID-1"},
                {"enabled": True, "target": "Analytes.xml:MethodId", "expression": "default:XML-ID-2"},
                {"enabled": True, "target": "Analytes.xml:MethodVersion", "expression": "default:7"},
                {"enabled": True, "target": "Analytes.xml:Assays[].Assay.Name", "expression": "default:Panel"},
                {"enabled": True, "target": "Analytes.xml:Assays[].Assay.AssayInformationType", "expression": "default:Chem"},
                {"enabled": True, "target": "ProtocolFile.json:AssayInformation[].Type", "expression": "default:Clinical"},
            ]
        },
    }

    result = apply_field_mappings(protocol_json=protocol, analytes_xml=analytes_xml, dto_bundle=_bundle(), field_mapping_settings=settings)
    root = ET.fromstring(result.analytes_xml)

    assert root.findtext("./MethodId") == "XML-ID-1"
    assert root.findtext("./MethodVersion") == "7"
    assert [node.text for node in root.findall("./Assays/Assay/Name")] == ["Panel", "Panel"]
    assert [node.text for node in root.findall("./Assays/Assay/AssayInformationType")] == ["Chem", "Chem"]
    assert [item["Type"] for item in result.protocol_json["AssayInformation"]] == ["Clinical", "Clinical"]
    assert result.report["ignored"][0]["target"] == "Analytes.xml:MethodId"

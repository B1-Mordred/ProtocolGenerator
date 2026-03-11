from __future__ import annotations

import xml.etree.ElementTree as ET

from addon_generator.domain.ids import assign_deterministic_ids
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.services.generation_service import GenerationService


def test_generate_analytes_xml_matches_expected_shape() -> None:
    addon = AddonModel(
        method=MethodModel(key="method:k", method_id="M-100", method_version="2.0", product_number="PN-100"),
        assays=[AssayModel(key="assay:chem", protocol_type="CHEM", xml_name="CHEM", metadata={"assay_abbreviation": "CHEM"})],
        analytes=[AnalyteModel(key="analyte:glu", name="Glucose", assay_key="assay:chem", assay_information_type="CHEM")],
        units=[AnalyteUnitModel(key="unit:mgdl", name="mg/dL", analyte_key="analyte:glu")],
    )
    assign_deterministic_ids(addon)

    result = generate_analytes_addon_xml(addon, xsd_path="AddOn.xsd")
    root = ET.fromstring(result.xml_content)

    assert root.findtext("Id") == "0"
    assert root.findtext("MethodId") == "PN-100"
    assert root.findtext("MethodVersion") == ""
    assert root.findtext("./Assays/Assay/Id") == "0"
    assert root.findtext("./Assays/Assay/Name") == "CHEM"
    assert root.findtext("./Assays/Assay/AddOnRef") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/Id") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/AssayRef") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit/AnalyteRef") == "0"
    assert result.issues.has_errors() is False




def test_generate_analytes_xml_skips_assays_without_abbreviation() -> None:
    addon = AddonModel(
        method=MethodModel(key="method:k", method_id="M-100", method_version="2.0", product_number="PN-100"),
        assays=[
            AssayModel(key="assay:chem", protocol_type="CHEM", xml_name="CHEM", metadata={"assay_abbreviation": "CHEM"}),
            AssayModel(key="assay:immuno", protocol_type="IMM", xml_name="IMM", metadata={"assay_abbreviation": ""}),
        ],
        analytes=[
            AnalyteModel(key="analyte:glu", name="Glucose", assay_key="assay:chem", assay_information_type="CHEM"),
            AnalyteModel(key="analyte:tsh", name="TSH", assay_key="assay:immuno", assay_information_type="IMM"),
        ],
        units=[
            AnalyteUnitModel(key="unit:mgdl", name="mg/dL", analyte_key="analyte:glu"),
            AnalyteUnitModel(key="unit:uiu", name="uIU/mL", analyte_key="analyte:tsh"),
        ],
    )
    assign_deterministic_ids(addon)

    result = generate_analytes_addon_xml(addon, xsd_path="AddOn.xsd")
    root = ET.fromstring(result.xml_content)

    assay_names = [assay.findtext("Name") for assay in root.findall("./Assays/Assay")]
    analyte_names = [analyte.findtext("Name") for analyte in root.findall("./Assays/Assay/Analytes/Analyte")]

    assert assay_names == ["CHEM"]
    assert analyte_names == ["Glucose"]


def test_generate_analytes_xml_forces_zero_ids_and_refs_for_preview_and_export() -> None:
    addon = AddonModel(
        addon_id=99,
        method=MethodModel(key="method:k", method_id="M-100", method_version="2.0", product_number="PN-100"),
        assays=[
            AssayModel(
                key="assay:chem",
                protocol_type="CHEM",
                xml_name="CHEM",
                xml_id=7,
                addon_ref=99,
                metadata={"assay_abbreviation": "CHEM"},
            )
        ],
        analytes=[AnalyteModel(key="analyte:glu", name="Glucose", assay_key="assay:chem", xml_id=8, assay_ref=7)],
        units=[AnalyteUnitModel(key="unit:mgdl", name="mg/dL", analyte_key="analyte:glu", xml_id=9, analyte_ref=8)],
    )

    result = generate_analytes_addon_xml(addon, xsd_path="AddOn.xsd")
    root = ET.fromstring(result.xml_content)

    assert set(root.findall('.//Id'))
    assert all(node.text == "0" for node in root.findall('.//Id'))
    assert all(node.text == "0" for node in root.findall('.//AddOnRef'))
    assert all(node.text == "0" for node in root.findall('.//AnalyteRef'))

def test_default_ruleset_generation_normalizes_manual_analyte_assay_references_with_units() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-200",
            "method_version": "1.0",
            "assays": [
                {
                    "key": "assay:chem",
                    "protocol_type": "CHEM",
                    "protocol_display_name": "Chemistry",
                    "xml_name": "Chemistry",
                    "assay_abbreviation": "CHEM",
                }
            ],
            "analytes": [
                {"key": "analyte:glu", "name": "Glucose", "assay_key": " chemistry ", "unit_names": "mg/dL"},
                {"key": "analyte:lac", "name": "Lactate", "assay_key": "CHEMISTRY", "unit_names": "mmol/L"},
                {"key": "analyte:k", "name": "Potassium", "assay_key": "  REFLEX Panel  ", "unit_names": "mmol/L"},
                {"key": "analyte:na", "name": "Sodium", "assay_key": "  REFLEX Panel  ", "unit_names": "mEq/L"},
            ],
        }
    )

    result = service.generate_all(addon)
    root = ET.fromstring(result.analytes_xml_string)

    assays = root.findall("./Assays/Assay")
    grouped_analytes = {
        assay.findtext("Name"): [item.findtext("Name") for item in assay.findall("./Analytes/Analyte")]
        for assay in assays
    }
    assert grouped_analytes == {"Chemistry": ["Glucose", "Lactate"]}

    linked_units = {
        analyte.findtext("Name"): [unit.findtext("Name") for unit in analyte.findall("./AnalyteUnits/AnalyteUnit")]
        for assay in assays
        for analyte in assay.findall("./Analytes/Analyte")
    }
    assert linked_units == {
        "Glucose": ["mg/dL"],
        "Lactate": ["mmol/L"],
    }

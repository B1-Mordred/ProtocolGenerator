from __future__ import annotations

import xml.etree.ElementTree as ET

from addon_generator.domain.ids import assign_deterministic_ids
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.services.generation_service import GenerationService


def test_generate_analytes_xml_matches_expected_shape() -> None:
    addon = AddonModel(
        method=MethodModel(key="method:k", method_id="M-100", method_version="2.0", product_number="PN-100"),
        assays=[AssayModel(key="assay:chem", protocol_type="CHEM", xml_name="CHEM")],
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
    assert grouped_analytes == {"Chemistry": ["Glucose", "Lactate"], "REFLEX Panel": ["Potassium", "Sodium"]}

    linked_units = {
        analyte.findtext("Name"): [unit.findtext("Name") for unit in analyte.findall("./AnalyteUnits/AnalyteUnit")]
        for assay in assays
        for analyte in assay.findall("./Analytes/Analyte")
    }
    assert linked_units == {
        "Glucose": ["mg/dL"],
        "Lactate": ["mmol/L"],
        "Potassium": ["mmol/L"],
        "Sodium": ["mEq/L"],
    }

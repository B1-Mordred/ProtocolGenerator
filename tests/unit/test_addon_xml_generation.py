from __future__ import annotations

import xml.etree.ElementTree as ET

from addon_generator.domain.ids import assign_deterministic_ids
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml


def test_generate_analytes_xml_matches_expected_shape() -> None:
    addon = AddonModel(
        method=MethodModel(key="method:k", method_id="M-100", method_version="2.0"),
        assays=[AssayModel(key="assay:chem", protocol_type="CHEM", xml_name="CHEM")],
        analytes=[AnalyteModel(key="analyte:glu", name="Glucose", assay_key="assay:chem", assay_information_type="CHEM")],
        units=[AnalyteUnitModel(key="unit:mgdl", name="mg/dL", analyte_key="analyte:glu")],
    )
    assign_deterministic_ids(addon)

    result = generate_analytes_addon_xml(addon, xsd_path="AddOn.xsd")
    root = ET.fromstring(result.xml_content)

    assert root.findtext("Id") == "0"
    assert root.findtext("MethodId") == "M-100"
    assert root.findtext("MethodVersion") == "2.0"
    assert root.findtext("./Assays/Assay/Id") == "0"
    assert root.findtext("./Assays/Assay/Name") == "CHEM"
    assert root.findtext("./Assays/Assay/AddOnRef") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/Id") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/AssayRef") == "0"
    assert root.findtext("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit/AnalyteRef") == "0"
    assert result.issues.has_errors() is False

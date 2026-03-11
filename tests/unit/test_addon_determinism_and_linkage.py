from xml.etree import ElementTree as ET

from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.generators.protocol_generator import generate_protocol_json


def test_method_linkage_and_ids_are_deterministic() -> None:
    addon = AddonModel(
        method=MethodModel(key="method", method_id="METHOD-X", method_version="3.1", product_number="PN-XYZ"),
        assays=[AssayModel(key="assay:z", protocol_type="Z", xml_name="Z"), AssayModel(key="assay:a", protocol_type="A", xml_name="A")],
        analytes=[AnalyteModel(key="n2", name="N2", assay_key="assay:z"), AnalyteModel(key="n1", name="N1", assay_key="assay:a")],
        units=[AnalyteUnitModel(key="u2", name="u2", analyte_key="n2"), AnalyteUnitModel(key="u1", name="u1", analyte_key="n1")],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)

    protocol = generate_protocol_json(addon, resolver).payload
    xml = generate_analytes_addon_xml(addon, xsd_path="AddOn.xsd").xml_content
    root = ET.fromstring(xml)

    assert root.findtext("MethodId") == "PN-XYZ"
    assert root.findtext("MethodVersion") == ""
    assert [a.xml_id for a in sorted(addon.assays, key=lambda x: x.key)] == [0, 1]



def test_domain_validation_rejects_ambiguous_analyte_assay_linkage() -> None:
    from addon_generator.validation.domain_validator import validate_domain

    addon = AddonModel(
        method=MethodModel(key="method", method_id="METHOD-X", method_version="3.1", product_number="PN-XYZ"),
        assays=[
            AssayModel(key="assay:a", protocol_type="A", xml_name="A"),
            AssayModel(key="assay:b", protocol_type="B", xml_name="B"),
        ],
        analytes=[
            AnalyteModel(key="n1", name="GLU", assay_key="assay:a"),
            AnalyteModel(key="n2", name=" glu ", assay_key="assay:b"),
        ],
        units=[
            AnalyteUnitModel(key="u1", name="mg/dL", analyte_key="n1"),
            AnalyteUnitModel(key="u2", name="mg/dL", analyte_key="n2"),
        ],
    )

    result = validate_domain(addon)

    assert result.is_valid is False
    assert any(issue.code == "ambiguous-analyte-assay-linkage" for issue in result.issues.issues)


def test_excel_normalization_expands_multi_unit_cells() -> None:
    from addon_generator.importers.excel_importer import ExcelImporter

    rows = [
        {
            "MethodId": "M-1",
            "MethodVersion": "1.0",
            "AssayKey": "assay:1",
            "ProtocolType": "A",
            "AnalyteKey": "analyte:1",
            "AnalyteName": "GLU",
            "UnitKey": "unit:mg",
            "UnitName": "mg/dl; mmol/L",
        }
    ]

    payload = ExcelImporter().normalize_workbook_rows(rows)

    assert len(payload["units"]) == 2
    assert payload["units"][0]["name"] == "mg/dL"
    assert payload["units"][1]["name"] == "mmol/L"

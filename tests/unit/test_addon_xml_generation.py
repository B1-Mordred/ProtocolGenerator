from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from addon_generator.domain.issues import IssueSeverity
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml


def test_generate_analytes_xml_is_deterministic_and_contains_required_refs(tmp_path: Path) -> None:
    addon = AddonModel(
        addon_id=999,
        assays=[
            AssayModel(
                key="assay:b",
                assay_id=20,
                analytes=[
                    AnalyteModel(
                        key="analyte:b",
                        analyte_id=7,
                        units=[
                            AnalyteUnitModel(key="unit:b", unit_id=4, symbol="mg/dL"),
                            AnalyteUnitModel(key="unit:a", unit_id=3, symbol="mmol/L"),
                        ],
                    )
                ],
            ),
            AssayModel(
                key="assay:a",
                assay_id=10,
                analytes=[AnalyteModel(key="analyte:a", analyte_id=2)],
            ),
        ],
    )

    result = generate_analytes_addon_xml(addon, xsd_path=tmp_path / "missing.AddOn.xsd")

    xml_root = ET.fromstring(result.xml_content)
    assay_refs = [node.text for node in xml_root.findall("./Assays/Assay/AssayRef")]
    assert assay_refs == ["10", "20"]

    analyte_node = xml_root.find("./Assays/Assay[2]/Analytes/Analyte")
    assert analyte_node is not None
    assert analyte_node.findtext("AddOnRef") == "999"
    assert analyte_node.findtext("AssayRef") == "20"
    assert analyte_node.findtext("AnalyteRef") == "7"

    unit_refs = [
        node.findtext("UnitRef")
        for node in xml_root.findall("./Assays/Assay[2]/Analytes/Analyte/AnalyteUnits/AnalyteUnit")
    ]
    assert unit_refs == ["3", "4"]
    assert result.issues.has_errors() is True


def test_generate_analytes_xml_writes_file_when_validation_reports_warning_only(
    tmp_path: Path, monkeypatch
) -> None:
    addon = AddonModel(addon_id=1, assays=[])
    output_file = tmp_path / "addon.xml"
    xsd_file = tmp_path / "AddOn.xsd"
    xsd_file.write_text("<xsd:schema xmlns:xsd='http://www.w3.org/2001/XMLSchema'/>", encoding="utf-8")

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001, A002
        if name == "lxml":
            raise ImportError("no lxml")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    result = generate_analytes_addon_xml(addon, xsd_path=xsd_file, output_path=output_file)

    assert result.output_path == output_file
    assert output_file.exists() is True
    assert any(issue.severity is IssueSeverity.WARNING for issue in result.issues.issues)
    assert result.issues.has_errors() is False

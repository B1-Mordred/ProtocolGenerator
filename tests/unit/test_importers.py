from __future__ import annotations

from xml.etree.ElementTree import tostring
import xml.etree.ElementTree as ET

import pytest

from addon_generator.importers import ExcelImporter, XmlImporter, map_gui_payload_to_addon


def test_gui_mapper_builds_canonical_addon() -> None:
    addon = map_gui_payload_to_addon(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "X", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "U", "analyte_key": "analyte:1"}],
        }
    )
    assert addon.method is not None and addon.method.method_id == "M-1"
    assert addon.assays[0].key == "assay:1"


def test_excel_importer_reads_rows(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    s = wb.active
    s.append(["MethodId", "MethodVersion", "AssayKey", "ProtocolType", "AnalyteKey", "AnalyteName", "UnitKey", "UnitName"])
    s.append(["M", "1", "a", "A", "n", "Name", "u", "mg/dL"])
    path = tmp_path / "f.xlsx"
    wb.save(path)
    addon = ExcelImporter().import_workbook(path)
    assert addon.method is not None and addon.method.method_id == "M"


def test_xml_importer_maps_required_elements(tmp_path) -> None:
    root = ET.fromstring("<AddOn><MethodId>M</MethodId><MethodVersion>1</MethodVersion><Assays><Assay><Id>0</Id><Name>A</Name><AddOnRef>0</AddOnRef><Analytes><Analyte><Id>0</Id><Name>N</Name><AssayRef>0</AssayRef><AnalyteUnits><AnalyteUnit><Id>0</Id><Name>U</Name><AnalyteRef>0</AnalyteRef></AnalyteUnit></AnalyteUnits></Analyte></Analytes></Assay></Assays></AddOn>")
    xml_path = tmp_path / "addon.xml"
    xml_path.write_text(tostring(root, encoding="unicode"), encoding="utf-8")
    addon = XmlImporter().import_xml(xml_path)
    assert addon.method is not None and addon.method.method_version == "1"

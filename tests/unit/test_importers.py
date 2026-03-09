from __future__ import annotations

from dataclasses import asdict
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import tostring

import pytest

from addon_generator.importers import (
    ExcelImportValidationError,
    ExcelImporter,
    XmlImporter,
    XmlImportValidationError,
    map_gui_payload_to_addon,
)


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


def test_excel_importer_reports_missing_required_columns(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    s = wb.active
    s.append(["MethodId", "AssayKey"])
    s.append(["M", "A"])
    path = tmp_path / "missing-columns.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc_info:
        ExcelImporter().import_workbook(path)

    diagnostics = exc_info.value.to_dict()["diagnostics"]
    assert any(d["rule_id"] == "missing-required-column" and d["column"] == "MethodVersion" for d in diagnostics)


def test_excel_importer_reports_duplicate_rows_with_metadata(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    s = wb.active
    s.append(["MethodId", "MethodVersion", "AssayKey", "ProtocolType", "AnalyteKey", "AnalyteName", "UnitKey", "UnitName"])
    s.append(["M", "1", "a", "A", "n", "Name", "u", "mg/dL"])
    s.append(["M", "1", "a", "A", "n", "Name", "u", "mg/dL"])
    path = tmp_path / "dupes.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc_info:
        ExcelImporter().import_workbook(path)

    duplicate = next(d for d in exc_info.value.to_dict()["diagnostics"] if d["rule_id"] == "duplicate-row")
    assert duplicate["sheet"] == "Sheet"
    assert duplicate["row"] == 3
    assert duplicate["value"]["AssayKey"] == "a"


def test_excel_importer_coerces_bool_numeric_and_empty_cells() -> None:
    importer = ExcelImporter()
    assert importer._coerce_cell(" true ") is True
    assert importer._coerce_cell("0") is False
    assert importer._coerce_cell("42") == 42
    assert importer._coerce_cell("3.14") == pytest.approx(3.14)
    assert importer._coerce_cell("   ") is None


def test_xml_importer_accepts_schema_valid_xml(tmp_path) -> None:
    root = ET.fromstring(
        "<AddOn><Id>10</Id><MethodId>M</MethodId><MethodVersion>1</MethodVersion><Assays><Assay><Id>100</Id><Name>A</Name><AddOnRef>10</AddOnRef><Analytes><Analyte><Id>1000</Id><Name>N</Name><AssayRef>100</AssayRef><AnalyteUnits><AnalyteUnit><Id>10000</Id><Name>U</Name><AnalyteRef>1000</AnalyteRef></AnalyteUnit></AnalyteUnits></Analyte></Analytes></Assay></Assays></AddOn>"
    )
    xml_path = tmp_path / "addon.xml"
    xml_path.write_text(tostring(root, encoding="unicode"), encoding="utf-8")

    addon = XmlImporter().import_xml(xml_path)

    assert addon.method is not None and addon.method.method_version == "1"
    assert addon.assays[0].key == "assay:100"


def test_xml_importer_rejects_schema_invalid_xml(tmp_path) -> None:
    invalid_xml = "<AddOn><MethodId>M</MethodId><MethodVersion>1</MethodVersion></AddOn>"
    xml_path = tmp_path / "invalid-addon.xml"
    xml_path.write_text(invalid_xml, encoding="utf-8")

    with pytest.raises(XmlImportValidationError, match="does not conform to schema"):
        XmlImporter().import_xml(xml_path)


def test_xml_importer_produces_same_canonical_entities_as_excel(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["MethodId", "MethodVersion", "AssayKey", "ProtocolType", "AnalyteKey", "AnalyteName", "UnitKey", "UnitName"])
    sheet.append(["M-42", "2.0", "assay:7", "Chem", "analyte:9", "Glucose", "unit:11", "mg/dL"])
    excel_path = tmp_path / "overlap.xlsx"
    wb.save(excel_path)

    xml_content = (
        "<AddOn><Id>42</Id><MethodId>M-42</MethodId><MethodVersion>2.0</MethodVersion>"
        "<Assays><Assay><Id>7</Id><Name>Chem</Name><AddOnRef>42</AddOnRef>"
        "<Analytes><Analyte><Id>9</Id><Name>Glucose</Name><AssayRef>7</AssayRef>"
        "<AnalyteUnits><AnalyteUnit><Id>11</Id><Name>mg/dL</Name><AnalyteRef>9</AnalyteRef>"
        "</AnalyteUnit></AnalyteUnits></Analyte></Analytes></Assay></Assays></AddOn>"
    )
    xml_path = tmp_path / "overlap.xml"
    xml_path.write_text(xml_content, encoding="utf-8")

    addon_from_excel = ExcelImporter().import_workbook(excel_path)
    addon_from_xml = XmlImporter().import_xml(xml_path)

    assert asdict(addon_from_xml) == asdict(addon_from_excel)

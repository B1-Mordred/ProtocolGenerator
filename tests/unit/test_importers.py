from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

import pytest

from addon_generator.importers import ExcelImporter, XmlImporter, map_gui_payload_to_context


def test_gui_mapper_builds_canonical_context_and_optional_fragments() -> None:
    payload = {
        "MethodInformation": {"DisplayName": "Chem Panel", "Id": "101"},
        "rows": [
            {"MethodDisplayName": "Chem Panel", "AssayDisplayName": "A1", "AnalyteName": "Glucose", "UnitName": "mg/dL"},
            {"MethodDisplayName": "Chem Panel", "AssayDisplayName": "A1", "AnalyteName": "Glucose", "UnitName": "mmol/L"},
        ],
        "LoadingWorkflowSteps": [{"StepType": "LoadTip"}],
        "ReagentSettings": [{"Name": "R1"}],
    }

    context = map_gui_payload_to_context(payload)

    assert context.addon.addon_id == 101
    assert context.addon.addon_name == "Chem Panel"
    assert len(context.addon.assays) == 1
    assert len(context.addon.assays[0].analytes[0].units) == 2
    assert set(context.context_fragments) == {"loading", "reagent"}


def test_excel_importer_reads_headers_and_ignores_blank_rows(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["MethodDisplayName", "AssayDisplayName", "AnalyteName", "UnitName"])
    sheet.append(["Chem Panel", "Basic", "Glucose", "mg/dL"])
    sheet.append([None, None, None, None])

    workbook_path = tmp_path / "baseline.xlsx"
    workbook.save(workbook_path)

    context = ExcelImporter().import_workbook(workbook_path)

    assert context.addon.methods[0].display_name == "Chem Panel"
    assert context.addon.assays[0].name == "Basic"


def test_xml_importer_maps_addon_assay_analyte_and_fragments(tmp_path) -> None:
    root = Element("AddOn", {"Name": "XML Panel", "Id": "77"})
    assay = SubElement(root, "Assay", {"Name": "Assay-X"})
    analyte = SubElement(assay, "Analyte", {"Name": "Na"})
    SubElement(analyte, "AnalyteUnit", {"Name": "mmol/L"})
    loading = SubElement(root, "LoadingWorkflowSteps")
    SubElement(loading, "Step").text = "Load"

    xml_path = tmp_path / "addon.xml"
    xml_path.write_text(tostring(root, encoding="unicode"), encoding="utf-8")

    context = XmlImporter().import_xml(xml_path)

    assert context.addon.addon_id == 77
    assert context.addon.addon_name == "XML Panel"
    assert context.addon.assays[0].analytes[0].name == "Na"
    assert "loading" in context.context_fragments

from __future__ import annotations

import pytest

from addon_generator.importers import ExcelImportValidationError, ExcelImporter
from addon_generator.importers.excel.workbook_parser import ExcelWorkbookParser


def _build_template_workbook(openpyxl):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    basics = wb.create_sheet("Basics")
    basics.append(["Method Id", "M-100"])
    basics.append(["Method Version", "1.0"])
    basics.append(["Method Display Name", "Panel A"])
    basics.append([])
    basics.append(["Assay Key", "Protocol Type", "Protocol Display Name", "Xml Assay Name"])
    basics.append(["assay:chem", "CHEM", "Chemistry", "Chemistry"])
    basics.append([None, None, None, None])

    analytes = wb.create_sheet("Analytes")
    analytes.append(["Notes"])
    analytes.append(["Analyte", "Unit", "Parameter Set", "Assay Key"])
    analytes.append(["GLU", "mg/dL", "CHEM", "assay:chem"])
    analytes.append([None, None, None, None])

    sample = wb.create_sheet("SamplePrep")
    sample.append(["Order", "Action"])
    sample.append(["1", "Mix"])
    sample.append([None, None])

    dilutions = wb.create_sheet("Dilutions")
    dilutions.append(["Name", "Ratio"])
    dilutions.append(["Std1", "1:2"])
    dilutions.append([None, None])

    wb.create_sheet("AddOn CheckList")

    hidden = wb.create_sheet("Hidden_Lists")
    hidden.append(["Units", "SamplePrepAction"])
    hidden.append(["mg/dL", "Mix"])

    return wb


def test_workbook_parser_maps_template_sheets_to_dtos(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)
    path = tmp_path / "template.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.method is not None
    assert bundle.method.method_id == "M-100"
    assert bundle.assays[0].key == "assay:chem"
    assert bundle.analytes[0].name == "GLU"
    assert bundle.units[0].name == "mg/dL"
    assert bundle.sample_prep_steps[0].label == "Mix"
    assert bundle.dilution_schemes[0].metadata["ratio"] == "1:2"


def test_workbook_parser_reports_invalid_vocab_from_hidden_lists(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)
    wb["Analytes"].cell(row=3, column=2, value="invalid-unit")
    path = tmp_path / "bad-template.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc:
        ExcelWorkbookParser().parse_path(path)

    assert "validation errors" in str(exc.value).lower()

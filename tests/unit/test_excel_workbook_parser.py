from __future__ import annotations

from pathlib import Path

import pytest

from addon_generator.importers import ExcelImportValidationError, ExcelImporter
from addon_generator.importers.excel.workbook_parser import ExcelWorkbookParser
from fixture_loader import materialize_workbook_fixture


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


def test_production_fixture_successfully_imports_and_links_entities(tmp_path: Path) -> None:
    workbook_path = materialize_workbook_fixture("production-shape", tmp_path)

    bundle = ExcelImporter().import_workbook_bundle(workbook_path)

    assert bundle.method is not None and bundle.method.method_id == "PRD-001"
    assert [assay.key for assay in bundle.assays] == ["assay:chem", "assay:imm"]
    assert [(a.name, a.assay_key) for a in bundle.analytes] == [("GLU", "assay:chem"), ("TSH", "assay:imm")]
    assert [unit.analyte_key for unit in bundle.units] == ["analyte:GLU", "analyte:TSH"]


def test_header_detection_and_checklist_exclusion_are_robust(tmp_path: Path) -> None:
    workbook_path = materialize_workbook_fixture("header-offset-and-checklist", tmp_path)

    bundle = ExcelImporter().import_workbook_bundle(workbook_path)

    assert [a.name for a in bundle.analytes] == ["Na"]
    assert bundle.analytes[0].assay_key == "assay:chem"
    assert all(a.name != "SHOULD_NOT_PARSE" for a in bundle.analytes)


def test_sampleprep_order_and_dilution_ratio_are_parsed_in_sheet_order(tmp_path: Path) -> None:
    workbook_path = materialize_workbook_fixture("production-shape", tmp_path)

    bundle = ExcelImporter().import_workbook_bundle(workbook_path)

    assert [step.metadata["order"] for step in bundle.sample_prep_steps] == ["1", "2"]
    assert [step.label for step in bundle.sample_prep_steps] == ["Mix", "Incubate"]
    assert [scheme.metadata["ratio"] for scheme in bundle.dilution_schemes] == ["1:2", "1:4"]


def test_hidden_list_vocab_is_ingested_and_validation_errors_are_reported(tmp_path: Path) -> None:
    workbook_path = materialize_workbook_fixture("invalid-hidden-vocab", tmp_path)

    with pytest.raises(ExcelImportValidationError) as exc:
        ExcelImporter().import_workbook_bundle(workbook_path)

    diagnostics = {(d.rule_id, d.sheet, d.column) for d in exc.value.diagnostics}
    assert ("invalid-vocabulary", "Analytes", "Unit") in diagnostics
    assert ("invalid-vocabulary", "SamplePrep", "Action") in diagnostics


def test_workbook_parser_reports_sheet_specific_duplicate_row_diagnostics(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["Basics"].append(["assay:chem", "CHEM", "Chemistry", "Chemistry"])
    wb["Analytes"].append(["GLU", "mg/dL", "CHEM", "assay:chem"])
    wb["SamplePrep"].append(["1", "Mix"])
    wb["Dilutions"].append(["Std1", "1:2"])

    path = tmp_path / "duplicate-template.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc:
        ExcelWorkbookParser().parse_path(path)

    diagnostics = {(d.rule_id, d.sheet): d for d in exc.value.diagnostics if d.rule_id == "duplicate-row"}

    assert diagnostics[("duplicate-row", "Basics")].value == {
        "assay_key": "assay:chem",
        "protocol_type": "CHEM",
        "duplicate_key": "assay:chem|CHEM",
    }
    assert diagnostics[("duplicate-row", "Analytes")].value == {
        "analyte": "GLU",
        "assay_key": "assay:chem",
        "duplicate_key": "GLU|assay:chem",
    }
    assert diagnostics[("duplicate-row", "SamplePrep")].value == {
        "order": "1",
        "action": "Mix",
        "duplicate_key": "1|Mix",
    }
    assert diagnostics[("duplicate-row", "Dilutions")].value == {
        "name": "Std1",
        "duplicate_key": "Std1",
    }


def test_workbook_parser_supports_case_and_spacing_variants_in_sheet_names(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    basics = wb.create_sheet(" Basics ")
    basics.append(["Method Id", "M-200"])
    basics.append(["Method Version", "1.0"])
    basics.append(["Method Display Name", "Panel B"])
    basics.append([])
    basics.append(["Assay Key", "Protocol Type", "Protocol Display Name", "Xml Assay Name"])
    basics.append(["assay:chem", "CHEM", "Chemistry", "Chemistry"])

    analytes = wb.create_sheet("Analytes ")
    analytes.append(["Analyte", "Unit", "Parameter Set", "Assay Key"])
    analytes.append(["GLU", "mg/dL", "CHEM", "assay:chem"])

    hidden = wb.create_sheet(" hidden_lists ")
    hidden.append(["Units"])
    hidden.append(["mg/dL"])

    path = tmp_path / "variant-sheet-names.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.method is not None
    assert bundle.method.method_id == "M-200"
    assert [a.key for a in bundle.assays] == ["assay:chem"]
    assert [a.name for a in bundle.analytes] == ["GLU"]


def test_supports_workbook_template_normalizes_sheet_names() -> None:
    assert ExcelWorkbookParser.supports_workbook_template([" Basics ", "ANALYTES", "hidden_lists", "AddOn CheckList"]) is True

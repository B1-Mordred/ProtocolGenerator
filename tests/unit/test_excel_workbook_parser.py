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


def test_sampleprep_imports_extended_columns_with_header_aliases(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["SamplePrep"].delete_rows(1, wb["SamplePrep"].max_row)
    wb["SamplePrep"].append(["Order", "Action", "Source", "Destination", "Volume [uL]", "Duration [sec]", "Force [rpm]"])
    wb["SamplePrep"].append(["1", "Mix", "Tube A", "Tube B", "10", "5", "1200"])

    path = tmp_path / "sampleprep-extended.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.sample_prep_steps[0].metadata == {
        "order": "1",
        "action": "Mix",
        "source": "Tube A",
        "destination": "Tube B",
        "volume": "10",
        "duration": "5",
        "force": "1200",
    }


def test_sampleprep_assigns_row_order_when_order_header_absent(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["SamplePrep"].delete_rows(1, wb["SamplePrep"].max_row)
    wb["SamplePrep"].append(["Action", "Source", "Destination"])
    wb["SamplePrep"].append(["Mix", "A", "B"])
    wb["SamplePrep"].append(["Incubate", "B", "C"])
    wb["Hidden_Lists"].append([None, "Incubate"])

    path = tmp_path / "sampleprep-row-order-fallback.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert [step.metadata["order"] for step in bundle.sample_prep_steps] == ["1", "2"]
    assert [step.key for step in bundle.sample_prep_steps] == ["sampleprep:1", "sampleprep:2"]


def test_dilutions_import_buffer_ratio_aliases_and_synthesizes_ratio_with_inconsistent_spacing(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["Dilutions"].delete_rows(1, wb["Dilutions"].max_row)
    wb["Dilutions"].append(["Dilution Name", "Dilution Buffer 1 Ratio", "Dilution Buffer 2  Ratio", "Dilution Buffer 3  Ratio"])
    wb["Dilutions"].append(["Std1", "2", "3", "5"])

    path = tmp_path / "dilutions-buffer-aliases.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.dilution_schemes[0].metadata == {
        "ratio": "2:3:5",
        "buffer1_ratio": "2",
        "buffer2_ratio": "3",
        "buffer3_ratio": "5",
    }


def test_dilutions_import_buffer_ratio_headers_with_double_spaces(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["Dilutions"].delete_rows(1, wb["Dilutions"].max_row)
    wb["Dilutions"].append(["Dilution Name", "Dilution Buffer 1 Ratio", "Dilution Buffer 2  Ratio", "Dilution Buffer 3   Ratio"])
    wb["Dilutions"].append(["Std1", "2", "3", "5"])

    path = tmp_path / "dilutions-buffer-double-space-headers.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.dilution_schemes[0].metadata == {
        "ratio": "2:3:5",
        "buffer1_ratio": "2",
        "buffer2_ratio": "3",
        "buffer3_ratio": "5",
    }


def test_dilutions_import_compact_buffer_ratio_headers_and_synthesizes_ratio(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["Dilutions"].delete_rows(1, wb["Dilutions"].max_row)
    wb["Dilutions"].append(["Dilution Name", "Buffer1 Ratio", "Buffer2 Ratio", "Buffer3 Ratio"])
    wb["Dilutions"].append(["Std1", "2", "3", "5"])

    path = tmp_path / "dilutions-buffer-compact-headers.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert bundle.dilution_schemes[0].metadata == {
        "ratio": "2:3:5",
        "buffer1_ratio": "2",
        "buffer2_ratio": "3",
        "buffer3_ratio": "5",
    }

def test_sampleprep_action_validation_falls_back_to_actions_vocab(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = _build_template_workbook(openpyxl)

    wb["Hidden_Lists"].delete_rows(1, wb["Hidden_Lists"].max_row)
    wb["Hidden_Lists"].append(["Units", "Actions"])
    wb["Hidden_Lists"].append(["mg/dL", "Mix"])
    wb["SamplePrep"].cell(row=2, column=2, value="Unknown Action")

    path = tmp_path / "sampleprep-actions-fallback-vocab.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc:
        ExcelImporter().import_workbook_bundle(path)

    diagnostics = {(d.rule_id, d.sheet, d.column) for d in exc.value.diagnostics}
    assert ("invalid-vocabulary", "SamplePrep", "Action") in diagnostics


def test_analytes_resolve_assay_key_from_parameter_set_when_assay_key_column_absent(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    basics = wb.create_sheet("Basics")
    basics.append(["Method Id", "M-300"])
    basics.append(["Method Version", "1.0"])
    basics.append([])
    basics.append([
        "Product Number",
        "Component Name",
        "Parameter Set Number",
        "Assay Abbreviation",
        'Parameter Set Name (or "Basic Kit")',
        "Type",
        "Container Type (if Liquid)",
    ])
    basics.append(["P-1", "Chemistry Panel", "100", "CHEM", "Chemistry", "KIT", "Tube"])
    basics.append(["P-2", "Immuno Panel", "200", "IMM", "Immunology", "KIT", "Tube"])

    analytes = wb.create_sheet("Analytes")
    analytes.append(["Analyte", "Unit", "Parameter Set"])
    analytes.append(["GLU", "mg/dL", "Chemistry"])
    analytes.append(["TSH", "IU/mL", "200"])

    hidden = wb.create_sheet("Hidden_Lists")
    hidden.append(["Units"])
    hidden.append(["mg/dL"])
    hidden.append(["IU/mL"])

    path = tmp_path / "parameter-set-linking.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert [(a.name, a.assay_key) for a in bundle.analytes] == [
        ("GLU", "100"),
        ("TSH", "200"),
    ]


def test_analytes_emit_missing_assay_link_diagnostic_when_parameter_set_is_unresolved(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    basics = wb.create_sheet("Basics")
    basics.append(["Method Id", "M-301"])
    basics.append(["Method Version", "1.0"])
    basics.append([])
    basics.append([
        "Product Number",
        "Component Name",
        "Parameter Set Number",
        "Assay Abbreviation",
        'Parameter Set Name (or "Basic Kit")',
        "Type",
        "Container Type (if Liquid)",
    ])
    basics.append(["P-1", "Chemistry Panel", "100", "CHEM", "Chemistry", "KIT", "Tube"])

    analytes = wb.create_sheet("Analytes")
    analytes.append(["Analyte", "Unit", "Parameter Set"])
    analytes.append(["GLU", "mg/dL", "Unknown Set"])

    hidden = wb.create_sheet("Hidden_Lists")
    hidden.append(["Units"])
    hidden.append(["mg/dL"])

    path = tmp_path / "missing-assay-link.xlsx"
    wb.save(path)

    with pytest.raises(ExcelImportValidationError) as exc:
        ExcelImporter().import_workbook_bundle(path)

    diagnostics = [d for d in exc.value.diagnostics if d.rule_id == "missing-assay-link"]
    assert len(diagnostics) == 1
    assert diagnostics[0].sheet == "Analytes"
    assert diagnostics[0].column == "Parameter Set"
    assert diagnostics[0].value == {"analyte": "GLU", "parameter_set": "Unknown Set"}


def test_real_world_workbook_populates_manual_entry_identity_fields() -> None:
    pytest.importorskip("openpyxl")

    bundle = ExcelImporter().import_workbook_bundle(Path("tests/AddOn_Input_92111_v03.xlsx"))

    assert bundle.method is not None
    assert bundle.method.series_name == "MassTox®"
    assert bundle.method.display_name == "TDM Series A"
    assert bundle.method.order_number == "92711"
    assert bundle.method.main_title == "MassPrep®"
    assert bundle.method.sub_title == "TDM Series A"
    assert bundle.method.product_number == "42952"

    assert bundle.sample_prep_steps
    assert bundle.sample_prep_steps[0].metadata["source"] == "Urine"
    assert bundle.sample_prep_steps[0].metadata["destination"] == "96 Well filter plates"

    assert bundle.dilution_schemes
    assert bundle.dilution_schemes[0].metadata["buffer1_ratio"] == "100"
    assert bundle.dilution_schemes[0].metadata["buffer2_ratio"] == ""


def test_user_workbook_fills_down_component_metadata_for_sparse_rows() -> None:
    pytest.importorskip("openpyxl")

    bundle = ExcelImporter().import_workbook_bundle(Path("tests/AddOn_Input_92111_v03.xlsx"))

    assay_by_key = {assay.key: assay for assay in bundle.assays}

    assert assay_by_key["92913-XT"].metadata["product_number"] == "92046/N2/XT2"
    assert assay_by_key["92913-XT"].metadata["type"] == "Internal Standard"
    assert assay_by_key["92913-XT"].metadata["container_type"] == "BG 50mL"

def test_user_workbook_addon_input_92111_v03_imports_successfully() -> None:
    pytest.importorskip("openpyxl")

    workbook_path = Path("tests/AddOn_Input_92111_v03.xlsx")
    bundle = ExcelImporter().import_workbook_bundle(workbook_path)

    assert bundle.method is not None
    assert bundle.method.method_id
    assert bundle.assays
    assert bundle.analytes

def test_workbook_parser_keeps_each_non_empty_kit_component_row_when_parameter_set_and_type_repeat(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    basics = wb.create_sheet("Basics")
    basics.append(["Method Id", "PRD-001"])
    basics.append(["Method Version", "5.4"])
    basics.append([])
    basics.append(
        [
            "Product Number",
            "Component Name",
            "Parameter Set Number",
            "Assay Abbreviation",
            'Parameter Set Name (or "BASIC Kit")',
            "Type",
            "Container Type (if liquid)",
        ]
    )
    basics.append(["PN-1", "Calibrator A", "PS-CAL", "CAL-A", "Calibration", "Calibrator", "Vial"])
    basics.append(["", "Calibrator B", "PS-CAL", "CAL-B", "Calibration", "Calibrator", "Vial"])
    basics.append(["", "Control Low", "PS-CTRL", "CTRL-L", "Controls", "Control", "Vial"])
    basics.append(["", "Control High", "PS-CTRL", "CTRL-H", "Controls", "Control", "Vial"])
    basics.append([None, None, None, None, None, None, None])

    analytes = wb.create_sheet("Analytes")
    analytes.append(["Analyte", "Unit", "Parameter Set", "Assay Key"])
    analytes.append(["GLU", "mg/dL", "Calibration", "PS-CAL"])
    analytes.append(["TSH", "uIU/mL", "Controls", "PS-CTRL"])

    sample = wb.create_sheet("SamplePrep")
    sample.append(["Order", "Action"])
    sample.append(["1", "Mix"])

    dilutions = wb.create_sheet("Dilutions")
    dilutions.append(["Name", "Ratio"])
    dilutions.append(["Std1", "1:2"])

    hidden = wb.create_sheet("Hidden_Lists")
    hidden.append(["Units", "SamplePrepAction"])
    hidden.append(["mg/dL", "Mix"])
    hidden.append(["uIU/mL", "Mix"])

    path = tmp_path / "production-shape-duplicate-parameter-set-rows.xlsx"
    wb.save(path)

    bundle = ExcelImporter().import_workbook_bundle(path)

    assert len(bundle.assays) == 4
    assert [assay.metadata["component_name"] for assay in bundle.assays] == [
        "Calibrator A",
        "Calibrator B",
        "Control Low",
        "Control High",
    ]

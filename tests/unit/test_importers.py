from __future__ import annotations

from pathlib import Path
import json
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


from fixture_loader import fixture_metadata, materialize_workbook_fixture
from addon_generator.services.canonical_normalizer import canonical_addons_equal, normalize_addon_for_comparison
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency



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

    assert canonical_addons_equal(addon_from_xml, addon_from_excel)


def test_fixture_loader_materializes_valid_and_malformed_workbooks(tmp_path) -> None:
    valid_path = materialize_workbook_fixture("multi-analyte", tmp_path)
    malformed_path = materialize_workbook_fixture("malformed-workbook", tmp_path)

    assert valid_path.exists() and valid_path.suffix == ".xlsx"
    assert malformed_path.exists() and malformed_path.suffix == ".xlsx"


def test_excel_importer_non_xlsx_fixture_returns_structured_diagnostics(tmp_path) -> None:
    pytest.importorskip("openpyxl")
    workbook_path = materialize_workbook_fixture("malformed-workbook", tmp_path)

    with pytest.raises(ExcelImportValidationError) as exc_info:
        ExcelImporter().import_workbook(workbook_path)

    payload = exc_info.value.to_dict()
    assert payload["message"] == "Workbook could not be opened"
    diagnostics = payload["diagnostics"]
    assert diagnostics and diagnostics[0]["rule_id"] == "invalid-workbook-format"
    assert diagnostics[0]["sheet"] == "(workbook)"
    assert diagnostics[0]["value"]["path"] == str(workbook_path)
    assert diagnostics[0]["value"]["error_type"]
    assert diagnostics[0]["value"]["error_message"]

def test_fixture_alias_mapping_normalizes_and_splits_units(tmp_path) -> None:
    workbook_path = materialize_workbook_fixture("alias-driven-mapping", tmp_path)
    addon = ExcelImporter().import_workbook(workbook_path)

    units = sorted(unit.name for unit in addon.units)
    assert units == ["mg/dL", "µg/mL"]


@pytest.mark.parametrize(
    "scenario",
    ["minimal-valid", "single-assay", "multi-assay", "multi-analyte", "variant-v1-flat", "variant-v2-extra-columns"],
)
def test_fixture_variant_success_matrix_imports(scenario: str, tmp_path) -> None:
    workbook_path = materialize_workbook_fixture(scenario, tmp_path)

    addon = ExcelImporter().import_workbook(workbook_path)

    assert addon.method is not None
    assert addon.assays
    assert addon.analytes


@pytest.mark.parametrize("scenario", ["alias-driven-mapping", "historical-unit-pipe-delimiter"])
def test_fixture_variant_unit_normalization_matrix(scenario: str, tmp_path) -> None:
    workbook_path = materialize_workbook_fixture(scenario, tmp_path)
    addon = ExcelImporter().import_workbook(workbook_path)

    units = sorted(unit.name for unit in addon.units)
    expected_units = sorted(fixture_metadata(scenario)["expected"]["normalized_units"])
    assert units == expected_units


def test_fixture_invalid_cross_file_mapping_surfaces_domain_issues(tmp_path) -> None:
    from addon_generator.validation.domain_validator import validate_domain

    workbook_path = materialize_workbook_fixture("invalid-cross-file-mapping", tmp_path)
    addon = ExcelImporter().import_workbook(workbook_path)
    issue_codes = {issue.code for issue in validate_domain(addon).issues.issues}

    expected = set(fixture_metadata("invalid-cross-file-mapping")["expected"]["error_codes"])
    assert expected.issubset(issue_codes)


def test_fixture_invalid_units_surfaces_domain_issues(tmp_path) -> None:
    from addon_generator.validation.domain_validator import validate_domain

    workbook_path = materialize_workbook_fixture("invalid-units", tmp_path)
    addon = ExcelImporter().import_workbook(workbook_path)
    issue_codes = {issue.code for issue in validate_domain(addon).issues.issues}

    expected = set(fixture_metadata("invalid-units")["expected"]["error_codes"])
    assert expected.issubset(issue_codes)


def test_cross_file_validator_accumulates_multiple_analyte_errors() -> None:
    protocol_json = {"MethodInformation": {"Id": "M", "Version": "1"}, "AssayInformation": []}
    xml = ET.fromstring(
        """
        <AddOn>
          <MethodId>M</MethodId>
          <MethodVersion>1</MethodVersion>
          <Assays>
            <Assay>
              <Id>10</Id>
              <Name>A</Name>
              <Analytes>
                <Analyte>
                  <Id />
                  <AssayRef>999</AssayRef>
                  <AnalyteUnits />
                </Analyte>
              </Analytes>
            </Assay>
          </Assays>
        </AddOn>
        """
    )

    result = validate_cross_file_consistency(protocol_json, xml)
    issue_codes = [issue.code for issue in result.issues.issues]

    assert "invalid-analyte-id" in issue_codes
    assert "broken-assay-ref" in issue_codes


def test_fixture_index_contains_expected_scenarios() -> None:
    index_path = Path("tests/fixtures/index.json")
    data = json.loads(index_path.read_text(encoding="utf-8"))["workbook_fixtures"]

    assert {
        "minimal-valid",
        "single-assay",
        "multi-assay",
        "multi-analyte",
        "alias-driven-mapping",
        "invalid-cross-file-mapping",
        "invalid-units",
        "variant-v1-flat",
        "variant-v2-extra-columns",
        "historical-unit-pipe-delimiter",
        "malformed-missing-columns",
        "malformed-duplicate-rows",
        "malformed-workbook",
    }.issubset(set(data))


@pytest.mark.parametrize("scenario", ["malformed-missing-columns", "malformed-duplicate-rows", "malformed-workbook"])
def test_fixture_malformed_workbook_failure_diagnostics_matrix(scenario: str, tmp_path) -> None:
    pytest.importorskip("openpyxl")
    workbook_path = materialize_workbook_fixture(scenario, tmp_path)
    expected_diagnostics = fixture_metadata(scenario)["expected"].get("diagnostics", [])

    with pytest.raises(ExcelImportValidationError) as exc_info:
        ExcelImporter().import_workbook(workbook_path)

    diagnostics = exc_info.value.to_dict()["diagnostics"]
    for expected in expected_diagnostics:
        assert any(
            all(actual.get(key) == value for key, value in expected.items())
            for actual in diagnostics
        ), f"Missing expected diagnostic for {scenario}: {expected}"


def test_canonical_comparison_normalizes_empty_string_and_whitespace() -> None:
    left = map_gui_payload_to_addon(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "MethodInformation": {"DisplayName": ""},
            "assays": [{"key": "assay:1", "protocol_type": " Chem ", "protocol_display_name": "", "xml_name": "Chem"}],
            "analytes": [{"key": "analyte:1", "name": "Glucose", "assay_key": "assay:1", "assay_information_type": ""}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )
    right = map_gui_payload_to_addon(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "MethodInformation": {"DisplayName": None},
            "assays": [{"key": "assay:1", "protocol_type": "Chem", "protocol_display_name": None, "xml_name": "Chem"}],
            "analytes": [{"key": "analyte:1", "name": "Glucose", "assay_key": "assay:1", "assay_information_type": None}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    assert canonical_addons_equal(left, right)


def test_excel_assay_label_normalization_matches_xml(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")

    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["MethodId", "MethodVersion", "AssayKey", "ProtocolType", "AssayDisplayName", "XmlAssayName", "AnalyteKey", "AnalyteName", "UnitKey", "UnitName"])
    sheet.append(["M-42", "2.0", "assay:7", "  Chem  ", "", "Chem", "analyte:9", "Glucose", "unit:11", "mg/dL"])
    excel_path = tmp_path / "assay-normalized.xlsx"
    wb.save(excel_path)

    xml_content = (
        "<AddOn><Id>42</Id><MethodId>M-42</MethodId><MethodVersion>2.0</MethodVersion>"
        "<Assays><Assay><Id>7</Id><Name>Chem</Name><AddOnRef>42</AddOnRef>"
        "<Analytes><Analyte><Id>9</Id><Name>Glucose</Name><AssayRef>7</AssayRef>"
        "<AnalyteUnits><AnalyteUnit><Id>11</Id><Name>mg/dL</Name><AnalyteRef>9</AnalyteRef>"
        "</AnalyteUnit></AnalyteUnits></Analyte></Analytes></Assay></Assays></AddOn>"
    )
    xml_path = tmp_path / "assay-normalized.xml"
    xml_path.write_text(xml_content, encoding="utf-8")

    addon_from_excel = ExcelImporter().import_workbook(excel_path)
    addon_from_xml = XmlImporter().import_xml(xml_path)

    assert canonical_addons_equal(addon_from_excel, addon_from_xml)


def test_canonical_comparison_excludes_source_only_metadata_fields() -> None:
    left = map_gui_payload_to_addon(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "X", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "U", "analyte_key": "analyte:1"}],
        }
    )
    right = map_gui_payload_to_addon(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "X", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "U", "analyte_key": "analyte:1"}],
        }
    )
    left.source_metadata["provenance"] = {"path": [{"source": "excel"}]}
    left.source_metadata["source_name"] = "file-a.xlsx"
    right.source_metadata["provenance"] = {"path": [{"source": "xml"}]}
    right.source_metadata["source_name"] = "file-b.xml"

    assert normalize_addon_for_comparison(left) == normalize_addon_for_comparison(right)


def test_read_workbook_rows_v2_preserves_unlinked_records() -> None:
    importer = ExcelImporter()

    importer._parse_workbook_rows = lambda _path: {  # type: ignore[method-assign]
        "layout_version": "v2-sheeted",
        "method": {"method_id": "M-1", "method_version": "1.0", "method_display_name": "Method"},
        "assays": [{"assay_key": "assay:real", "protocol_type": "CHEM", "assay_display_name": "Chem", "xml_assay_name": "Chem"}],
        "analytes": [{"analyte_key": "analyte:oops", "analyte_name": "GLU", "assay_key": "assay:missing", "assay_information_type": "CHEM"}],
        "units": [{"unit_key": "unit:oops", "unit_name": "mg/dL", "analyte_key": "analyte:missing"}],
    }

    rows = importer.read_workbook_rows("ignored.xlsx")

    assert any(row.get("AssayKey") == "assay:real" and not row.get("AnalyteKey") for row in rows)
    assert any(row.get("AnalyteKey") == "analyte:oops" and row.get("AssayKey") == "assay:missing" for row in rows)
    assert any(row.get("UnitKey") == "unit:oops" and row.get("AnalyteKey") == "analyte:missing" for row in rows)

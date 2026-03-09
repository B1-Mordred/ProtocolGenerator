import pytest

from addon_generator.services.generation_service import GenerationService


def test_generation_pipeline_produces_linked_outputs() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    result = service.generate_all(addon)

    assert result.protocol_json["MethodInformation"]["Id"] == "M-1"
    assert result.protocol_json["MethodInformation"]["Version"] == "1.0"
    assert result.protocol_json["LoadingWorkflowSteps"]
    assert result.protocol_json["ProcessingWorkflowSteps"]
    assert "<MethodId>M-1</MethodId>" in result.analytes_xml_string
    assert result.issues == []


def test_excel_import_pipeline_flow_with_sheeted_layout(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()

    method = wb.active
    method.title = "Method"
    method.append(["MethodId", "MethodVersion", "MethodDisplayName"])
    method.append(["M-2", "2.0", "Sheeted Layout"])

    assays = wb.create_sheet("Assays")
    assays.append(["AssayKey", "ProtocolType", "AssayDisplayName", "XmlAssayName"])
    assays.append(["assay-1", "Chem", "Chemistry", "Chem"])

    analytes = wb.create_sheet("Analytes")
    analytes.append(["AnalyteKey", "AnalyteName", "AssayKey", "AssayInformationType"])
    analytes.append(["analyte-1", "GLU", "assay-1", "Primary"])

    units = wb.create_sheet("Units")
    units.append(["UnitKey", "UnitName", "AnalyteKey"])
    units.append(["unit-1", "mg/dL", "analyte-1"])

    path = tmp_path / "sheeted.xlsx"
    wb.save(path)

    service = GenerationService()
    addon = service.import_from_excel(str(path))
    result = service.generate_all(addon)

    assert addon.method is not None and addon.method.method_id == "M-2"
    assert addon.assays[0].protocol_type == "Chem"
    assert addon.analytes[0].assay_key == "assay-1"
    assert addon.units[0].analyte_key == "analyte-1"
    assert result.protocol_json["MethodInformation"]["Id"] == "M-2"
    assert result.issues == []

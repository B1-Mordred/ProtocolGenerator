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
    assert "<MethodId>M-1</MethodId>" in result.analytes_xml_string
    assert result.issues == []

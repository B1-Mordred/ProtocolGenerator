from addon_generator.input_models.dtos import DilutionSchemeInputDTO, InputDTOBundle
from addon_generator.services.generation_service import GenerationService


def test_generation_service_import_and_domain_validation() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M", "method_version": "1", "MethodInformation": {"DisplayName": "Method"}, "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}], "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}], "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}]})
    issues = service.validate_domain(addon)
    assert issues.has_errors() is False


def test_generation_merge_precedence_and_provenance() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "MethodInformation": {
                "DisplayName": "GUI Name",
                "MainTitle": "GUI Main",
            },
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [],
            "units": [],
        }
    )

    imported_fragments = {
        "MethodInformation": {
            "DisplayName": "Imported Name",
            "MainTitle": "Imported Main",
            "SubTitle": "Imported Sub",
        }
    }

    result = service.generate_protocol_json(addon, imported_fragments)
    method = result.payload["MethodInformation"]

    assert method["DisplayName"] == "GUI Name"
    assert method["MainTitle"] == "GUI Main"
    assert method["SubTitle"] == "Imported Sub"

    provenance = {entry["path"]: entry for entry in result.merge_report["field_provenance"]}
    assert provenance["MethodInformation.DisplayName"]["source"] == "gui"
    assert provenance["MethodInformation.DisplayName"]["conflict"] is True
    assert provenance["MethodInformation.SubTitle"]["source"] == "imported"
    assert "gui" not in provenance["MethodInformation.SubTitle"]["conflict_sources"]


def test_generation_merge_report_is_deterministic_and_has_required_field_views() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M-2", "method_version": "1.0", "assays": [], "analytes": [], "units": []})

    first = service.generate_protocol_json(addon).merge_report
    second = service.generate_protocol_json(addon).merge_report

    assert first == second
    assert first["field_provenance"] == sorted(first["field_provenance"], key=lambda item: item["path"])
    assert first["required_fields"] == {"unresolved": [], "conflicting": []}


def test_generate_all_consumes_dto_context_for_validation() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M", "method_version": "1", "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}], "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}], "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}]})
    dto_bundle = InputDTOBundle(source_type="excel", dilution_schemes=[DilutionSchemeInputDTO(key="d:1", metadata={"ratio": "bad"})])

    result = service.generate_all(addon, dto_bundle=dto_bundle)

    assert "malformed-dilution-scheme" in {issue.code for issue in result.issues}


def test_dto_bundle_builder_ignores_non_mapping_source_metadata_values() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M-3",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )
    addon.source_metadata = {
        "sample_prep_steps": None,
        "dilution_schemes": None,
        "hidden_vocab": ["not", "a", "mapping"],
        "provenance": "excel.xlsx",
    }

    bundle = service._dto_bundle_from_addon(addon)

    assert bundle.sample_prep_steps == []
    assert bundle.dilution_schemes == []
    assert bundle.hidden_vocab == {}
    assert bundle.provenance == {}

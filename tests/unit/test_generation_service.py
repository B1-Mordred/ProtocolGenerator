from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue
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


def test_generate_all_applies_mapping_overrides_for_cross_file_mode() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [{"key": "assay:1", "protocol_type": "A  ", "xml_name": "a"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    baseline = service.generate_all(addon)
    assert "assay-cross-file-mismatch" in {issue.code for issue in baseline.issues}

    overridden = service.generate_all(
        addon,
        mapping_overrides={"assay_mapping": {"cross_file_match": {"mode": "normalized"}}},
    )
    assert "assay-cross-file-mismatch" not in {issue.code for issue in overridden.issues}


def test_generate_all_applies_mapping_overrides_for_protocol_defaults() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M", "method_version": "1", "assays": [], "analytes": [], "units": []})

    result = service.generate_all(
        addon,
        mapping_overrides={"protocol_defaults": {"method_information": {"DisplayName": "Configured Name"}}},
    )

    assert result.protocol_json["MethodInformation"]["DisplayName"] == "Configured Name"


def test_generate_all_derives_protocol_defaults_from_manual_metadata() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [
                {
                    "key": "assay:1",
                    "protocol_type": "Immuno",
                    "protocol_display_name": "Calibrator Assay",
                    "xml_name": "Immuno",
                    "metadata": {
                        "component_name": "Calibrator A",
                        "parameter_set_number": "PS-01",
                        "type": "Calibrator",
                        "container_type": "Vial",
                    },
                }
            ],
            "analytes": [
                {
                    "key": "analyte:1",
                    "name": "AN1",
                    "assay_key": "assay:1",
                    "assay_information_type": "Immunology",
                }
            ],
            "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
        }
    )

    result = service.generate_all(addon)

    assert result.protocol_json["AssayInformation"][0]["StopPreparationWithFailedCalibrator"] is True
    assert result.resolved_mapping_snapshot["protocol_defaults"]["loading_workflow_steps"][0]["StepParameters"]["FullFilename"] == "immuno-loading-template"
    assert result.resolved_mapping_snapshot["protocol_defaults"]["processing_workflow_steps"][0]["GroupDisplayName"] == "Calibrator Assay"


def test_generate_all_user_overrides_take_precedence_over_derived_defaults() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [
                {
                    "key": "assay:1",
                    "protocol_type": "Immuno",
                    "xml_name": "Immuno",
                    "metadata": {
                        "component_name": "Calibrator A",
                        "parameter_set_number": "PS-01",
                        "type": "Calibrator",
                        "container_type": "Vial",
                    },
                }
            ],
            "analytes": [],
            "units": [],
        }
    )

    result = service.generate_all(
        addon,
        mapping_overrides={
            "protocol_defaults": {
                "processing_workflow_steps": [
                    {
                        "GroupDisplayName": "Manual Override",
                        "GroupIndex": 0,
                        "GroupSteps": [],
                    }
                ]
            }
        },
    )

    assert result.resolved_mapping_snapshot["protocol_defaults"]["processing_workflow_steps"][0]["GroupDisplayName"] == "Manual Override"


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


def test_sort_issues_preserves_insertion_order_within_phase_and_severity() -> None:
    service = GenerationService()
    staged = [
        ("domain", ValidationIssue(code="b", message="", path="x", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN)),
        ("domain", ValidationIssue(code="a", message="", path="x", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN)),
        ("projection", ValidationIssue(code="z", message="", path="x", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION)),
    ]

    sorted_issues = service._sort_issues(staged)

    assert [issue.code for issue in sorted_issues] == ["b", "a", "z"]


def test_generate_all_synthesizes_missing_assay_groups_for_analytes() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:missing"}],
            "units": [],
        }
    )

    result = service.generate_all(addon)

    assert any(assay.key == "assay:missing" for assay in addon.assays)
    assert "<Name>assay:missing</Name>" in result.analytes_xml_string
    assert "<Name>GLU</Name>" in result.analytes_xml_string
    assert "assay-group-synthesized-from-analytes" in {issue.code for issue in result.warnings}


def test_generate_all_resolves_analyte_assay_key_via_assay_alias() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [{"key": "assay:chem", "protocol_type": "Chem", "xml_name": "Chem"}],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "chem"}],
            "units": [],
        }
    )

    result = service.generate_all(addon)

    assert addon.analytes[0].assay_key == "assay:chem"
    assert "assay-group-synthesized-from-analytes" not in {issue.code for issue in result.warnings}


def test_generate_analytes_xml_applies_assay_group_normalization() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload(
        {
            "method_id": "M",
            "method_version": "1",
            "assays": [],
            "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:auto"}],
            "units": [],
        }
    )

    analytes_xml = service.generate_analytes_xml(addon)

    assert "<Name>assay:auto</Name>" in analytes_xml
    assert "<Name>GLU</Name>" in analytes_xml

from __future__ import annotations

from addon_generator.importers.gui_mapper import map_gui_payload_to_bundle
from addon_generator.input_models.dtos import AssayInputDTO, DilutionSchemeInputDTO, InputDTOBundle, MethodInputDTO, SamplePrepStepInputDTO
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.input_merge_service import InputMergeService


def test_merge_service_applies_deterministic_precedence_and_conflicts() -> None:
    xml_bundle = InputDTOBundle(source_type="xml", source_name="x", method=MethodInputDTO(key="method:M", method_id="M", method_version="1", display_name="XML"))
    gui_bundle = InputDTOBundle(source_type="gui", source_name="g", method=MethodInputDTO(key="method:M", method_id="M", method_version="1", display_name="GUI"))

    merged, report = InputMergeService().merge([gui_bundle, xml_bundle])

    assert merged.method is not None
    assert merged.method.display_name == "GUI"
    assert any(item["path"] == "method.display_name" for item in report["conflicts"])


def test_canonical_builder_converts_bundle_to_domain_model() -> None:
    bundle = map_gui_payload_to_bundle(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
            "analytes": [{"key": "analyte:1", "name": "X", "assay_key": "assay:1"}],
            "units": [{"key": "unit:1", "name": "U", "analyte_key": "analyte:1"}],
        }
    )

    addon = CanonicalModelBuilder().build(bundle)

    assert addon.method is not None and addon.method.method_id == "M-1"
    assert addon.analytes[0].unit_keys == ["unit:1"]
    assert addon.source_metadata["source"] == "gui"


def test_assay_projection_fields_remain_independent_with_stable_linkage() -> None:
    bundle = map_gui_payload_to_bundle(
        {
            "method_id": "M-1",
            "method_version": "1.0",
            "assays": [
                {
                    "key": "assay:1",
                    "protocol_type": "PROTO-A",
                    "protocol_display_name": "Display A",
                    "xml_name": "XML-A",
                }
            ],
            "analytes": [
                {
                    "key": "analyte:1",
                    "name": "Analyte A",
                    "assay_key": "assay:1",
                    "assay_information_type": "PROTO-A",
                }
            ],
            "units": [{"key": "unit:1", "name": "U", "analyte_key": "analyte:1"}],
        }
    )

    addon = CanonicalModelBuilder().build(bundle)

    assert addon.assays[0].protocol_type == "PROTO-A"
    assert addon.assays[0].protocol_display_name == "Display A"
    assert addon.assays[0].xml_name == "XML-A"
    assert addon.analytes[0].assay_key == addon.assays[0].key


def test_merge_service_treats_empty_optional_text_as_none() -> None:
    xml_bundle = InputDTOBundle(source_type="xml", source_name="x", method=MethodInputDTO(key="method:M", method_id="M", method_version="1", display_name=""))
    gui_bundle = InputDTOBundle(source_type="gui", source_name="g", method=MethodInputDTO(key="method:M", method_id="M", method_version="1", display_name=None))

    merged, report = InputMergeService().merge([xml_bundle, gui_bundle])

    assert merged.method is not None
    assert merged.method.display_name is None
    assert not any(item["path"] == "method.display_name" for item in report["conflicts"])


def test_merge_service_includes_sample_prep_and_dilutions_from_input_bundles() -> None:
    gui_bundle = InputDTOBundle(
        source_type="gui",
        sample_prep_steps=[SamplePrepStepInputDTO(key="sp1", label="Mix", metadata={"source": "A"})],
        dilution_schemes=[DilutionSchemeInputDTO(key="d1", label="1+2", metadata={"buffer1_ratio": "50"})],
    )

    merged, _report = InputMergeService().merge([gui_bundle])

    assert len(merged.sample_prep_steps) == 1
    assert merged.sample_prep_steps[0].key == "sp1"
    assert len(merged.dilution_schemes) == 1
    assert merged.dilution_schemes[0].key == "d1"


def test_merge_service_preserves_same_key_assays_with_different_component_metadata() -> None:
    bundle = InputDTOBundle(
        source_type="excel",
        assays=[
            AssayInputDTO(key="assay:shared", metadata={"component_name": "Component A", "parameter_set_number": "PS-1"}),
            AssayInputDTO(key="assay:shared", metadata={"component_name": "Component B", "parameter_set_number": "PS-1"}),
        ],
    )

    merged, report = InputMergeService().merge([bundle])

    assert [assay.metadata.get("component_name") for assay in merged.assays] == ["Component A", "Component B"]
    assert not any(item["path"] == "assays.assay:shared" for item in report["conflicts"])


def test_merge_service_reports_assay_conflicts_only_for_same_composite_identity() -> None:
    low = InputDTOBundle(
        source_type="xml",
        assays=[
            AssayInputDTO(
                key="assay:shared",
                protocol_type="Legacy",
                metadata={
                    "component_name": "Component A",
                    "parameter_set_number": "PS-1",
                    "assay_abbreviation": "ABB",
                    "type": "Liquid",
                    "container_type": "Tube",
                },
            )
        ],
    )
    high = InputDTOBundle(
        source_type="gui",
        assays=[
            AssayInputDTO(
                key="assay:shared",
                protocol_type="New",
                metadata={
                    "component_name": "Component A",
                    "parameter_set_number": "PS-1",
                    "assay_abbreviation": "ABB",
                    "type": "Liquid",
                    "container_type": "Tube",
                },
            ),
            AssayInputDTO(
                key="assay:shared",
                protocol_type="Other",
                metadata={
                    "component_name": "Component B",
                    "parameter_set_number": "PS-1",
                    "assay_abbreviation": "ABB",
                    "type": "Liquid",
                    "container_type": "Tube",
                },
            ),
        ],
    )

    merged, report = InputMergeService().merge([low, high])

    assert [assay.metadata.get("component_name") for assay in merged.assays] == ["Component A", "Component B"]
    assay_conflicts = [item for item in report["conflicts"] if item["path"] == "assays.assay:shared"]
    assert len(assay_conflicts) == 1
    assert assay_conflicts[0]["winner_source"] == "gui"
    assert assay_conflicts[0]["loser_source"] == "xml"


def test_merge_service_preserves_excel_sample_prep_order_instead_of_key_sorting() -> None:
    bundle = InputDTOBundle(
        source_type="excel",
        sample_prep_steps=[
            SamplePrepStepInputDTO(key="sample-prep-1", label="First", metadata={"order": "1"}),
            SamplePrepStepInputDTO(key="sample-prep-10", label="Tenth", metadata={"order": "10"}),
            SamplePrepStepInputDTO(key="sample-prep-2", label="Second", metadata={"order": "2"}),
        ],
    )

    merged, _report = InputMergeService().merge([bundle])

    assert [step.key for step in merged.sample_prep_steps] == ["sample-prep-1", "sample-prep-10", "sample-prep-2"]


def test_merge_service_keeps_sample_prep_in_first_seen_order_when_higher_precedence_overrides() -> None:
    xml_bundle = InputDTOBundle(
        source_type="xml",
        sample_prep_steps=[
            SamplePrepStepInputDTO(key="sample-prep-1", label="Legacy Mix", metadata={"order": "1"}),
            SamplePrepStepInputDTO(key="sample-prep-10", label="Legacy Heat", metadata={"order": "10"}),
        ],
    )
    excel_bundle = InputDTOBundle(
        source_type="excel",
        sample_prep_steps=[
            SamplePrepStepInputDTO(key="sample-prep-1", label="Mix", metadata={"order": "1"}),
            SamplePrepStepInputDTO(key="sample-prep-10", label="Heat", metadata={"order": "10"}),
        ],
    )

    merged, _report = InputMergeService().merge([xml_bundle, excel_bundle])

    assert [step.key for step in merged.sample_prep_steps] == ["sample-prep-1", "sample-prep-10"]
    assert [step.label for step in merged.sample_prep_steps] == ["Mix", "Heat"]

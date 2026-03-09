from __future__ import annotations

from addon_generator.importers.gui_mapper import map_gui_payload_to_bundle
from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
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

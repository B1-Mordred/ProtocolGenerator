from addon_generator.domain.models import AddonModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.generators.protocol_json_generator import generate_protocol_json
from addon_generator.validation.protocol_schema_validator import validate_protocol_schema


def test_protocol_generator_populates_required_sections_and_fields() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="M-1", method_version="1.0"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)
    payload = generate_protocol_json(addon, resolver).payload

    required_method = {
        "Id",
        "DisplayName",
        "Version",
        "MainTitle",
        "SubTitle",
        "OrderNumber",
        "MaximumNumberOfSamples",
        "MaximumNumberOfProcessingCycles",
        "MaximumNumberOfAssays",
        "SamplesLayoutType",
        "MethodInformationType",
    }
    assert required_method.issubset(set(payload["MethodInformation"].keys()))
    assert payload["AssayInformation"] and payload["LoadingWorkflowSteps"] and payload["ProcessingWorkflowSteps"]


def test_generated_protocol_validates_against_schema() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)
    payload = generate_protocol_json(addon, resolver).payload
    validation = validate_protocol_schema(payload, schema_path="protocol.schema.json")
    assert validation.is_valid is True


def test_protocol_generator_uses_fragment_definitions_for_deterministic_workflow_rendering() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
        source_metadata={
            "assay_family": "chemistry",
            "reagent": "rg-1",
            "dilution": "1:20",
            "instrument": "inst-9",
            "config": "cfg-z",
        },
        protocol_context=ProtocolContextModel(
            assay_fragments=[
                {
                    "name": "chemistry-rg1",
                    "selector": {"assay_family": "chemistry", "reagent": "rg-1"},
                    "payload": {"Type": "CHEM", "DisplayName": "Chemistry RG1"},
                }
            ],
            loading_fragments=[
                {
                    "name": "generic-loading",
                    "selector": {"assay_family": "chemistry"},
                    "payload": [{"StepName": "GENERIC"}],
                },
                {
                    "name": "specific-loading",
                    "selector": {
                        "assay_family": "chemistry",
                        "reagent": "rg-1",
                        "dilution": "1:20",
                        "instrument": "inst-9",
                        "config": "cfg-z",
                    },
                    "payload": [{"StepName": "SPECIFIC"}],
                },
            ],
            processing_fragments=[
                {
                    "name": "specific-processing",
                    "selector": {
                        "assay_family": "chemistry",
                        "reagent": "rg-1",
                        "dilution": "1:20",
                        "instrument": "inst-9",
                        "config": "cfg-z",
                    },
                    "payload": [{"StepName": "PROC-SPECIFIC"}],
                }
            ],
        ),
    )

    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)
    payload = generate_protocol_json(addon, resolver).payload

    assert payload["AssayInformation"] == [{"Type": "A"}]
    assert payload["LoadingWorkflowSteps"] == [{"StepName": "SPECIFIC"}]
    assert payload["ProcessingWorkflowSteps"] == [
        {
            "GroupDisplayName": "Default",
            "GroupIndex": 0,
            "GroupSteps": [
                {
                    "StepName": "PROC-SPECIFIC",
                    "StepType": "PROC-SPECIFIC",
                    "StepIndex": 0,
                    "StaticDurationInSeconds": 0,
                    "DynamicDurationInSeconds": 0,
                }
            ],
        }
    ]

    validation = validate_protocol_schema(payload, schema_path="protocol.schema.json")
    assert validation.is_valid is True

def test_protocol_generator_uses_schema_valid_samples_layout_for_multi_assay() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1"),
        assays=[
            AssayModel(key="a1", protocol_type="A", xml_name="A"),
            AssayModel(key="a2", protocol_type="B", xml_name="B"),
        ],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)
    payload = generate_protocol_json(addon, resolver).payload

    assert payload["MethodInformation"]["SamplesLayoutType"] in {"SAMPLES_LAYOUT_COMBINED", "SAMPLES_LAYOUT_SPLIT"}
    assert payload["MethodInformation"]["SamplesLayoutType"] == "SAMPLES_LAYOUT_SPLIT"

    validation = validate_protocol_schema(payload, schema_path="protocol.schema.json")
    assert validation.is_valid is True


def test_protocol_generator_method_information_prefers_addon_product_number() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1.2", product_number="PN-42"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)

    payload = generate_protocol_json(addon, resolver).payload

    assert payload["MethodInformation"]["Id"] == "PN-42"
    assert payload["MethodInformation"]["Version"] == "1.2"


def test_protocol_generator_method_information_defaults_blank_version_to_zero_version() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="  ", product_number="PN-42"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)

    payload = generate_protocol_json(addon, resolver).payload

    assert payload["MethodInformation"]["Id"] == "PN-42"
    assert payload["MethodInformation"]["Version"] == "0.0.0.0"

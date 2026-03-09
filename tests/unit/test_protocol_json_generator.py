from addon_generator.domain.models import AddonModel, AssayModel, MethodModel
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

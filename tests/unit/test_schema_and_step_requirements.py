from __future__ import annotations

from copy import deepcopy

from protocol_generator_gui.schema_utils import loading_step_types, processing_step_types
from protocol_generator_gui.validation import validate_protocol
from protocol_generator_gui.wizard_logic import categorize_schema_fields

from addon_generator.domain.models import AddonModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.generators.protocol_json_generator import generate_protocol_json
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver


def test_schema_parsing_builds_dynamic_required_and_advanced_field_groups(schema: dict):
    load_mfx_schema = loading_step_types(schema)["LoadMfxCarriers"]
    required, advanced = categorize_schema_fields(load_mfx_schema)

    assert {"BarcodeMask", "FullFilename", "RequiredPlates", "RequiredTipRacks"}.issubset(set(required))
    assert advanced == []


def test_loading_workflow_step_type_drives_required_field_resolution(schema: dict, minimal_protocol: dict):
    payload = deepcopy(minimal_protocol)
    payload["LoadingWorkflowSteps"][0]["StepType"] = "LoadCalibratorAndControlCarrier"
    payload["LoadingWorkflowSteps"][0]["StepParameters"] = {
        "BarcodeMask": "*",
        "FullFilename": "carrier.file",
        "TipLabwareType": "tips",
        "AspirationLiquidClassName": "aq",
        "RequiredCalibrators": [],
    }

    errors = validate_protocol(schema, payload)

    assert any("RequiredControls" in msg for _, msg in errors)
    assert any("RequiredReagents" in msg for _, msg in errors)


def test_processing_group_step_type_drives_required_field_resolution(schema: dict, minimal_protocol: dict):
    payload = deepcopy(minimal_protocol)
    group_step = payload["ProcessingWorkflowSteps"][0]["GroupSteps"][0]
    group_step["StepType"] = "StartHeaterShaker"
    group_step["StepParameters"] = {"KeepGripperTools": True}

    errors = validate_protocol(schema, payload)

    assert any(path.endswith("StepParameters") and "LabwareType" in msg for path, msg in errors)


def test_schema_step_type_maps_include_conditional_parameter_schemas(schema: dict):
    loading_map = loading_step_types(schema)
    processing_map = processing_step_types(schema)

    assert "LoadMfxCarriers" in loading_map
    assert "RequiredPlates" in loading_map["LoadMfxCarriers"]["required"]
    assert "UnloadHeaterShaker" in processing_map
    assert "KeepGripperTools" in processing_map["UnloadHeaterShaker"]["required"]


def test_workflow_assembly_assigns_sequential_group_and_step_indexes() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
        protocol_context=ProtocolContextModel(
            processing_fragments=[
                {
                    "GroupDisplayName": "B Group",
                    "GroupSteps": [
                        {"StepType": "Zeta", "StaticDurationInSeconds": 9, "DynamicDurationInSeconds": 3},
                        {"StepType": "Alpha"},
                    ],
                },
                {
                    "GroupDisplayName": "A Group",
                    "GroupSteps": [{"StepType": "Beta"}],
                },
            ]
        ),
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)

    payload = generate_protocol_json(addon, resolver).payload

    groups = payload["ProcessingWorkflowSteps"]
    assert [group["GroupIndex"] for group in groups] == [0, 1]
    assert all("GroupDisplayName" in group for group in groups)
    assert [step["StepIndex"] for step in groups[0]["GroupSteps"]] == [0]
    assert [step["StepIndex"] for step in groups[1]["GroupSteps"]] == [0, 1]
    assert groups[1]["GroupSteps"][0]["StepType"] == "Alpha"
    assert groups[1]["GroupSteps"][0]["StaticDurationInSeconds"] == 0
    assert groups[1]["GroupSteps"][0]["DynamicDurationInSeconds"] == 0


def test_workflow_assembly_normalizes_fragment_only_processing_steps_to_schema_group_shape() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="MID", method_version="1"),
        assays=[AssayModel(key="a1", protocol_type="A", xml_name="A")],
        protocol_context=ProtocolContextModel(
            processing_fragments=[
                {"StepName": "PROC-B"},
                {"StepName": "PROC-A"},
            ]
        ),
    )
    resolver = LinkResolver(load_mapping_config("config/mapping.v1.yaml"))
    resolver.assign_ids(addon)

    payload = generate_protocol_json(addon, resolver).payload

    assert len(payload["ProcessingWorkflowSteps"]) == 1
    group = payload["ProcessingWorkflowSteps"][0]
    assert group["GroupIndex"] == 0
    assert [step["StepType"] for step in group["GroupSteps"]] == ["PROC-A", "PROC-B"]
    assert [step["StepIndex"] for step in group["GroupSteps"]] == [0, 1]
    assert all(isinstance(step["StepParameters"], dict) for step in group["GroupSteps"])

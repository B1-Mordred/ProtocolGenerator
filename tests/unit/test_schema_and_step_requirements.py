from __future__ import annotations

from copy import deepcopy

from protocol_generator_gui.schema_utils import loading_step_types, processing_step_types
from protocol_generator_gui.validation import validate_protocol
from protocol_generator_gui.wizard_logic import categorize_schema_fields


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

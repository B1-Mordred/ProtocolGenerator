from __future__ import annotations

from copy import deepcopy

from protocol_generator_gui.validation import validate_protocol
from protocol_generator_gui.wizard_logic import build_import_conflicts, can_progress, resolve_conflict


def test_validation_reports_missing_required_sections(schema: dict):
    errors = validate_protocol(schema, {})
    assert errors
    assert any("MethodInformation" in msg for _, msg in errors)


def test_validation_accepts_minimal_valid_protocol_shape(schema: dict, minimal_protocol: dict):
    assert validate_protocol(schema, minimal_protocol) == []


def test_validation_rejects_missing_nested_required_arrays(schema: dict, minimal_protocol: dict):
    payload = deepcopy(minimal_protocol)
    del payload["LoadingWorkflowSteps"][0]["StepParameters"]["RequiredPlates"]

    errors = validate_protocol(schema, payload)

    assert any(path.endswith("LoadingWorkflowSteps/0/StepParameters") and "RequiredPlates" in msg for path, msg in errors)


def test_validation_rejects_numeric_values_below_minimum(schema: dict, minimal_protocol: dict):
    payload = deepcopy(minimal_protocol)
    payload["MethodInformation"]["MaximumNumberOfSamples"] = -1

    errors = validate_protocol(schema, payload)

    assert ("MethodInformation/MaximumNumberOfSamples", "must be >= 1") in errors


def test_validation_rejects_unknown_loading_step_type(schema: dict, minimal_protocol: dict):
    payload = deepcopy(minimal_protocol)
    payload["LoadingWorkflowSteps"][0]["StepType"] = "NotKnown"

    errors = validate_protocol(schema, payload)

    assert any(path.endswith("LoadingWorkflowSteps/0/StepType") and "must be one of" in msg for path, msg in errors)


def test_required_conflict_gating_for_export_stage():
    conflicts = build_import_conflicts({"AssayInformation": []}, {"AssayInformation": [{"Type": "A"}]}, {"AssayInformation"})
    allowed, _ = can_progress("output_preview_export", conflicts)
    assert allowed is False

    resolve_conflict(conflicts, "AssayInformation", "keep_current")
    allowed_after, _ = can_progress("output_preview_export", conflicts)
    assert allowed_after is True

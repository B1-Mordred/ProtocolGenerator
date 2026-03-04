from __future__ import annotations

from copy import deepcopy

from protocol_generator_gui.validation import validate_protocol


def test_json_assembly_from_wizard_sections_validates(schema: dict, minimal_protocol: dict):
    sections = {
        "MethodInformation": deepcopy(minimal_protocol["MethodInformation"]),
        "AssayInformation": deepcopy(minimal_protocol["AssayInformation"]),
        "LoadingWorkflowSteps": deepcopy(minimal_protocol["LoadingWorkflowSteps"]),
        "ProcessingWorkflowSteps": deepcopy(minimal_protocol["ProcessingWorkflowSteps"]),
    }
    assembled = {
        "MethodInformation": sections["MethodInformation"],
        "AssayInformation": sections["AssayInformation"],
        "LoadingWorkflowSteps": sections["LoadingWorkflowSteps"],
        "ProcessingWorkflowSteps": sections["ProcessingWorkflowSteps"],
    }

    assert validate_protocol(schema, assembled) == []

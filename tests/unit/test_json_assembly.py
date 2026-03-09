from __future__ import annotations

from copy import deepcopy

from addon_generator.services.generation_service import GenerationService, fragments_from_protocol_payload
from protocol_generator_gui.validation import validate_protocol


def test_json_assembly_from_wizard_sections_validates(schema: dict, minimal_protocol: dict):
    payload = {
        "MethodInformation": deepcopy(minimal_protocol["MethodInformation"]),
        "AssayInformation": deepcopy(minimal_protocol["AssayInformation"]),
        "LoadingWorkflowSteps": deepcopy(minimal_protocol["LoadingWorkflowSteps"]),
        "ProcessingWorkflowSteps": deepcopy(minimal_protocol["ProcessingWorkflowSteps"]),
    }

    service = GenerationService()
    context = service.import_from_gui_payload(payload)
    assembled = service.generate_protocol_json(context, fragments_from_protocol_payload(payload)).payload

    assert validate_protocol(schema, assembled) == []


def test_json_assembly_preserves_direct_workflow_step_payloads(schema: dict, minimal_protocol: dict):
    payload = {
        "MethodInformation": deepcopy(minimal_protocol["MethodInformation"]),
        "AssayInformation": deepcopy(minimal_protocol["AssayInformation"]),
        "LoadingWorkflowSteps": deepcopy(minimal_protocol["LoadingWorkflowSteps"]),
        "ProcessingWorkflowSteps": deepcopy(minimal_protocol["ProcessingWorkflowSteps"]),
    }

    service = GenerationService()
    context = service.import_from_gui_payload(payload)
    assembled = service.generate_protocol_json(context, None).payload

    assert isinstance(assembled["LoadingWorkflowSteps"], list)
    assert isinstance(assembled["ProcessingWorkflowSteps"], list)
    assert validate_protocol(schema, assembled) == []


def test_json_assembly_fragment_wrappers_still_supported(schema: dict, minimal_protocol: dict):
    payload = {
        "MethodInformation": deepcopy(minimal_protocol["MethodInformation"]),
        "AssayInformation": [
            {
                "metadata": {"name": "assay-fragment"},
                "payload": deepcopy(minimal_protocol["AssayInformation"]),
            }
        ],
        "LoadingWorkflowSteps": [
            {
                "metadata": {"name": "loading-fragment"},
                "payload": deepcopy(minimal_protocol["LoadingWorkflowSteps"]),
            }
        ],
        "ProcessingWorkflowSteps": [
            {
                "metadata": {"name": "processing-fragment"},
                "payload": deepcopy(minimal_protocol["ProcessingWorkflowSteps"]),
            }
        ],
    }

    service = GenerationService()
    context = service.import_from_gui_payload(payload)
    assembled = service.generate_protocol_json(context, None).payload

    assert validate_protocol(schema, assembled) == []

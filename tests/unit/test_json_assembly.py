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

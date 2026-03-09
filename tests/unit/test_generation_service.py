from __future__ import annotations

from copy import deepcopy

from addon_generator.services.generation_service import GenerationService, fragments_from_protocol_payload
from protocol_generator_gui.validation import validate_protocol


def test_generate_protocol_json_from_gui_payload_validates(schema: dict, minimal_protocol: dict) -> None:
    service = GenerationService()
    payload = deepcopy(minimal_protocol)

    context = service.import_from_gui_payload(payload)
    fragments = fragments_from_protocol_payload(payload)
    protocol_json = service.generate_protocol_json(context, fragments).payload

    assert validate_protocol(schema, protocol_json) == []


def test_validate_domain_flags_missing_assays() -> None:
    service = GenerationService()
    context = service.import_from_gui_payload({"MethodInformation": {"DisplayName": "OnlyMethod"}, "rows": []})

    issues = service.validate_domain(context)

    assert issues.has_errors() is True
    assert any(issue.code == "missing-assays" for issue in issues.issues)

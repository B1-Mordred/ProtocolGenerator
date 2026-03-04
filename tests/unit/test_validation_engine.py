from __future__ import annotations

from protocol_generator_gui.validation import validate_protocol


def test_validation_enforces_const_values() -> None:
    schema = {
        "type": "object",
        "required": ["mode"],
        "properties": {
            "mode": {"const": "STRICT"},
        },
        "additionalProperties": False,
    }

    errors = validate_protocol(schema, {"mode": "LENIENT"})

    assert ("mode", "must be STRICT") in errors


def test_validation_rejects_values_not_matching_any_one_of_option() -> None:
    schema = {
        "type": "object",
        "required": ["value"],
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "integer", "minimum": 10},
                    {"type": "string", "enum": ["A", "B"]},
                ]
            }
        },
    }

    errors = validate_protocol(schema, {"value": 1})

    assert ("value", "must match exactly one allowed schema") in errors


def test_validation_rejects_additional_properties_when_disallowed() -> None:
    schema = {
        "type": "object",
        "properties": {"known": {"type": "string"}},
        "additionalProperties": False,
    }

    errors = validate_protocol(schema, {"known": "ok", "extra": "nope"})

    assert ("extra", "additional property not allowed") in errors

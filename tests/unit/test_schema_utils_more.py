from __future__ import annotations

from pathlib import Path

from protocol_generator_gui.schema_utils import (
    assay_information_schema,
    dereference,
    load_schema,
    method_information_schema,
    resolve_ref,
)


def test_load_schema_reads_json() -> None:
    schema = load_schema(Path(__file__).resolve().parents[2] / "protocol.schema.json")
    assert schema["type"] == "object"


def test_resolve_ref_follows_local_pointer() -> None:
    schema = {
        "$defs": {"Node": {"type": "object", "properties": {"name": {"type": "string"}}}},
    }

    resolved = resolve_ref(schema, "#/$defs/Node")

    assert resolved["properties"]["name"]["type"] == "string"


def test_dereference_returns_target_for_ref_nodes() -> None:
    schema = {
        "$defs": {"Inner": {"type": "integer", "minimum": 2}},
    }

    resolved = dereference(schema, {"$ref": "#/$defs/Inner"})

    assert resolved["minimum"] == 2


def test_method_and_assay_schema_extractors_return_defs(schema: dict) -> None:
    assert method_information_schema(schema)["type"] == "object"
    assert assay_information_schema(schema)["type"] == "object"

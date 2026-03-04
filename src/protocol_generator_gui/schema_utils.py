from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_schema(schema_path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(schema_path).read_text(encoding="utf-8"))


def resolve_ref(schema: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported ref: {ref}")
    node: Any = schema
    for token in ref[2:].split("/"):
        node = node[token]
    return node


def dereference(schema: Dict[str, Any], node: Dict[str, Any]) -> Dict[str, Any]:
    if "$ref" in node:
        return resolve_ref(schema, node["$ref"])
    return node


def extract_step_type_map(step_schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for rule in step_schema.get("allOf", []):
        step_type = (
            rule.get("if", {})
            .get("properties", {})
            .get("StepType", {})
            .get("const")
        )
        params_schema = (
            rule.get("then", {})
            .get("properties", {})
            .get("StepParameters")
        )
        if step_type and params_schema:
            mapping[step_type] = params_schema
    return mapping


def loading_step_types(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return extract_step_type_map(schema["$defs"]["LoadingWorkflowStep"])


def processing_step_types(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return extract_step_type_map(schema["$defs"]["ProcessingGroupStep"])


def method_information_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    return schema["$defs"]["MethodInformation"]


def assay_information_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    return schema["$defs"]["AssayInformation"]

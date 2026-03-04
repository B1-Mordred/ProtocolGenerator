from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

SCHEMA_FILENAME = "protocol.schema.json"


def default_schema_path() -> Path:
    """Resolve schema path for source, installed, and PyInstaller-frozen execution."""
    search_roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_roots.append(Path(meipass))

    current_file = Path(__file__).resolve()
    search_roots.extend(
        [
            Path.cwd(),
            current_file.parent,
            current_file.parents[1],
            current_file.parents[2],
        ]
    )

    for root in search_roots:
        candidate = root / SCHEMA_FILENAME
        if candidate.exists():
            return candidate

    return search_roots[0] / SCHEMA_FILENAME


def load_schema(schema_path: str | Path | None = None) -> Dict[str, Any]:
    resolved = Path(schema_path) if schema_path is not None else default_schema_path()
    return json.loads(resolved.read_text(encoding="utf-8"))


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

from __future__ import annotations

from typing import Any, Dict, List, Tuple


ValidationError = Tuple[str, str]


def validate_protocol(schema: Dict[str, Any], data: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    _validate_node(schema, schema, data, [], errors)
    return errors


def _resolve_ref(root: Dict[str, Any], ref: str) -> Dict[str, Any]:
    node: Any = root
    for token in ref.removeprefix("#/").split("/"):
        node = node[token]
    return node


def _path(parts: List[Any]) -> str:
    return "/".join(str(p) for p in parts) if parts else "<root>"


def _check_type(expected: str, value: Any) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }.get(expected, True)


def _validate_node(root: Dict[str, Any], schema: Dict[str, Any], value: Any, path: List[Any], errors: List[ValidationError]) -> None:
    if "$ref" in schema:
        schema = _resolve_ref(root, schema["$ref"])

    if "allOf" in schema:
        for part in schema["allOf"]:
            _validate_node(root, part, value, path, errors)

    expected_type = schema.get("type")
    if expected_type and not _check_type(expected_type, value):
        errors.append((_path(path), f"expected type {expected_type}"))
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append((_path(path), f"must be one of {schema['enum']}"))

    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        errors.append((_path(path), f"must be >= {schema['minimum']}"))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append((_path(path), f"must contain at least {schema['minItems']} items"))
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                _validate_node(root, item_schema, item, [*path, i], errors)

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append((_path(path), f"'{key}' is a required property"))

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append((_path([*path, key]), "additional property not allowed"))

        for key, prop_schema in properties.items():
            if key in value:
                _validate_node(root, prop_schema, value[key], [*path, key], errors)

        for cond in schema.get("allOf", []):
            condition = cond.get("if")
            consequence = cond.get("then")
            if condition and consequence and _matches_if(condition, value):
                _validate_node(root, consequence, value, path, errors)


def _matches_if(if_schema: Dict[str, Any], value: Dict[str, Any]) -> bool:
    props = if_schema.get("properties", {})
    for key, spec in props.items():
        if "const" in spec and value.get(key) != spec["const"]:
            return False
    return True

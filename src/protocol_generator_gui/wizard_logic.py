from __future__ import annotations

from typing import Any, Dict

FIELD_METADATA: Dict[str, str] = {
    "Id": "Unique identifier for the method, for example 'method-001'.",
    "DisplayName": "Human-readable name shown to operators.",
    "OrderNumber": "Internal order or catalog number used to identify the method.",
    "BarcodeMask": "Barcode pattern, for example '*' for any barcode prefix.",
    "GroupDisplayName": "Display name used in grouped processing steps.",
}

STEP_HELP = {
    "general": {
        "purpose": "Define the method identity and assay defaults used by downstream workflow steps.",
        "required": ["MethodInformation required fields", "At least one AssayInformation item"],
        "examples": ["DisplayName: Viral Panel A", "MaximumNumberOfSamples: 96"],
    },
    "loading": {
        "purpose": "Describe loading workflow steps and required consumables before processing starts.",
        "required": ["At least one LoadingWorkflowSteps item", "StepType and StepParameters must match schema"],
        "examples": ["LoadMfxCarriers with barcode mask '*'", "LoadCalibratorAndControlCarrier with required controls"],
    },
    "processing": {
        "purpose": "Configure runtime processing behavior and step sequencing for each group.",
        "required": ["At least one processing step in GroupSteps", "StepIndex and duration fields present"],
        "examples": ["SingleTransfer with source/destination settings", "UnloadHeaterShaker with keep gripper tools false"],
    },
}


def build_field_tooltip(name: str, field: Dict[str, Any]) -> str:
    description = str(field.get("description", "")).strip()
    if description:
        return description
    return FIELD_METADATA.get(name, f"Provide a valid value for '{name}' based on the schema type.")


def categorize_schema_fields(schema: Dict[str, Any]) -> tuple[list[str], list[str]]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    required_fields = [name for name in properties.keys() if name in required]
    advanced_fields = [name for name in properties.keys() if name not in required]
    return required_fields, advanced_fields


def make_step_help(step: str) -> str:
    details = STEP_HELP[step]
    required_lines = "\n".join(f"- {line}" for line in details["required"])
    example_lines = "\n".join(f"- {line}" for line in details["examples"])
    return (
        f"Purpose\n{details['purpose']}\n\n"
        f"Required fields\n{required_lines}\n\n"
        f"Examples\n{example_lines}"
    )


def summarize_progress(current_step: int, step_state: Dict[str, Any], status: str) -> str:
    complete = 0
    unresolved = 0
    for key in ("general", "loading", "processing"):
        value = str(step_state[key].get() if hasattr(step_state[key], "get") else step_state[key])
        if value.startswith("✓"):
            complete += 1
        if "(" in value and value.endswith(")"):
            unresolved += int(value.split("(")[-1].split(")")[0])
    if status.startswith("Errors:") and unresolved == 0:
        unresolved = int(status.split()[1])
    return f"Step {current_step}/3 | Completed: {complete}/3 | Unresolved errors: {unresolved}"

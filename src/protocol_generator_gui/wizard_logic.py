from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

from addon_generator.importers.gui_mapper import map_gui_payload_to_addon

FIELD_METADATA: Dict[str, str] = {
    "Id": "Unique identifier for the method, for example 'method-001'.",
    "DisplayName": "Human-readable name shown to operators.",
    "OrderNumber": "Internal order or catalog number used to identify the method.",
    "BarcodeMask": "Barcode pattern, for example '*' for any barcode prefix.",
    "GroupDisplayName": "Display name used in grouped processing steps.",
}

STAGES = [
    "method_setup",
    "assay_analyte_setup",
    "import_preview_conflicts",
    "validation",
    "output_preview_export",
]

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


@dataclass(slots=True)
class ConflictItem:
    field: str
    imported_value: Any
    current_value: Any
    required: bool = False
    provenance_hint: str = "import"
    resolution: str = "unresolved"


@dataclass(slots=True)
class WizardState:
    method_information: dict[str, Any] = field(default_factory=dict)
    assays: list[dict[str, Any]] = field(default_factory=list)
    analytes: list[dict[str, Any]] = field(default_factory=list)
    loading_steps: list[dict[str, Any]] = field(default_factory=list)
    processing_steps: list[dict[str, Any]] = field(default_factory=list)
    imported_payload: dict[str, Any] = field(default_factory=dict)
    conflicts: list[ConflictItem] = field(default_factory=list)
    export_target: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "MethodInformation": dict(self.method_information),
            "AssayInformation": list(self.assays),
            "analytes": list(self.analytes),
            "LoadingWorkflowSteps": list(self.loading_steps),
            "ProcessingWorkflowSteps": list(self.processing_steps),
        }

    def to_draft(self) -> dict[str, Any]:
        return {
            "state": self.to_payload(),
            "imported_payload": self.imported_payload,
            "conflicts": [asdict(c) for c in self.conflicts],
            "export_target": self.export_target,
        }

    @classmethod
    def from_draft(cls, raw: dict[str, Any]) -> "WizardState":
        payload = raw.get("state", raw)
        conflicts = [ConflictItem(**item) for item in raw.get("conflicts", [])]
        return cls(
            method_information=dict(payload.get("MethodInformation", {})),
            assays=list(payload.get("AssayInformation", [])),
            analytes=list(payload.get("analytes", [])),
            loading_steps=list(payload.get("LoadingWorkflowSteps", [])),
            processing_steps=list(payload.get("ProcessingWorkflowSteps", [])),
            imported_payload=dict(raw.get("imported_payload", {})),
            conflicts=conflicts,
            export_target=raw.get("export_target"),
        )


METHOD_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")


def validate_method_editor(method_information: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    method_id = str(method_information.get("Id", "")).strip()
    version = str(method_information.get("Version", "")).strip()
    display_name = str(method_information.get("DisplayName", "")).strip()

    if not method_id:
        issues.append("MethodInformation/Id is required")
    elif not METHOD_ID_PATTERN.match(method_id):
        issues.append("MethodInformation/Id must be alphanumeric with . _ - allowed")

    if not version:
        issues.append("MethodInformation/Version is required")
    elif not VERSION_PATTERN.match(version):
        issues.append("MethodInformation/Version must be numeric dotted notation")

    if not display_name:
        issues.append("MethodInformation/DisplayName is required")

    return issues


def assay_analyte_integrity_warnings(assays: list[dict[str, Any]], analytes: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    assay_types = {str(a.get("Type", "")).strip() for a in assays if str(a.get("Type", "")).strip()}

    seen_map: dict[tuple[str, str], int] = {}
    for analyte in analytes:
        analyte_name = str(analyte.get("name") or analyte.get("Name") or "").strip()
        assay_key = str(analyte.get("assay_key") or analyte.get("AssayType") or "").strip()
        if assay_key and assay_key not in assay_types:
            warnings.append(f"orphan analyte mapping: {analyte_name or '<unnamed>'} -> {assay_key}")
        map_key = (analyte_name.casefold(), assay_key.casefold())
        seen_map[map_key] = seen_map.get(map_key, 0) + 1

    for (name, assay_key), count in seen_map.items():
        if not name:
            continue
        if count > 1:
            warnings.append(f"duplicate analyte mapping: {name} -> {assay_key} ({count} entries)")

    by_name: dict[str, set[str]] = {}
    for analyte in analytes:
        analyte_name = str(analyte.get("name") or analyte.get("Name") or "").strip().casefold()
        assay_key = str(analyte.get("assay_key") or analyte.get("AssayType") or "").strip().casefold()
        if analyte_name:
            by_name.setdefault(analyte_name, set()).add(assay_key)
    for analyte_name, assay_keys in by_name.items():
        non_empty = {k for k in assay_keys if k}
        if len(non_empty) > 1:
            warnings.append(f"ambiguous analyte mapping: {analyte_name} -> {sorted(non_empty)}")

    return warnings


def build_import_conflicts(current_payload: dict[str, Any], imported_payload: dict[str, Any], required_fields: set[str] | None = None) -> list[ConflictItem]:
    required_fields = required_fields or set()
    conflicts: list[ConflictItem] = []
    for field in sorted(set(current_payload.keys()) | set(imported_payload.keys())):
        imported_value = imported_payload.get(field)
        current_value = current_payload.get(field)
        if imported_value == current_value:
            continue
        conflicts.append(
            ConflictItem(
                field=field,
                imported_value=imported_value,
                current_value=current_value,
                required=field in required_fields,
                provenance_hint="imported fragment" if field.startswith("Assay") else "method/import",
            )
        )
    return conflicts


def resolve_conflict(conflicts: list[ConflictItem], field: str, action: str) -> None:
    for conflict in conflicts:
        if conflict.field == field:
            conflict.resolution = action
            return


def unresolved_required_conflicts(conflicts: list[ConflictItem]) -> list[str]:
    return [c.field for c in conflicts if c.required and c.resolution == "unresolved"]


def can_progress(stage: str, conflicts: list[ConflictItem]) -> tuple[bool, str]:
    if stage not in STAGES:
        return False, "Unknown stage"
    unresolved_required = unresolved_required_conflicts(conflicts)
    if stage in {"import_preview_conflicts", "validation", "output_preview_export"} and unresolved_required:
        return False, f"Unresolved required fields: {', '.join(unresolved_required)}"
    return True, "ok"


def build_output_preview(protocol_json: dict[str, Any], analytes_xml: str, target_dir: str | None, blockers: list[str]) -> dict[str, Any]:
    messages: list[str] = []
    if blockers:
        messages.append(f"Blocked export: {len(blockers)} unresolved required fields")
    if not target_dir:
        messages.append("Select an export target to continue")
    return {
        "ProtocolFile.json": json.dumps(protocol_json, indent=2),
        "Analytes.xml": analytes_xml,
        "messages": messages,
        "can_export": not blockers and bool(target_dir),
    }


def gui_payload_to_canonical_dto(payload: dict[str, Any]) -> dict[str, Any]:
    addon = map_gui_payload_to_addon(payload)
    return {
        "method": {"key": addon.method.key, "id": addon.method.method_id, "version": addon.method.method_version},
        "assays": [{"key": assay.key, "type": assay.protocol_type} for assay in addon.assays],
        "analytes": [{"key": analyte.key, "assay_key": analyte.assay_key} for analyte in addon.analytes],
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

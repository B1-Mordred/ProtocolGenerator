from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection


@dataclass(slots=True)
class ProtocolSchemaValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_protocol_schema(
    payload: dict[str, Any],
    schema: dict[str, Any] | None = None,
    schema_path: str | Path | None = None,
) -> ProtocolSchemaValidationResult:
    """Validate protocol payload against JSON schema using jsonschema."""

    issues = ValidationIssueCollection()

    loaded_schema = schema
    if loaded_schema is None:
        if schema_path is None:
            issues.add(
                ValidationIssue(
                    code="schema-missing",
                    message="No JSON schema provided for protocol validation.",
                    path="protocol.schema",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.VALIDATION,
                )
            )
            return ProtocolSchemaValidationResult(is_valid=False, issues=issues)

        path = Path(schema_path)
        if not path.exists():
            issues.add(
                ValidationIssue(
                    code="schema-not-found",
                    message=f"Schema file not found: {path}",
                    path=str(path),
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.VALIDATION,
                )
            )
            return ProtocolSchemaValidationResult(is_valid=False, issues=issues)
        loaded_schema = json.loads(path.read_text(encoding="utf-8"))

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        issues.add(
            ValidationIssue(
                code="jsonschema-unavailable",
                message="jsonschema is not installed; skipped protocol schema validation.",
                path="protocol.schema",
                severity=IssueSeverity.WARNING,
                source=IssueSource.VALIDATION,
            )
        )
        return ProtocolSchemaValidationResult(is_valid=True, issues=issues)

    validator = Draft202012Validator(loaded_schema)
    for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
        instance_path = ".".join(str(segment) for segment in error.path) or "$"
        issues.add(
            ValidationIssue(
                code="protocol-schema-validation",
                message=error.message,
                path=instance_path,
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
                source_location="/".join(str(segment) for segment in error.absolute_schema_path),
            )
        )

    return ProtocolSchemaValidationResult(is_valid=not issues.has_errors(), issues=issues)

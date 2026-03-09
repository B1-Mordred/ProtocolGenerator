from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import ProtocolContextModel


@dataclass(slots=True)
class CrossFileValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_cross_file_consistency(
    context: ProtocolContextModel,
    protocol_payload: dict[str, Any],
) -> CrossFileValidationResult:
    """Validate cross-file consistency between addon domain and generated protocol payload."""

    issues = ValidationIssueCollection()

    _validate_method_version_linkage(context, protocol_payload, issues)
    _validate_assay_refs(context, protocol_payload, issues)

    return CrossFileValidationResult(is_valid=not issues.has_errors(), issues=issues)


def _validate_method_version_linkage(
    context: ProtocolContextModel,
    protocol_payload: dict[str, Any],
    issues: ValidationIssueCollection,
) -> None:
    method_information = protocol_payload.get("MethodInformation", {})
    if not isinstance(method_information, dict):
        issues.add(
            ValidationIssue(
                code="method-information-invalid",
                message="MethodInformation must be an object.",
                path="MethodInformation",
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
            )
        )
        return

    method_id = str(method_information.get("Id", "")).strip()
    version = str(method_information.get("Version", "")).strip()

    if context.addon.methods and not method_id:
        issues.add(
            ValidationIssue(
                code="method-linkage-id-missing",
                message="MethodInformation.Id is required when addon methods are defined.",
                path="MethodInformation.Id",
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
            )
        )
    if not version:
        issues.add(
            ValidationIssue(
                code="method-linkage-version-missing",
                message="MethodInformation.Version is missing.",
                path="MethodInformation.Version",
                severity=IssueSeverity.WARNING,
                source=IssueSource.VALIDATION,
            )
        )

    if context.addon.methods and method_id:
        allowed = {str(method.method_id) for method in context.addon.methods if method.method_id > 0}
        if allowed and method_id not in allowed:
            issues.add(
                ValidationIssue(
                    code="method-linkage-mismatch",
                    message=f"MethodInformation.Id '{method_id}' does not match addon methods {sorted(allowed)}.",
                    path="MethodInformation.Id",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.VALIDATION,
                    entity_keys=tuple(method.key for method in context.addon.methods),
                )
            )


def _validate_assay_refs(
    context: ProtocolContextModel,
    protocol_payload: dict[str, Any],
    issues: ValidationIssueCollection,
) -> None:
    assay_information = protocol_payload.get("AssayInformation", [])
    if not isinstance(assay_information, list):
        issues.add(
            ValidationIssue(
                code="assay-information-invalid",
                message="AssayInformation must be an array.",
                path="AssayInformation",
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
            )
        )
        return

    known_assays = {assay.name.strip().casefold(): assay for assay in context.addon.assays if assay.name.strip()}
    for index, assay_record in enumerate(assay_information):
        if not isinstance(assay_record, dict):
            issues.add(
                ValidationIssue(
                    code="assay-record-invalid",
                    message="AssayInformation entry must be an object.",
                    path=f"AssayInformation[{index}]",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.VALIDATION,
                )
            )
            continue

        assay_type = str(assay_record.get("Type", "")).strip()
        if not assay_type:
            issues.add(
                ValidationIssue(
                    code="assay-type-missing",
                    message="AssayInformation entry is missing Type.",
                    path=f"AssayInformation[{index}].Type",
                    severity=IssueSeverity.WARNING,
                    source=IssueSource.VALIDATION,
                )
            )
            continue

        normalized = assay_type.casefold()
        if normalized not in known_assays:
            issues.add(
                ValidationIssue(
                    code="broken-assay-reference",
                    message=f"AssayInformation.Type '{assay_type}' has no matching addon assay.",
                    path=f"AssayInformation[{index}].Type",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.VALIDATION,
                )
            )


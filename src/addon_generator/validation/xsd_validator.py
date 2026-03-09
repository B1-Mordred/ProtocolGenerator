from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection


@dataclass(slots=True)
class XsdValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_xml_against_xsd(xml_content: str, xsd_path: Path | str) -> XsdValidationResult:
    """Validate XML content against an XSD and return structured issues."""

    issues = ValidationIssueCollection()
    schema_path = Path(xsd_path)

    if not schema_path.exists():
        issues.add(
            ValidationIssue(
                code="xsd-not-found",
                message=f"XSD file not found: {schema_path}",
                path=str(schema_path),
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
            )
        )
        return XsdValidationResult(is_valid=False, issues=issues)

    try:
        from lxml import etree
    except ImportError:
        issues.add(
            ValidationIssue(
                code="xsd-validation-unavailable",
                message="lxml is not installed; skipped XSD validation.",
                path=str(schema_path),
                severity=IssueSeverity.WARNING,
                source=IssueSource.VALIDATION,
            )
        )
        return XsdValidationResult(is_valid=True, issues=issues)

    try:
        schema_doc = etree.parse(str(schema_path))
        schema = etree.XMLSchema(schema_doc)
    except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
        issues.add(
            ValidationIssue(
                code="xsd-load-failed",
                message=f"Failed to load XSD: {exc}",
                path=str(schema_path),
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
            )
        )
        return XsdValidationResult(is_valid=False, issues=issues)

    try:
        xml_doc = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        issues.add(
            ValidationIssue(
                code="xml-parse-failed",
                message=f"Generated XML is invalid: {exc}",
                path="/",
                severity=IssueSeverity.ERROR,
                source=IssueSource.VALIDATION,
                source_location=f"line {exc.lineno}, column {exc.offset}",
            )
        )
        return XsdValidationResult(is_valid=False, issues=issues)

    is_valid = schema.validate(xml_doc)
    for entry in schema.error_log:
        severity = IssueSeverity.ERROR if entry.level_name in {"ERROR", "FATAL"} else IssueSeverity.WARNING
        issues.add(
            ValidationIssue(
                code="xsd-validation",
                message=entry.message,
                path="/",
                severity=severity,
                source=IssueSource.VALIDATION,
                source_location=f"line {entry.line}, column {entry.column}",
            )
        )

    return XsdValidationResult(is_valid=is_valid and not issues.has_errors(), issues=issues)

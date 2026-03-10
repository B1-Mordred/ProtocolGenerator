from __future__ import annotations

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue
from addon_generator.services.generation_service import GenerationResult
from addon_generator.ui.services.validation_service import ValidationService


class _Builder:
    def build(self, merged_bundle):
        return object()


class _GenerationService:
    def __init__(self, issues, warnings):
        self._issues = issues
        self._warnings = warnings

    def generate_all(self, addon, *, dto_bundle=None):
        return GenerationResult(
            addon_model=object(),
            protocol_json={},
            analytes_xml_string="<xml/>",
            issues=self._issues,
            warnings=self._warnings,
            resolved_mapping_snapshot={},
            merge_report={},
            unresolved_required_fields=[],
            conflicting_required_fields=[],
        )


def test_validation_service_assigns_required_categories_and_navigation_targets() -> None:
    issues = [
        ValidationIssue(code="workbook-open-failed", message="Workbook failed", path="workbook", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION),
        ValidationIssue(code="missing-method-id", message="Missing method", path="method.method_id", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN),
        ValidationIssue(code="assay-cross-file-mismatch", message="Cross file mismatch", path="assays[A1]", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION),
        ValidationIssue(code="schema-missing", message="Schema missing", path="protocol.schema", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION),
        ValidationIssue(code="projection-failed", message="Projection error", path="payload", severity=IssueSeverity.ERROR, source=IssueSource.PROJECTION),
    ]
    warnings = [
        ValidationIssue(code="missing-display", message="Display missing", path="method.display_name", severity=IssueSeverity.WARNING, source=IssueSource.DOMAIN),
        ValidationIssue(code="note", message="FYI", path="method", severity=IssueSeverity.INFO, source=IssueSource.DOMAIN),
    ]
    service = ValidationService()
    service._builder = _Builder()
    service._service = _GenerationService(issues, warnings)

    _addon, summary = service.validate(merged_bundle=object())

    assert summary.category_counts["Import Issues"] == 1
    assert summary.category_counts["Domain Validation"] == 1
    assert summary.category_counts["Cross-file Validation"] == 1
    assert summary.category_counts["Schema/XSD Validation"] == 1
    assert summary.category_counts["Export Blockers"] == 1
    assert summary.category_counts["Warnings"] == 1
    assert summary.category_counts["Info"] == 1
    assert summary.grouped_issues["Domain Validation"][0].navigation_target == {"section_index": 0, "entity": "method", "path": "method.method_id"}


def test_validation_service_derives_severity_counts_and_export_blocking() -> None:
    service = ValidationService()
    service._builder = _Builder()
    service._service = _GenerationService(
        issues=[ValidationIssue(code="missing-method-id", message="Missing method", path="method.method_id", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN)],
        warnings=[ValidationIssue(code="note", message="Warn", path="method", severity=IssueSeverity.WARNING, source=IssueSource.DOMAIN)],
    )

    _addon, summary = service.validate(merged_bundle=object())

    assert summary.severity_counts == {"error": 1, "warning": 1, "info": 0}
    assert summary.export_blocked is True

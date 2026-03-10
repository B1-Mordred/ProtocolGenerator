from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from addon_generator.domain.issues import IssueSource, ValidationIssue
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService
from addon_generator.ui.models.issue_view_model import IssueViewModel


@dataclass(slots=True)
class ValidationSummary:
    issues: list[IssueViewModel]
    grouped_issues: dict[str, list[IssueViewModel]]
    severity_counts: dict[str, int]
    category_counts: dict[str, int]
    export_blocked: bool


class ValidationService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def validate(self, merged_bundle: InputDTOBundle) -> tuple[object, ValidationSummary]:
        addon = self._builder.build(merged_bundle)
        result = self._service.generate_all(addon, dto_bundle=merged_bundle)
        issues = [self._to_issue_view_model(issue) for issue in result.issues + result.warnings]

        grouped_issues: dict[str, list[IssueViewModel]] = defaultdict(list)
        severity_counts = {"error": 0, "warning": 0, "info": 0}
        category_counts: dict[str, int] = {}
        for issue in issues:
            grouped_issues[issue.category].append(issue)
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        export_blocked = severity_counts.get("error", 0) > 0
        summary = ValidationSummary(
            issues=issues,
            grouped_issues=dict(grouped_issues),
            severity_counts=severity_counts,
            category_counts=category_counts,
            export_blocked=export_blocked,
        )
        return addon, summary

    def _to_issue_view_model(self, issue: ValidationIssue) -> IssueViewModel:
        return IssueViewModel(
            code=issue.code,
            severity=issue.severity.value,
            summary=issue.message,
            section="Validation",
            category=self._classify_category(issue),
            entity_context="/".join(issue.entity_keys) or issue.path,
            provenance=issue.source_location or "",
            recommended_action=self._recommended_action(issue),
            navigation_target=self._navigation_target(issue),
        )

    def _classify_category(self, issue: ValidationIssue) -> str:
        severity = issue.severity.value
        if severity == "warning":
            return "Warnings"
        if severity == "info":
            return "Info"
        if self._is_import_issue(issue):
            return "Import Issues"
        if self._is_cross_file_issue(issue):
            return "Cross-file Validation"
        if self._is_schema_or_xsd_issue(issue):
            return "Schema/XSD Validation"
        if issue.source == IssueSource.DOMAIN:
            return "Domain Validation"
        return "Export Blockers"

    def _is_import_issue(self, issue: ValidationIssue) -> bool:
        tokens = f"{issue.code} {issue.path} {issue.message}".lower()
        return any(token in tokens for token in ("workbook", "excel", "import", "duplicate-row", "sheet"))

    def _is_cross_file_issue(self, issue: ValidationIssue) -> bool:
        tokens = f"{issue.code} {issue.path} {issue.message}".lower()
        return "cross-file" in tokens or issue.code in {
            "broken-assay-ref",
            "broken-analyte-ref",
            "duplicate-analyte-unit-id",
            "invalid-assay-ref",
            "invalid-analyte-ref",
            "invalid-analyte-unit-id",
        }

    def _is_schema_or_xsd_issue(self, issue: ValidationIssue) -> bool:
        tokens = f"{issue.code} {issue.path} {issue.message}".lower()
        return any(token in tokens for token in ("schema", "xsd", "xml", "jsonschema"))

    def _recommended_action(self, issue: ValidationIssue) -> str | None:
        details = issue.details or {}
        action = details.get("recommended_action")
        if action:
            return str(action)
        if issue.severity.value == "error":
            return "Fix this issue before export and run validation again."
        return None

    def _navigation_target(self, issue: ValidationIssue) -> dict[str, object]:
        path = issue.path.lower()
        section_index = 6
        entity = "/".join(issue.entity_keys) or issue.path
        if "method" in path:
            section_index = 0
            entity = "method"
        elif "assay" in path:
            section_index = 1
            entity = "assay"
        elif "analyte" in path:
            section_index = 2
            entity = "analyte"
        elif "sample" in path or "prep" in path:
            section_index = 3
            entity = "sample_prep"
        elif "dilution" in path:
            section_index = 4
            entity = "dilution"
        return {"section_index": section_index, "entity": entity, "path": issue.path}

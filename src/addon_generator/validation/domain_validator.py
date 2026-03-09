from __future__ import annotations

from dataclasses import dataclass

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import ProtocolContextModel


@dataclass(slots=True)
class DomainValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_domain_context(context: ProtocolContextModel) -> DomainValidationResult:
    """Validate canonical addon domain invariants.

    Hard failures (11.1):
    - duplicate method/assay/analyte/unit ids
    - broken assay/analyte references against indices when supplied
    - non-unique cross-match labels

    Warnings (11.2):
    - empty display labels
    - analytes without units
    """

    issues = ValidationIssueCollection()

    _check_duplicate_ids(context, issues)
    _check_reference_integrity(context, issues)
    _check_cross_match_uniqueness(context, issues)
    _check_quality_warnings(context, issues)

    return DomainValidationResult(is_valid=not issues.has_errors(), issues=issues)


def _check_duplicate_ids(context: ProtocolContextModel, issues: ValidationIssueCollection) -> None:
    _duplicate_scan(
        [(m.key, m.method_id) for m in context.addon.methods],
        entity="method",
        id_field="method_id",
        issues=issues,
    )
    _duplicate_scan(
        [(a.key, a.assay_id) for a in context.addon.assays],
        entity="assay",
        id_field="assay_id",
        issues=issues,
    )
    analytes = []
    for assay in context.addon.assays:
        analytes.extend((analyte.key, analyte.analyte_id) for analyte in assay.analytes)
    _duplicate_scan(analytes, entity="analyte", id_field="analyte_id", issues=issues)


def _duplicate_scan(
    key_and_ids: list[tuple[str, int]],
    *,
    entity: str,
    id_field: str,
    issues: ValidationIssueCollection,
) -> None:
    seen: dict[int, str] = {}
    for key, numeric_id in key_and_ids:
        if numeric_id <= 0:
            continue
        if numeric_id in seen:
            issues.add(
                ValidationIssue(
                    code="duplicate-id",
                    message=f"Duplicate {entity} {id_field}={numeric_id} conflicts with {seen[numeric_id]}.",
                    path=f"addon.{entity}s",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.DOMAIN,
                    entity_keys=(seen[numeric_id], key),
                )
            )
        else:
            seen[numeric_id] = key


def _check_reference_integrity(context: ProtocolContextModel, issues: ValidationIssueCollection) -> None:
    if context.assay_index:
        for assay in context.addon.assays:
            if assay.key not in context.assay_index:
                issues.add(
                    ValidationIssue(
                        code="broken-assay-reference",
                        message="Assay appears in addon list but not in assay_index.",
                        path="context.assay_index",
                        severity=IssueSeverity.ERROR,
                        source=IssueSource.DOMAIN,
                        entity_keys=(assay.key,),
                    )
                )

    if context.analyte_index:
        for assay in context.addon.assays:
            for analyte in assay.analytes:
                if analyte.key not in context.analyte_index:
                    issues.add(
                        ValidationIssue(
                            code="broken-analyte-reference",
                            message="Analyte appears under assay but not in analyte_index.",
                            path=f"addon.assays[{assay.key}].analytes",
                            severity=IssueSeverity.ERROR,
                            source=IssueSource.DOMAIN,
                            entity_keys=(assay.key, analyte.key),
                        )
                    )


def _check_cross_match_uniqueness(context: ProtocolContextModel, issues: ValidationIssueCollection) -> None:
    _label_uniqueness(
        [(method.key, method.display_name) for method in context.addon.methods],
        entity="method",
        issues=issues,
    )
    _label_uniqueness(
        [(assay.key, assay.name) for assay in context.addon.assays],
        entity="assay",
        issues=issues,
    )

    analyte_pairs: list[tuple[str, str]] = []
    for assay in context.addon.assays:
        analyte_pairs.extend((analyte.key, analyte.name) for analyte in assay.analytes)
    _label_uniqueness(analyte_pairs, entity="analyte", issues=issues)


def _label_uniqueness(items: list[tuple[str, str]], *, entity: str, issues: ValidationIssueCollection) -> None:
    seen: dict[str, str] = {}
    for key, label in items:
        normalized = " ".join(label.split()).casefold()
        if not normalized:
            continue
        if normalized in seen:
            issues.add(
                ValidationIssue(
                    code="non-unique-cross-match-field",
                    message=f"Non-unique {entity} match label '{label}'.",
                    path=f"addon.{entity}s",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.DOMAIN,
                    entity_keys=(seen[normalized], key),
                )
            )
        else:
            seen[normalized] = key


def _check_quality_warnings(context: ProtocolContextModel, issues: ValidationIssueCollection) -> None:
    for method in context.addon.methods:
        if not method.display_name.strip():
            issues.add(
                ValidationIssue(
                    code="missing-method-display-name",
                    message="Method display name is empty.",
                    path="addon.methods",
                    severity=IssueSeverity.WARNING,
                    source=IssueSource.DOMAIN,
                    entity_keys=(method.key,),
                )
            )

    for assay in context.addon.assays:
        if not assay.name.strip():
            issues.add(
                ValidationIssue(
                    code="missing-assay-name",
                    message="Assay name is empty.",
                    path="addon.assays",
                    severity=IssueSeverity.WARNING,
                    source=IssueSource.DOMAIN,
                    entity_keys=(assay.key,),
                )
            )

        for analyte in assay.analytes:
            if not analyte.name.strip():
                issues.add(
                    ValidationIssue(
                        code="missing-analyte-name",
                        message="Analyte name is empty.",
                        path=f"addon.assays[{assay.key}].analytes",
                        severity=IssueSeverity.WARNING,
                        source=IssueSource.DOMAIN,
                        entity_keys=(assay.key, analyte.key),
                    )
                )
            if not analyte.units:
                issues.add(
                    ValidationIssue(
                        code="analyte-without-units",
                        message="Analyte has no declared units.",
                        path=f"addon.assays[{assay.key}].analytes",
                        severity=IssueSeverity.WARNING,
                        source=IssueSource.DOMAIN,
                        entity_keys=(assay.key, analyte.key),
                    )
                )

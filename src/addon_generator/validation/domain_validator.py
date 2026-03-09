from __future__ import annotations

from dataclasses import dataclass

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import AddonModel


@dataclass(slots=True)
class DomainValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_domain(addon: AddonModel) -> DomainValidationResult:
    issues = ValidationIssueCollection()

    if addon.method is None:
        issues.add(ValidationIssue(code="missing-method", message="Method is required", path="method", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
    else:
        if not addon.method.method_id.strip():
            issues.add(ValidationIssue(code="missing-method-id", message="method.method_id is required", path="method.method_id", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
        if not addon.method.method_version.strip():
            issues.add(ValidationIssue(code="missing-method-version", message="method.method_version is required", path="method.method_version", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
        if not (addon.method.display_name or "").strip():
            issues.add(ValidationIssue(code="missing-method-display", message="method.display_name is optional but empty", path="method.display_name", severity=IssueSeverity.WARNING, source=IssueSource.DOMAIN))

    assay_keys = {a.key for a in addon.assays}
    if len(assay_keys) != len(addon.assays):
        issues.add(ValidationIssue(code="duplicate-assay-keys", message="Assay keys must be unique", path="assays", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
    if len({a.xml_id for a in addon.assays if a.xml_id is not None}) != len([a for a in addon.assays if a.xml_id is not None]):
        issues.add(ValidationIssue(code="duplicate-assay-xml-ids", message="Assay xml_id values must be unique", path="assays", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_keys = {a.key for a in addon.analytes}
    if len(analyte_keys) != len(addon.analytes):
        issues.add(ValidationIssue(code="duplicate-analyte-keys", message="Analyte keys must be unique", path="analytes", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    for analyte in addon.analytes:
        if not analyte.name.strip():
            issues.add(ValidationIssue(code="empty-analyte-name", message="Analyte name must be non-empty", path=f"analytes[{analyte.key}]", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
        if analyte.assay_key not in assay_keys:
            issues.add(ValidationIssue(code="unknown-assay-key", message=f"Analyte references missing assay key '{analyte.assay_key}'", path=f"analytes[{analyte.key}].assay_key", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    unit_keys = {u.key for u in addon.units}
    if len(unit_keys) != len(addon.units):
        issues.add(ValidationIssue(code="duplicate-unit-keys", message="Unit keys must be unique", path="units", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_key_set = {a.key for a in addon.analytes}
    for unit in addon.units:
        if unit.analyte_key not in analyte_key_set:
            issues.add(ValidationIssue(code="unknown-analyte-key", message=f"Unit references missing analyte key '{unit.analyte_key}'", path=f"units[{unit.key}].analyte_key", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    return DomainValidationResult(is_valid=not issues.has_errors(), issues=issues)

from __future__ import annotations

from dataclasses import dataclass

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import AddonModel
from addon_generator.mapping.normalizers import normalize_for_matching


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
        elif not any(ch.isdigit() for ch in addon.method.method_version):
            issues.add(ValidationIssue(code="invalid-method-version-format", message="method.method_version must include at least one numeric character", path="method.method_version", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
        if not (addon.method.display_name or "").strip():
            issues.add(ValidationIssue(code="missing-method-display", message="method.display_name is optional but empty", path="method.display_name", severity=IssueSeverity.WARNING, source=IssueSource.DOMAIN))

    if not addon.assays:
        issues.add(ValidationIssue(code="empty-assay-list", message="At least one assay is required", path="assays", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    assay_keys = {a.key for a in addon.assays}
    if len(assay_keys) != len(addon.assays):
        issues.add(ValidationIssue(code="duplicate-assay-keys", message="Assay keys must be unique", path="assays", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
    if len({a.xml_id for a in addon.assays if a.xml_id is not None}) != len([a for a in addon.assays if a.xml_id is not None]):
        issues.add(ValidationIssue(code="duplicate-assay-xml-ids", message="Assay xml_id values must be unique", path="assays", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_counts_by_assay: dict[str, int] = {assay.key: 0 for assay in addon.assays}
    for analyte in addon.analytes:
        if analyte.assay_key in analyte_counts_by_assay:
            analyte_counts_by_assay[analyte.assay_key] += 1
    for assay_key, analyte_count in analyte_counts_by_assay.items():
        if analyte_count == 0:
            issues.add(ValidationIssue(code="assay-missing-analytes", message=f"Assay '{assay_key}' must include at least one analyte", path=f"assays[{assay_key}]", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_keys = {a.key for a in addon.analytes}
    if len(analyte_keys) != len(addon.analytes):
        issues.add(ValidationIssue(code="duplicate-analyte-keys", message="Analyte keys must be unique", path="analytes", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_assay_by_name: dict[str, set[str]] = {}
    for analyte in addon.analytes:
        if not analyte.name.strip():
            issues.add(ValidationIssue(code="empty-analyte-name", message="Analyte name must be non-empty", path=f"analytes[{analyte.key}]", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
        if analyte.assay_key not in assay_keys:
            issues.add(ValidationIssue(code="unknown-assay-key", message=f"Analyte references missing assay key '{analyte.assay_key}'", path=f"analytes[{analyte.key}].assay_key", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
            continue

        canonical_name = normalize_for_matching(analyte.name)
        if canonical_name:
            analyte_assay_by_name.setdefault(canonical_name, set()).add(analyte.assay_key)

        linked_assay = next((assay for assay in addon.assays if assay.key == analyte.assay_key), None)
        if linked_assay is not None and analyte.assay_information_type and linked_assay.protocol_type:
            if normalize_for_matching(analyte.assay_information_type) != normalize_for_matching(linked_assay.protocol_type):
                issues.add(ValidationIssue(code="unsupported-analyte-assay-information-type", message=f"Analyte assay_information_type '{analyte.assay_information_type}' is incompatible with assay protocol_type '{linked_assay.protocol_type}'", path=f"analytes[{analyte.key}].assay_information_type", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))


    for analyte_name, linked_assays in sorted(analyte_assay_by_name.items()):
        if len(linked_assays) > 1:
            issues.add(
                ValidationIssue(
                    code="ambiguous-analyte-assay-linkage",
                    message=f"Analyte '{analyte_name}' is linked to multiple assays: {sorted(linked_assays)}",
                    path="analytes",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.DOMAIN,
                )
            )

    unit_keys = {u.key for u in addon.units}
    if len(unit_keys) != len(addon.units):
        issues.add(ValidationIssue(code="duplicate-unit-keys", message="Unit keys must be unique", path="units", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    analyte_key_set = {a.key for a in addon.analytes}
    analyte_units_count: dict[str, int] = {a.key: 0 for a in addon.analytes}
    for unit in addon.units:
        if unit.analyte_key not in analyte_key_set:
            issues.add(ValidationIssue(code="unknown-analyte-key", message=f"Unit references missing analyte key '{unit.analyte_key}'", path=f"units[{unit.key}].analyte_key", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
            continue
        analyte_units_count[unit.analyte_key] = analyte_units_count.get(unit.analyte_key, 0) + 1

    for analyte in addon.analytes:
        if analyte_units_count.get(analyte.key, 0) == 0:
            issues.add(ValidationIssue(code="missing-analyte-units", message=f"Analyte '{analyte.key}' must have at least one unit", path=f"analytes[{analyte.key}].unit_keys", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))

    normalized_aliases: dict[str, str] = {}
    for assay in addon.assays:
        all_aliases = [assay.key, *assay.aliases]
        for alias in all_aliases:
            canonical_alias = alias.strip().casefold()
            if not canonical_alias:
                continue
            owner = normalized_aliases.get(canonical_alias)
            if owner is not None and owner != assay.key:
                issues.add(ValidationIssue(code="ambiguous-assay-alias", message=f"Alias '{alias}' maps to multiple assays ('{owner}', '{assay.key}')", path=f"assays[{assay.key}].aliases", severity=IssueSeverity.ERROR, source=IssueSource.DOMAIN))
            else:
                normalized_aliases[canonical_alias] = assay.key

    return DomainValidationResult(is_valid=not issues.has_errors(), issues=issues)

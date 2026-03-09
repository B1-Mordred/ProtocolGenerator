from __future__ import annotations

from dataclasses import dataclass

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.mapping.normalizers import normalize_for_matching


@dataclass(slots=True)
class DTOValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_dto_bundle(bundle: InputDTOBundle | None) -> DTOValidationResult:
    issues = ValidationIssueCollection()
    if bundle is None:
        return DTOValidationResult(is_valid=True, issues=issues)

    analyte_scopes: dict[str, set[str]] = {}
    for analyte in bundle.analytes:
        canonical = normalize_for_matching(analyte.name)
        if not canonical:
            continue
        analyte_scopes.setdefault(canonical, set()).add(analyte.assay_key)
    for analyte_name, scopes in sorted(analyte_scopes.items()):
        if len(scopes) > 1:
            issues.add(
                _issue(
                    bundle,
                    code="duplicate-analyte-incompatible-scope",
                    message=f"Analyte '{analyte_name}' appears in incompatible assay scopes: {sorted(scopes)}",
                    path="analytes",
                    entity_keys=tuple(sorted(scopes)),
                    provenance_key="analytes.name",
                )
            )

    assay_keys = {assay.key for assay in bundle.assays}
    for analyte in bundle.analytes:
        if analyte.assay_information_type and analyte.assay_information_type.strip() and analyte.assay_key not in assay_keys:
            issues.add(
                _issue(
                    bundle,
                    code="unresolved-parameter-set-assay-link",
                    message=f"Analyte '{analyte.key}' Parameter Set cannot resolve to assay '{analyte.assay_key}'",
                    path=f"analytes[{analyte.key}].assay_key",
                    entity_keys=(analyte.key, analyte.assay_key),
                    provenance_key="analytes.assay_key",
                )
            )

    hidden_actions = {normalize_for_matching(v) for v in bundle.hidden_vocab.get("SamplePrepAction", []) if str(v).strip()}
    for step in bundle.sample_prep_steps:
        action = (step.label or step.metadata.get("raw_action") or "").strip()
        if not action:
            continue
        if hidden_actions and normalize_for_matching(action) not in hidden_actions:
            issues.add(
                _issue(
                    bundle,
                    code="unsupported-sample-prep-action",
                    message=f"Sample prep action '{action}' is not in hidden vocabulary",
                    path=f"sample_prep_steps[{step.key}].label",
                    entity_keys=(step.key,),
                    provenance_key="sample_prep.action",
                )
            )

    for scheme in bundle.dilution_schemes:
        ratio = str(scheme.metadata.get("ratio") or "").strip()
        if not ratio:
            issues.add(
                _issue(
                    bundle,
                    code="missing-dilution-ratio",
                    message=f"Dilution scheme '{scheme.key}' is missing ratio",
                    path=f"dilution_schemes[{scheme.key}].ratio",
                    entity_keys=(scheme.key,),
                    provenance_key="dilutions.ratio",
                )
            )
            continue
        parts = ratio.split(":")
        if len(parts) != 2 or not all(part.strip().isdigit() for part in parts):
            issues.add(
                _issue(
                    bundle,
                    code="malformed-dilution-scheme",
                    message=f"Dilution ratio '{ratio}' must match N:N",
                    path=f"dilution_schemes[{scheme.key}].ratio",
                    entity_keys=(scheme.key,),
                    provenance_key="dilutions.ratio",
                )
            )
            continue
        left, right = (int(parts[0]), int(parts[1]))
        if left <= 0 or right <= 0:
            issues.add(
                _issue(
                    bundle,
                    code="invalid-dilution-ratio",
                    message=f"Dilution ratio '{ratio}' must be positive integers",
                    path=f"dilution_schemes[{scheme.key}].ratio",
                    entity_keys=(scheme.key,),
                    provenance_key="dilutions.ratio",
                )
            )

    return DTOValidationResult(is_valid=not issues.has_errors(), issues=issues)


def _issue(
    bundle: InputDTOBundle,
    *,
    code: str,
    message: str,
    path: str,
    entity_keys: tuple[str, ...],
    provenance_key: str,
) -> ValidationIssue:
    prov = _first_provenance(bundle.provenance.get(provenance_key, []))
    return ValidationIssue(
        code=code,
        message=message,
        path=path,
        severity=IssueSeverity.ERROR,
        source=IssueSource.VALIDATION,
        entity_keys=entity_keys,
        source_location=prov,
    )


def _first_provenance(records: list[FieldProvenance]) -> str | None:
    if not records:
        return None
    p = records[0]
    bits = [p.source_file or p.source_type]
    if p.source_sheet:
        bits.append(p.source_sheet)
    if p.row is not None:
        bits.append(f"row={p.row}")
    if p.column:
        bits.append(f"col={p.column}")
    return ":".join(bits)

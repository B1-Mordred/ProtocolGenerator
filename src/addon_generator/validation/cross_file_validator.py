from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection


@dataclass(slots=True)
class CrossFileValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def _issue(code: str, message: str, path: str, *, entity_keys: tuple[str, ...] = (), source_location: str | None = None) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        path=path,
        severity=IssueSeverity.ERROR,
        source=IssueSource.VALIDATION,
        entity_keys=entity_keys,
        source_location=source_location,
    )


def validate_cross_file_consistency(protocol_json: dict[str, Any], analytes_xml_root: Any) -> CrossFileValidationResult:
    issues = ValidationIssueCollection()

    xml_method_id = analytes_xml_root.findtext("MethodId") or ""
    xml_method_version = analytes_xml_root.findtext("MethodVersion") or ""
    protocol_method = protocol_json.get("MethodInformation", {})
    protocol_method_id = str(protocol_method.get("Id") or "")
    protocol_method_version = str(protocol_method.get("Version") or "")

    if xml_method_id != protocol_method_id:
        issues.add(_issue("method-id-mismatch", "Analytes.xml MethodId differs from protocol MethodInformation.Id", "MethodInformation.Id", entity_keys=(xml_method_id, protocol_method_id), source_location="AddOn/MethodId"))
    if xml_method_version != protocol_method_version:
        issues.add(_issue("method-version-mismatch", "Analytes.xml MethodVersion differs from protocol MethodInformation.Version", "MethodInformation.Version", entity_keys=(xml_method_version, protocol_method_version), source_location="AddOn/MethodVersion"))
    if not xml_method_id or not xml_method_version:
        issues.add(_issue("missing-method-identity", "Analytes.xml must define non-empty MethodId and MethodVersion", "AddOn", source_location="AddOn"))

    if not protocol_method_id or not protocol_method_version:
        issues.add(_issue("missing-merged-method-identity", "Merged protocol must define non-empty MethodInformation.Id and MethodInformation.Version", "MethodInformation", source_location="ProtocolFile.json/MethodInformation"))

    def _parse_int(value: str | None, *, path: str, code: str) -> int | None:
        if value is None or value == "":
            issues.add(ValidationIssue(code=code, message=f"Missing integer value at {path}", path=path, severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))
            return None
        try:
            return int(value)
        except ValueError:
            issues.add(ValidationIssue(code=code, message=f"Invalid integer '{value}' at {path}", path=path, severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))
            return None

    assay_ids: set[int] = set()
    duplicate_assay_ids: set[int] = set()
    for idx, node in enumerate(analytes_xml_root.findall("./Assays/Assay")):
        assay_id = _parse_int(node.findtext("Id"), path=f"Assays.Assay[{idx}].Id", code="invalid-assay-id")
        if assay_id is None:
            continue
        if assay_id in assay_ids:
            duplicate_assay_ids.add(assay_id)
        assay_ids.add(assay_id)
    for assay_id in sorted(duplicate_assay_ids):
        issues.add(ValidationIssue(code="duplicate-assay-id", message=f"Duplicate assay Id detected: {assay_id}", path="Assays.Assay.Id", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    analyte_ids: set[int] = set()
    duplicate_analyte_ids: set[int] = set()
    for idx, analyte in enumerate(analytes_xml_root.findall("./Assays/Assay/Analytes/Analyte")):
        analyte_id = _parse_int(analyte.findtext("Id"), path=f"Analyte[{idx}].Id", code="invalid-analyte-id")
        if analyte_id is not None:
            if analyte_id in analyte_ids:
                duplicate_analyte_ids.add(analyte_id)
            analyte_ids.add(analyte_id)

        assay_ref = _parse_int(analyte.findtext("AssayRef"), path=f"Analyte[{idx}].AssayRef", code="invalid-assay-ref")
        if assay_ref is not None and assay_ref not in assay_ids:
            issues.add(ValidationIssue(code="broken-assay-ref", message=f"Analyte AssayRef {assay_ref} does not exist", path="Analyte.AssayRef", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))
    for analyte_id in sorted(duplicate_analyte_ids):
        issues.add(ValidationIssue(code="duplicate-analyte-id", message=f"Duplicate analyte Id detected: {analyte_id}", path="Analyte.Id", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    unit_ids: set[int] = set()
    duplicate_unit_ids: set[int] = set()
    for idx, unit in enumerate(analytes_xml_root.findall("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit")):
        unit_id = _parse_int(unit.findtext("Id"), path=f"AnalyteUnit[{idx}].Id", code="invalid-analyte-unit-id")
        if unit_id is not None:
            if unit_id in unit_ids:
                duplicate_unit_ids.add(unit_id)
            unit_ids.add(unit_id)
        analyte_ref = _parse_int(unit.findtext("AnalyteRef"), path=f"AnalyteUnit[{idx}].AnalyteRef", code="invalid-analyte-ref")
        if analyte_ref is None:
            continue
        if analyte_ref not in analyte_ids:
            issues.add(ValidationIssue(code="broken-analyte-ref", message=f"AnalyteUnit AnalyteRef {analyte_ref} does not exist", path="AnalyteUnit.AnalyteRef", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))
    for unit_id in sorted(duplicate_unit_ids):
        issues.add(ValidationIssue(code="duplicate-analyte-unit-id", message=f"Duplicate analyte unit Id detected: {unit_id}", path="AnalyteUnit.Id", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    protocol_assays = protocol_json.get("AssayInformation", [])
    protocol_types = {str(item.get("Type") or "").strip().casefold() for item in protocol_assays if isinstance(item, dict)}
    xml_assay_names = {str(node.findtext("Name") or "").strip().casefold() for node in analytes_xml_root.findall("./Assays/Assay")}
    for assay_name in sorted(name for name in xml_assay_names if name):
        if assay_name not in protocol_types:
            issues.add(_issue("cross-file-assay-mismatch", f"Assay '{assay_name}' exists in Analytes.xml but not in protocol AssayInformation", "AssayInformation", entity_keys=(assay_name,), source_location="AddOn/Assays/Assay/Name"))

    return CrossFileValidationResult(is_valid=not issues.has_errors(), issues=issues)

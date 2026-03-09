from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue, ValidationIssueCollection


@dataclass(slots=True)
class CrossFileValidationResult:
    is_valid: bool
    issues: ValidationIssueCollection


def validate_cross_file_consistency(protocol_json: dict[str, Any], analytes_xml_root: Any) -> CrossFileValidationResult:
    issues = ValidationIssueCollection()

    xml_method_id = analytes_xml_root.findtext("MethodId") or ""
    xml_method_version = analytes_xml_root.findtext("MethodVersion") or ""
    protocol_method = protocol_json.get("MethodInformation", {})
    protocol_method_id = str(protocol_method.get("Id") or "")
    protocol_method_version = str(protocol_method.get("Version") or "")

    if xml_method_id != protocol_method_id:
        issues.add(ValidationIssue(code="method-id-mismatch", message="Analytes.xml MethodId differs from protocol MethodInformation.Id", path="MethodInformation.Id", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))
    if xml_method_version != protocol_method_version:
        issues.add(ValidationIssue(code="method-version-mismatch", message="Analytes.xml MethodVersion differs from protocol MethodInformation.Version", path="MethodInformation.Version", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    assay_ids = {int(node.findtext("Id") or 0) for node in analytes_xml_root.findall("./Assays/Assay")}
    analyte_ids: set[int] = set()
    for analyte in analytes_xml_root.findall("./Assays/Assay/Analytes/Analyte"):
        analyte_id = int(analyte.findtext("Id") or 0)
        analyte_ids.add(analyte_id)
        assay_ref = int(analyte.findtext("AssayRef") or -1)
        if assay_ref not in assay_ids:
            issues.add(ValidationIssue(code="broken-assay-ref", message=f"Analyte AssayRef {assay_ref} does not exist", path="Analyte.AssayRef", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    for unit in analytes_xml_root.findall("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit"):
        analyte_ref = int(unit.findtext("AnalyteRef") or -1)
        if analyte_ref not in analyte_ids:
            issues.add(ValidationIssue(code="broken-analyte-ref", message=f"AnalyteUnit AnalyteRef {analyte_ref} does not exist", path="AnalyteUnit.AnalyteRef", severity=IssueSeverity.ERROR, source=IssueSource.VALIDATION))

    return CrossFileValidationResult(is_valid=not issues.has_errors(), issues=issues)

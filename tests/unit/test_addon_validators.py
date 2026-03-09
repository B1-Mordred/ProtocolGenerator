from __future__ import annotations

from pathlib import Path

import pytest

from addon_generator.domain.issues import IssueSeverity
from addon_generator.domain.models import AddonModel, AnalyteModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain_context
from addon_generator.validation.protocol_schema_validator import validate_protocol_schema
from addon_generator.validation.xsd_validator import validate_xml_against_xsd


def test_domain_validator_reports_hard_failures_and_warnings() -> None:
    context = ProtocolContextModel(
        addon=AddonModel(
            methods=[
                MethodModel(key="method:a", method_id=1, display_name="Chemistry"),
                MethodModel(key="method:b", method_id=1, display_name="chemistry"),
            ],
            assays=[
                AssayModel(
                    key="assay:a",
                    assay_id=20,
                    name="Panel A",
                    analytes=[AnalyteModel(key="analyte:a", analyte_id=3, name="Glucose", units=[])],
                ),
                AssayModel(
                    key="assay:b",
                    assay_id=20,
                    name="Panel a",
                    analytes=[AnalyteModel(key="analyte:b", analyte_id=3, name="glucose", units=[])],
                ),
            ],
        ),
        assay_index={"assay:a": AssayModel(key="assay:a")},
        analyte_index={"analyte:a": AnalyteModel(key="analyte:a")},
    )

    result = validate_domain_context(context)

    assert result.is_valid is False
    codes = {issue.code for issue in result.issues.issues}
    assert "duplicate-id" in codes
    assert "broken-assay-reference" in codes
    assert "broken-analyte-reference" in codes
    assert "non-unique-cross-match-field" in codes
    assert "analyte-without-units" in codes


def test_protocol_schema_validator_collects_jsonschema_errors() -> None:
    pytest.importorskip("jsonschema")
    schema = {
        "type": "object",
        "required": ["MethodInformation"],
        "properties": {
            "MethodInformation": {
                "type": "object",
                "required": ["Version"],
                "properties": {"Version": {"type": "string"}},
                "additionalProperties": False,
            }
        },
    }

    payload = {"MethodInformation": {"Version": 1, "Extra": True}}

    result = validate_protocol_schema(payload=payload, schema=schema)

    assert result.is_valid is False
    assert all(issue.severity is IssueSeverity.ERROR for issue in result.issues.issues)
    assert any(issue.path == "MethodInformation.Version" for issue in result.issues.issues)
    assert any(issue.source_location for issue in result.issues.issues)


def test_cross_file_validator_reports_method_and_assay_linkage_problems() -> None:
    context = ProtocolContextModel(
        addon=AddonModel(
            methods=[MethodModel(key="method:1", method_id=77, display_name="Main")],
            assays=[AssayModel(key="assay:1", assay_id=1, name="A1")],
        )
    )
    payload = {
        "MethodInformation": {"Id": "12", "Version": ""},
        "AssayInformation": [{"Type": "Unknown"}, {"Type": ""}],
    }

    result = validate_cross_file_consistency(context, payload)

    assert result.is_valid is False
    issues_by_code = {issue.code: issue for issue in result.issues.issues}
    assert "method-linkage-mismatch" in issues_by_code
    assert issues_by_code["method-linkage-version-missing"].severity is IssueSeverity.WARNING
    assert "broken-assay-reference" in issues_by_code
    assert "assay-type-missing" in issues_by_code


def test_xsd_validator_exposes_source_locations_on_invalid_xml(tmp_path: Path) -> None:
    pytest.importorskip("lxml")
    xsd = tmp_path / "sample.xsd"
    xsd.write_text(
        """
<xsd:schema xmlns:xsd='http://www.w3.org/2001/XMLSchema'>
  <xsd:element name='root' type='xsd:string'/>
</xsd:schema>
""".strip(),
        encoding="utf-8",
    )

    result = validate_xml_against_xsd("<bad></bad>", xsd)

    assert result.is_valid is False
    assert any(issue.source_location for issue in result.issues.issues)

from xml.etree import ElementTree as ET

from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain


def test_domain_validator_catches_missing_version_and_broken_links() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="M", method_version=""),
        assays=[AssayModel(key="a")],
        analytes=[AnalyteModel(key="n", name="N", assay_key="missing")],
        units=[AnalyteUnitModel(key="u", name="U", analyte_key="missing")],
    )
    result = validate_domain(addon)
    codes = {i.code for i in result.issues.issues}
    assert "missing-method-version" in codes
    assert "unknown-assay-key" in codes
    assert "unknown-analyte-key" in codes


def test_domain_validator_detects_combinations_and_alias_ambiguity() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="M", method_version="vNext"),
        assays=[
            AssayModel(key="chem", protocol_type="CHEM", aliases=["Main"]),
            AssayModel(key="ia", protocol_type="IA", aliases=["main"]),
        ],
        analytes=[AnalyteModel(key="n", name="N", assay_key="chem", assay_information_type="IA")],
        units=[],
    )

    result = validate_domain(addon)
    codes = {i.code for i in result.issues.issues}

    assert "invalid-method-version-format" in codes
    assert "unsupported-analyte-assay-information-type" in codes
    assert "missing-analyte-units" in codes
    assert "ambiguous-assay-alias" in codes


def test_domain_validator_detects_empty_assays() -> None:
    addon = AddonModel(method=MethodModel(key="m", method_id="M", method_version="1.0"), assays=[], analytes=[], units=[])
    result = validate_domain(addon)
    assert "empty-assay-list" in {i.code for i in result.issues.issues}


def test_cross_file_validator_detects_method_mismatch() -> None:
    protocol = {"MethodInformation": {"Id": "P", "Version": "1"}}
    root = ET.fromstring("<AddOn><MethodId>X</MethodId><MethodVersion>1</MethodVersion><Assays /></AddOn>")
    result = validate_cross_file_consistency(protocol, root)
    assert result.is_valid is False


def test_cross_file_validator_detects_duplicates_and_broken_refs() -> None:
    protocol = {"MethodInformation": {"Id": "MID", "Version": "2"}}
    root = ET.fromstring(
        """
<AddOn>
  <MethodId>MID</MethodId>
  <MethodVersion>2</MethodVersion>
  <Assays>
    <Assay>
      <Id>1</Id>
      <Analytes>
        <Analyte>
          <Id>10</Id>
          <AssayRef>99</AssayRef>
          <AnalyteUnits>
            <AnalyteUnit><Id>100</Id><AnalyteRef>10</AnalyteRef></AnalyteUnit>
          </AnalyteUnits>
        </Analyte>
      </Analytes>
    </Assay>
    <Assay>
      <Id>1</Id>
      <Analytes>
        <Analyte>
          <Id>10</Id>
          <AssayRef>1</AssayRef>
          <AnalyteUnits>
            <AnalyteUnit><Id>100</Id><AnalyteRef>999</AnalyteRef></AnalyteUnit>
          </AnalyteUnits>
        </Analyte>
      </Analytes>
    </Assay>
  </Assays>
</AddOn>
        """
    )

    result = validate_cross_file_consistency(protocol, root)
    codes = {i.code for i in result.issues.issues}

    assert "duplicate-assay-id" in codes
    assert "duplicate-analyte-id" in codes
    assert "duplicate-analyte-unit-id" in codes
    assert "broken-assay-ref" in codes
    assert "broken-analyte-ref" in codes


def test_cross_file_validator_detects_assay_mismatch_and_merged_identity_gap() -> None:
    protocol = {"MethodInformation": {"Id": "", "Version": ""}, "AssayInformation": [{"Type": "CHEM"}]}
    root = ET.fromstring("""
<AddOn>
  <MethodId>MID</MethodId>
  <MethodVersion>1</MethodVersion>
  <Assays><Assay><Id>1</Id><Name>IA</Name><Analytes /></Assay></Assays>
</AddOn>
    """)
    result = validate_cross_file_consistency(protocol, root)
    codes = {i.code for i in result.issues.issues}
    assert "cross-file-assay-mismatch" in codes
    assert "missing-merged-method-identity" in codes


def test_domain_validator_orders_unknown_assay_before_assay_missing_analytes() -> None:
    addon = AddonModel(
        method=MethodModel(key="m", method_id="M", method_version="1.0"),
        assays=[AssayModel(key="assay:real", protocol_type="CHEM")],
        analytes=[AnalyteModel(key="analyte:oops", name="GLU", assay_key="assay:missing")],
        units=[AnalyteUnitModel(key="unit:oops", name="mg/dL", analyte_key="analyte:oops")],
    )

    codes = [issue.code for issue in validate_domain(addon).issues.issues]

    assert codes.index("unknown-assay-key") < codes.index("assay-missing-analytes")

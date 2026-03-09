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


def test_cross_file_validator_detects_method_mismatch() -> None:
    protocol = {"MethodInformation": {"Id": "P", "Version": "1"}}
    root = ET.fromstring("<AddOn><MethodId>X</MethodId><MethodVersion>1</MethodVersion><Assays /></AddOn>")
    result = validate_cross_file_consistency(protocol, root)
    assert result.is_valid is False

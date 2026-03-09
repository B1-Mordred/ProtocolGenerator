from addon_generator.domain.fragments import FragmentCollection, ProtocolFragment
from addon_generator.domain.ids import DeterministicIdAssigner
from addon_generator.domain.issues import IssueSeverity, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel


def test_addon_model_defaults_and_key_fields_are_internal_only() -> None:
    addon = AddonModel()

    assert addon.addon_id == 0

    method = MethodModel(key="method:prep:1", method_id=11, display_name="Prep")
    assay = AssayModel(key="assay:screen:1", assay_id=22, name="Screen")
    analyte = AnalyteModel(key="analyte:glucose:1", analyte_id=33, name="Glucose")
    unit = AnalyteUnitModel(key="unit:mmol-l:1", unit_id=44, symbol="mmol/L")

    assert method.key != str(method.method_id)
    assert assay.key != str(assay.assay_id)
    assert analyte.key != str(analyte.analyte_id)
    assert unit.key != str(unit.unit_id)


def test_deterministic_id_assigner_is_stable_per_kind_and_label() -> None:
    assigner = DeterministicIdAssigner()

    key_1, id_1 = assigner.assign("method", "Sample Prep")
    key_1_repeat, id_1_repeat = assigner.assign("method", "Sample Prep")
    key_2, id_2 = assigner.assign("method", "Analysis")
    assay_key, assay_id = assigner.assign("assay", "Sample Prep")

    assert (key_1, id_1) == (key_1_repeat, id_1_repeat)
    assert id_2 == 2
    assert assay_id == 1
    assert key_1.startswith("method:")
    assert assay_key.startswith("assay:")


def test_fragment_and_issue_collections() -> None:
    fragments = FragmentCollection()
    fragments.add(ProtocolFragment(path=("MethodInformation", "Name"), value="Prep"))
    fragments.add(ProtocolFragment(path=("AssayInformation", "Primary"), value="Panel-1"))

    assert fragments.materialize() == {
        "MethodInformation": {"Name": "Prep"},
        "AssayInformation": {"Primary": "Panel-1"},
    }

    issues = ValidationIssueCollection()
    issues.add(ValidationIssue(code="missing-field", message="Missing", path="MethodInformation.Name"))
    issues.add(
        ValidationIssue(
            code="optional-warning",
            message="Optional check",
            path="AssayInformation[0]",
            severity=IssueSeverity.WARNING,
        )
    )

    assert issues.has_errors() is True

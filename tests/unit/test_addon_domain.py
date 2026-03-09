from addon_generator.domain.ids import assign_deterministic_ids
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel


def test_canonical_model_and_id_assignment_defaults() -> None:
    addon = AddonModel(
        method=MethodModel(key="method:a", method_id="M-1", method_version="1.0"),
        assays=[AssayModel(key="assay:b"), AssayModel(key="assay:a")],
        analytes=[AnalyteModel(key="analyte:2", name="B", assay_key="assay:b"), AnalyteModel(key="analyte:1", name="A", assay_key="assay:a")],
        units=[AnalyteUnitModel(key="unit:2", name="u2", analyte_key="analyte:2"), AnalyteUnitModel(key="unit:1", name="u1", analyte_key="analyte:1")],
    )

    assign_deterministic_ids(addon)

    assert addon.addon_id == 0
    assert [a.xml_id for a in sorted(addon.assays, key=lambda x: x.key)] == [0, 1]
    assert all(a.assay_ref is not None for a in addon.analytes)
    assert all(u.analyte_ref is not None for u in addon.units)

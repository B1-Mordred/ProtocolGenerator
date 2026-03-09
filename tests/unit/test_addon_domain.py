from addon_generator.domain.fragments import FragmentResolver, FragmentSelectionContext
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


def test_fragment_resolver_selects_most_specific_match_deterministically() -> None:
    resolver = FragmentResolver()
    context = FragmentSelectionContext(
        assay_family="hematology",
        reagent="r1",
        dilution="1:10",
        instrument="inst-a",
        config="cfg-a",
    )

    result = resolver.resolve(
        section="LoadingWorkflowSteps",
        raw_fragments=[
            {
                "name": "generic",
                "selector": {"assay_family": "hematology"},
                "payload": [{"name": "generic"}],
            },
            {
                "name": "most-specific-a",
                "selector": {
                    "assay_family": "hematology",
                    "reagent": "r1",
                    "dilution": "1:10",
                    "instrument": "inst-a",
                    "config": "cfg-a",
                },
                "payload": [{"name": "specific-a"}],
            },
            {
                "name": "most-specific-b",
                "selector": {
                    "assay_family": "hematology",
                    "reagent": "r1",
                    "dilution": "1:10",
                    "instrument": "inst-a",
                    "config": "cfg-a",
                },
                "payload": [{"name": "specific-a"}],
            },
        ],
        context=context,
    )

    assert result == [{"name": "specific-a"}]

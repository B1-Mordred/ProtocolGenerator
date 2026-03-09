from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel, ProtocolContextModel
from addon_generator.fragments.resolvers.default import DefaultProtocolContextResolver
from addon_generator.fragments.resolvers.dilution import DilutionFragmentResolver
from addon_generator.fragments.resolvers.sample_prep import SamplePrepFragmentResolver


def test_default_resolver_returns_assay_loading_processing_contributions() -> None:
    addon = AddonModel(
        protocol_context=ProtocolContextModel(
            assay_fragments=[{"Type": "A", "DisplayName": "Assay A"}],
            loading_fragments=[{"StepName": "LOAD-A"}],
            processing_fragments=[{"StepName": "PROC-A"}],
        )
    )
    resolver = DefaultProtocolContextResolver()

    contributions = resolver.contributions(addon, FragmentSelectionContext())

    by_section = {item.section: item.payload for item in contributions}
    assert by_section["AssayInformation"] == [{"Type": "A", "DisplayName": "Assay A"}]
    assert by_section["LoadingWorkflowSteps"] == [{"StepName": "LOAD-A"}]
    assert by_section["ProcessingWorkflowSteps"] == [{"StepName": "PROC-A"}]


def test_sample_prep_resolver_merges_reagent_calibrator_control() -> None:
    addon = AddonModel(
        source_metadata={"assay_family": "chem", "reagent": "r1"},
        protocol_context=ProtocolContextModel(
            reagent_fragments=[{"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"StepName": "R"}]}],
            calibrator_fragments=[{"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"StepName": "C"}]}],
            control_fragments=[{"selector": {"assay_family": "chem", "reagent": "r1"}, "payload": [{"StepName": "CTRL"}]}],
        ),
    )
    resolver = SamplePrepFragmentResolver()

    contributions = resolver.contributions(addon, FragmentSelectionContext(assay_family="chem", reagent="r1"))

    assert len(contributions) == 1
    assert contributions[0].section == "LoadingWorkflowSteps"
    assert contributions[0].payload == [{"StepName": "R"}]


def test_dilution_resolver_targets_processing_steps() -> None:
    addon = AddonModel(
        source_metadata={"assay_family": "chem", "dilution": "1:2"},
        protocol_context=ProtocolContextModel(
            dilution_fragments=[{"selector": {"assay_family": "chem", "dilution": "1:2"}, "payload": [{"StepName": "DILUTE"}]}]
        ),
    )
    resolver = DilutionFragmentResolver()

    contributions = resolver.contributions(addon, FragmentSelectionContext(assay_family="chem", dilution="1:2"))

    assert len(contributions) == 1
    assert contributions[0].section == "ProcessingWorkflowSteps"
    assert contributions[0].payload == [{"StepName": "DILUTE"}]

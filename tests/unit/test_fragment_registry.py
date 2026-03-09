from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel, ProtocolContextModel
from addon_generator.fragments.registry import FragmentResolverRegistry
from addon_generator.fragments.resolvers.base import SectionContribution


class _ResolverA:
    name = "b-resolver"
    order_hint = 50

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        return [SectionContribution(section="LoadingWorkflowSteps", payload=[{"StepName": "B"}], resolver_name=self.name, order_hint=self.order_hint)]


class _ResolverB:
    name = "a-resolver"
    order_hint = 50

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        return [
            SectionContribution(section="LoadingWorkflowSteps", payload=[{"StepName": "A"}], resolver_name=self.name, order_hint=self.order_hint),
            SectionContribution(section="ProcessingWorkflowSteps", payload=[{"GroupDisplayName": "z"}], resolver_name=self.name, order_hint=self.order_hint),
        ]


def test_registry_collects_and_orders_deterministically() -> None:
    registry = FragmentResolverRegistry(resolvers=[_ResolverA(), _ResolverB()])

    merged = registry.collect(AddonModel(protocol_context=ProtocolContextModel()), FragmentSelectionContext())

    assert merged["LoadingWorkflowSteps"] == [{"StepName": "A"}, {"StepName": "B"}]
    assert merged["ProcessingWorkflowSteps"] == [{"GroupDisplayName": "z"}]

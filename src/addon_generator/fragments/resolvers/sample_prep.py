from __future__ import annotations

from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel
from addon_generator.fragments.resolvers.base import BaseFragmentSectionResolver, SectionContribution


class SamplePrepFragmentResolver(BaseFragmentSectionResolver):
    """Optional sample-prep resolver for reagent/calibrator/control context fragments."""

    name = "sample_prep"
    order_hint = 20

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        protocol_context = addon.protocol_context
        if protocol_context is None:
            return []

        raw_fragments = [
            *list(protocol_context.reagent_fragments),
            *list(protocol_context.calibrator_fragments),
            *list(protocol_context.control_fragments),
        ]
        resolved = self._resolve_raw_fragments(section="LoadingWorkflowSteps", raw_fragments=raw_fragments, context=context)
        if resolved is None:
            return []
        return [
            SectionContribution(
                section="LoadingWorkflowSteps",
                payload=resolved,
                resolver_name=self.name,
                order_hint=self.order_hint,
            )
        ]

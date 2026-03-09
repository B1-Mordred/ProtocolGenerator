from __future__ import annotations

from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel
from addon_generator.fragments.resolvers.base import BaseFragmentSectionResolver, SectionContribution


class DilutionFragmentResolver(BaseFragmentSectionResolver):
    name = "dilution"
    order_hint = 30

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        protocol_context = addon.protocol_context
        if protocol_context is None:
            return []

        resolved = self._resolve_raw_fragments(
            section="ProcessingWorkflowSteps",
            raw_fragments=list(protocol_context.dilution_fragments),
            context=context,
        )
        if resolved is None:
            return []
        return [
            SectionContribution(
                section="ProcessingWorkflowSteps",
                payload=resolved,
                resolver_name=self.name,
                order_hint=self.order_hint,
            )
        ]

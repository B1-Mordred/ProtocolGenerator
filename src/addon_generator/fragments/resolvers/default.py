from __future__ import annotations

from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel
from addon_generator.fragments.resolvers.base import BaseFragmentSectionResolver, SectionContribution


class DefaultProtocolContextResolver(BaseFragmentSectionResolver):
    name = "default"
    order_hint = 10

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        protocol_context = addon.protocol_context
        if protocol_context is None:
            return []

        contribution_specs = (
            ("AssayInformation", protocol_context.assay_fragments),
            ("LoadingWorkflowSteps", protocol_context.loading_fragments),
            ("ProcessingWorkflowSteps", protocol_context.processing_fragments),
        )
        contributions: list[SectionContribution] = []
        for section, raw_fragments in contribution_specs:
            resolved = self._resolve_raw_fragments(section=section, raw_fragments=list(raw_fragments), context=context)
            if resolved is None:
                continue
            contributions.append(
                SectionContribution(
                    section=section,
                    payload=resolved,
                    resolver_name=self.name,
                    order_hint=self.order_hint,
                )
            )
        return contributions

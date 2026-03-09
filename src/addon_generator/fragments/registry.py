from __future__ import annotations

import json
from typing import Any

from addon_generator.domain.fragments import FragmentSelectionContext
from addon_generator.domain.models import AddonModel
from addon_generator.fragments.resolvers.base import FragmentSectionResolver, SectionContribution
from addon_generator.fragments.resolvers.default import DefaultProtocolContextResolver
from addon_generator.fragments.resolvers.dilution import DilutionFragmentResolver
from addon_generator.fragments.resolvers.sample_prep import SamplePrepFragmentResolver


class FragmentResolverRegistry:
    def __init__(self, resolvers: list[FragmentSectionResolver] | None = None):
        self._resolvers = list(resolvers) if resolvers is not None else [
            DefaultProtocolContextResolver(),
            SamplePrepFragmentResolver(),
            DilutionFragmentResolver(),
        ]

    def collect(self, addon: AddonModel, context: FragmentSelectionContext) -> dict[str, Any]:
        indexed: list[tuple[int, int, str, SectionContribution]] = []
        for registration_index, resolver in enumerate(self._resolvers):
            for contribution in resolver.contributions(addon, context):
                indexed.append((contribution.order_hint, registration_index, resolver.name, contribution))

        indexed.sort(
            key=lambda entry: (
                entry[0],
                entry[3].section,
                json.dumps(entry[3].payload, sort_keys=True, default=str),
                entry[1],
                entry[2],
            )
        )

        sections: dict[str, list[Any]] = {}
        for _, _, _, contribution in indexed:
            bucket = sections.setdefault(contribution.section, [])
            payload = contribution.payload
            if isinstance(payload, list):
                bucket.extend(payload)
            else:
                bucket.append(payload)

        return sections

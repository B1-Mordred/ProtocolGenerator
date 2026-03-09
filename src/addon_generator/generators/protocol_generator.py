from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.fragments import FragmentCollection, ProtocolFragment
from addon_generator.domain.models import ProtocolContextModel


@dataclass(slots=True)
class ProtocolJsonGenerationResult:
    payload: dict[str, Any]
    fragments: FragmentCollection


def build_canonical_protocol_fragments(context: ProtocolContextModel) -> FragmentCollection:
    """Build protocol fragments from the canonical domain model only."""

    addon = context.addon
    fragments = FragmentCollection(
        [
            ProtocolFragment(path=("MethodInformation", "Id"), value=str(addon.addon_id), origin="canonical-model"),
            ProtocolFragment(
                path=("MethodInformation", "DisplayName"), value=addon.addon_name, origin="canonical-model"
            ),
            ProtocolFragment(path=("AssayInformation",), value=[{"Type": assay.name} for assay in addon.assays], origin="canonical-model"),
        ]
    )
    return fragments


def generate_protocol_json(
    context: ProtocolContextModel,
    protocol_fragments: FragmentCollection | None = None,
) -> ProtocolJsonGenerationResult:
    """Materialize protocol json from canonical model + optional protocol fragments."""

    merged = FragmentCollection()
    for fragment in build_canonical_protocol_fragments(context).fragments:
        merged.add(fragment)
    if protocol_fragments is not None:
        for fragment in protocol_fragments.fragments:
            merged.add(fragment)

    return ProtocolJsonGenerationResult(payload=merged.materialize(), fragments=merged)

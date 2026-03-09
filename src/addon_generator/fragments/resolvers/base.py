from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from addon_generator.domain.fragments import FragmentResolver, FragmentSelectionContext
from addon_generator.domain.models import AddonModel


@dataclass(frozen=True, slots=True)
class SectionContribution:
    section: str
    payload: Any
    resolver_name: str
    order_hint: int = 100


class FragmentSectionResolver(Protocol):
    name: str
    order_hint: int

    def contributions(self, addon: AddonModel, context: FragmentSelectionContext) -> list[SectionContribution]:
        ...


class BaseFragmentSectionResolver:
    name = "base"
    order_hint = 100

    def __init__(self) -> None:
        self._fragment_resolver = FragmentResolver()

    def _resolve_raw_fragments(
        self,
        *,
        section: str,
        raw_fragments: list[dict[str, Any]] | None,
        context: FragmentSelectionContext,
    ) -> Any:
        if not raw_fragments:
            return None
        if self._is_direct_section_payload(raw_fragments):
            return list(raw_fragments)

        resolved = self._fragment_resolver.resolve(section=section, raw_fragments=raw_fragments, context=context)
        if section == "AssayInformation" and resolved is not None and not isinstance(resolved, list):
            return [resolved]
        return resolved

    @staticmethod
    def _is_direct_section_payload(raw_fragments: list[dict[str, Any]]) -> bool:
        fragment_definition_keys = {
            "metadata",
            "selector",
            "payload",
            "value",
            "steps",
            "name",
            "assay_family",
            "reagent",
            "dilution",
            "instrument",
            "config",
        }
        return all(isinstance(item, dict) and not any(key in item for key in fragment_definition_keys) for item in raw_fragments)

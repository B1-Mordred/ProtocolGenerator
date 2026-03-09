from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ProtocolFragment:
    """A fragment that can be merged into a projected protocol payload."""

    path: tuple[str, ...]
    value: Any
    origin: str = "domain"


@dataclass(slots=True)
class FragmentCollection:
    """Ordered fragment set with deterministic last-write-wins materialization."""

    fragments: list[ProtocolFragment] = field(default_factory=list)

    def add(self, fragment: ProtocolFragment) -> None:
        self.fragments.append(fragment)

    def materialize(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for fragment in self.fragments:
            target = result
            for segment in fragment.path[:-1]:
                target = target.setdefault(segment, {})
            target[fragment.path[-1]] = fragment.value
        return result


@dataclass(frozen=True, slots=True)
class FragmentMetadata:
    """Descriptive metadata that identifies and documents a fragment definition."""

    name: str
    section: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class FragmentSelectionContext:
    """Context attributes used for deterministic fragment selection."""

    assay_family: str | None = None
    reagent: str | None = None
    dilution: str | None = None
    instrument: str | None = None
    config: str | None = None


@dataclass(frozen=True, slots=True)
class FragmentSelector:
    """Matching criteria for a fragment definition."""

    assay_family: str | None = None
    reagent: str | None = None
    dilution: str | None = None
    instrument: str | None = None
    config: str | None = None

    def _criteria(self) -> tuple[tuple[str, str], ...]:
        pairs = (
            ("assay_family", self.assay_family),
            ("reagent", self.reagent),
            ("dilution", self.dilution),
            ("instrument", self.instrument),
            ("config", self.config),
        )
        return tuple((key, value.strip().casefold()) for key, value in pairs if isinstance(value, str) and value.strip())

    def matches(self, context: FragmentSelectionContext) -> bool:
        for key, expected in self._criteria():
            actual = getattr(context, key)
            if not isinstance(actual, str) or actual.strip().casefold() != expected:
                return False
        return True

    def specificity(self) -> int:
        return len(self._criteria())


@dataclass(frozen=True, slots=True)
class FragmentDefinition:
    """Fragment definition contract for metadata, selector, and renderable payload."""

    metadata: FragmentMetadata
    selector: FragmentSelector
    payload: Any

    def fingerprint(self) -> str:
        return json.dumps(self.payload, sort_keys=True, default=str)


class FragmentLoader(Protocol):
    """Loading contract for raw fragment data into definitions."""

    def load(self, section: str, raw_fragments: list[dict[str, Any]]) -> list[FragmentDefinition]:
        ...


class FragmentRenderer(Protocol):
    """Rendering/processing contract for transforming a selected fragment to section output."""

    def render(self, definition: FragmentDefinition) -> Any:
        ...


class DefaultFragmentLoader:
    def load(self, section: str, raw_fragments: list[dict[str, Any]]) -> list[FragmentDefinition]:
        definitions: list[FragmentDefinition] = []
        for index, raw in enumerate(raw_fragments):
            metadata_raw = raw.get("metadata", {}) if isinstance(raw.get("metadata"), dict) else {}
            selector_raw = raw.get("selector", {}) if isinstance(raw.get("selector"), dict) else {}

            metadata = FragmentMetadata(
                name=str(metadata_raw.get("name") or raw.get("name") or f"{section}:{index}"),
                section=section,
                description=metadata_raw.get("description") if isinstance(metadata_raw.get("description"), str) else None,
            )
            selector = FragmentSelector(
                assay_family=selector_raw.get("assay_family") or raw.get("assay_family"),
                reagent=selector_raw.get("reagent") or raw.get("reagent"),
                dilution=selector_raw.get("dilution") or raw.get("dilution"),
                instrument=selector_raw.get("instrument") or raw.get("instrument"),
                config=selector_raw.get("config") or raw.get("config"),
            )

            payload = raw.get("payload")
            if payload is None:
                payload = raw.get("value")
            if payload is None:
                payload = raw.get("steps")
            if payload is None and raw.get(section) is not None:
                payload = raw.get(section)
            if payload is None:
                payload = raw

            definitions.append(FragmentDefinition(metadata=metadata, selector=selector, payload=payload))
        return definitions


class DefaultFragmentRenderer:
    def render(self, definition: FragmentDefinition) -> Any:
        return definition.payload


class FragmentResolver:
    """Deterministically select and render the most specific matching fragment."""

    def __init__(self, loader: FragmentLoader | None = None, renderer: FragmentRenderer | None = None):
        self.loader = loader or DefaultFragmentLoader()
        self.renderer = renderer or DefaultFragmentRenderer()

    def resolve(self, section: str, raw_fragments: list[dict[str, Any]], context: FragmentSelectionContext) -> Any:
        definitions = self.loader.load(section=section, raw_fragments=raw_fragments)
        matching = [definition for definition in definitions if definition.selector.matches(context)]
        if not matching:
            return None
        selected = sorted(
            matching,
            key=lambda definition: (
                -definition.selector.specificity(),
                definition.metadata.name,
                definition.fingerprint(),
            ),
        )[0]
        return self.renderer.render(selected)

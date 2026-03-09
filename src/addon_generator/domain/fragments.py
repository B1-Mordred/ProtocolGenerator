from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

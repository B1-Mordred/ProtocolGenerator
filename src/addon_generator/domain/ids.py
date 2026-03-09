from __future__ import annotations

import re
from collections import defaultdict


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    normalized = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return normalized or "item"


def make_stable_key(kind: str, label: str, index: int) -> str:
    """Create stable keys from deterministic inputs."""

    return f"{kind}:{_slugify(label)}:{index}"


class DeterministicIdAssigner:
    """Assign deterministic integer IDs and internal keys per object kind."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._seen: dict[tuple[str, str], tuple[str, int]] = {}

    def assign(self, kind: str, label: str) -> tuple[str, int]:
        """Return the same key/id for repeated (kind, label) assignments."""

        cache_key = (kind, label)
        if cache_key in self._seen:
            return self._seen[cache_key]

        self._counters[kind] += 1
        next_id = self._counters[kind]
        key = make_stable_key(kind=kind, label=label, index=next_id)
        result = (key, next_id)
        self._seen[cache_key] = result
        return result

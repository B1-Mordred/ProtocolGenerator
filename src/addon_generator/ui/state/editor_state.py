from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EditorState:
    manual_overrides: dict[str, Any] = field(default_factory=dict)
    effective_values: dict[str, Any] = field(default_factory=dict)
    unresolved_conflicts: dict[str, list[Any]] = field(default_factory=dict)
    selected_entity: str | None = None
    selected_section_index: int = 0
    export_settings: dict[str, Any] = field(default_factory=dict)

    def set_override(self, key: str, value: Any) -> None:
        self.manual_overrides[key] = value

    def clear_override(self, key: str) -> None:
        self.manual_overrides.pop(key, None)

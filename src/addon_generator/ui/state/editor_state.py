from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EditorState:
    manual_overrides: dict[str, Any] = field(default_factory=dict)
    sample_prep_overrides: list[dict[str, str]] = field(default_factory=list)
    dilution_overrides: list[dict[str, str]] = field(default_factory=list)
    selected_sample_prep_step_id: str | None = None
    selected_dilution_id: str | None = None
    manual_edit_markers: dict[str, bool] = field(default_factory=dict)
    effective_values: dict[str, Any] = field(default_factory=dict)
    unresolved_conflicts: dict[str, list[Any]] = field(default_factory=dict)
    selected_entity: str | None = None
    selected_section_index: int = 0
    export_settings: dict[str, Any] = field(default_factory=dict)

    def set_override(self, key: str, value: Any) -> None:
        self.manual_overrides[key] = value
        self.manual_edit_markers[key] = True

    def clear_override(self, key: str) -> None:
        self.manual_overrides.pop(key, None)
        self.manual_edit_markers.pop(key, None)

    def mark_manual_edit(self, key: str, is_manual: bool = True) -> None:
        if is_manual:
            self.manual_edit_markers[key] = True
            return
        self.manual_edit_markers.pop(key, None)

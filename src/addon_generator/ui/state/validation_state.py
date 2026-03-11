from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field

from addon_generator.ui.models.issue_view_model import IssueViewModel


@dataclass(slots=True)
class ValidationState:
    stale: bool = True
    issues: list[IssueViewModel] = field(default_factory=list)
    grouped_issues: dict[str, list[IssueViewModel]] = field(default_factory=dict)
    severity_counts: dict[str, int] = field(default_factory=lambda: {"error": 0, "warning": 0, "info": 0})
    category_counts: dict[str, int] = field(default_factory=dict)
    field_mapping_report: dict[str, object] = field(default_factory=dict)
    export_blocked: bool = False
    last_validated_at: datetime | None = None

    @property
    def has_blockers(self) -> bool:
        return self.export_blocked

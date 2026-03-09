from __future__ import annotations

from dataclasses import dataclass, field

from addon_generator.ui.models.issue_view_model import IssueViewModel


@dataclass(slots=True)
class ValidationState:
    stale: bool = True
    issues: list[IssueViewModel] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueSource(str, Enum):
    DOMAIN = "domain"
    VALIDATION = "validation"
    PROJECTION = "projection"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    path: str
    severity: IssueSeverity = IssueSeverity.ERROR
    source: IssueSource = IssueSource.VALIDATION
    entity_keys: tuple[str, ...] = ()
    source_location: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIssueCollection:
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def has_errors(self) -> bool:
        return any(issue.severity is IssueSeverity.ERROR for issue in self.issues)

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class IssueViewModel:
    code: str
    severity: str
    summary: str
    section: str = ""
    category: str = "General"
    entity_context: str = ""
    provenance: str = ""
    recommended_action: str = ""
    navigation_target: dict[str, Any] | None = None

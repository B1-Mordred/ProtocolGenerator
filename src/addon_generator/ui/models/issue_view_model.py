from dataclasses import dataclass


@dataclass(slots=True)
class IssueViewModel:
    code: str
    severity: str
    summary: str
    section: str = ""
    entity_context: str = ""
    provenance: str = ""

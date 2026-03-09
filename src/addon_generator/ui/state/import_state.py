from __future__ import annotations

from dataclasses import dataclass, field

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.ui.models.issue_view_model import IssueViewModel


@dataclass(slots=True)
class ImportState:
    bundles: list[InputDTOBundle] = field(default_factory=list)
    provenance: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    issues: list[IssueViewModel] = field(default_factory=list)

    def replace(self, *, bundles: list[InputDTOBundle], provenance: dict[str, list[dict[str, str]]], issues: list[IssueViewModel]) -> None:
        self.bundles = bundles
        self.provenance = provenance
        self.issues = issues

from __future__ import annotations

from dataclasses import dataclass, field

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.ui.models.issue_view_model import IssueViewModel


@dataclass(slots=True)
class ImportState:
    bundles: list[InputDTOBundle] = field(default_factory=list)
    provenance: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    imported_sample_prep_dtos: list[dict[str, str]] = field(default_factory=list)
    imported_dilution_dtos: list[dict[str, str]] = field(default_factory=list)
    conflict_summary: dict[str, int] = field(default_factory=dict)
    provenance_lookup: dict[str, dict[str, str]] = field(default_factory=dict)
    issues: list[IssueViewModel] = field(default_factory=list)
    review_resolutions: dict[str, str] = field(default_factory=dict)

    def replace(self, *, bundles: list[InputDTOBundle], provenance: dict[str, list[dict[str, str]]], issues: list[IssueViewModel]) -> None:
        self.bundles = bundles
        self.provenance = provenance
        self.issues = issues
        self.review_resolutions = {}
        self.imported_sample_prep_dtos = []
        self.imported_dilution_dtos = []
        self.conflict_summary = {}
        self.provenance_lookup = {
            key: {
                "source": (entries[-1].get("source") if entries else ""),
                "source_label": (entries[-1].get("source_label") if entries else ""),
                "location_text": (entries[-1].get("location_text") if entries else ""),
            }
            for key, entries in provenance.items()
        }

from __future__ import annotations

import logging

from addon_generator.domain.issues import ValidationIssue
from addon_generator.importers import ExcelImporter, XmlImporter
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.ui.models.issue_view_model import IssueViewModel


LOGGER = logging.getLogger(__name__)


class ImportService:
    def load_excel(self, path: str) -> tuple[InputDTOBundle, dict[str, list[dict[str, str]]], list[IssueViewModel]]:
        LOGGER.info("Starting Excel import from %s", path)
        bundle = ExcelImporter().import_workbook_bundle(path)
        LOGGER.info(
            "Excel import succeeded from %s (assays=%d analytes=%d units=%d sample_prep_steps=%d dilutions=%d)",
            path,
            len(bundle.assays),
            len(bundle.analytes),
            len(bundle.units),
            len(bundle.sample_prep_steps),
            len(bundle.dilution_schemes),
        )
        return bundle, self._coerce_provenance(bundle), []

    def load_xml(self, path: str) -> tuple[InputDTOBundle, dict[str, list[dict[str, str]]], list[IssueViewModel]]:
        bundle = XmlImporter().import_xml_bundle(path)
        return bundle, self._coerce_provenance(bundle), []

    @staticmethod
    def _coerce_provenance(bundle: InputDTOBundle) -> dict[str, list[dict[str, str]]]:
        out: dict[str, list[dict[str, str]]] = {}
        for key, entries in (bundle.provenance or {}).items():
            out[key] = [ImportService._entry_dict(entry) for entry in entries]
        return out

    @staticmethod
    def _entry_dict(entry: object) -> dict[str, str]:
        source = getattr(entry, "source_type", "default")
        source_label = {"excel": "Excel", "xml": "XML", "gui": "GUI", "default": "Default"}.get(source, str(source).title())
        location = ":".join(
            [
                str(part)
                for part in (
                    getattr(entry, "source_file", None),
                    getattr(entry, "source_sheet", None),
                    getattr(entry, "row", None),
                    getattr(entry, "column", None),
                )
                if part not in (None, "")
            ]
        )
        return {
            "source": source,
            "source_label": source_label,
            "location": location,
            "location_text": location or "(unknown location)",
            "note": getattr(entry, "field_key", "") or "",
        }


def issue_from_validation_issue(issue: ValidationIssue, section: str = "Validation") -> IssueViewModel:
    details = issue.details or {}
    path = issue.path.lower()
    section_index = 6
    entity = "/".join(issue.entity_keys) or issue.path
    category = "Validation"
    if "method" in path:
        section_index = 0
        category = "Method"
    elif "assay" in path:
        section_index = 1
        category = "Assays"
    elif "analyte" in path:
        section_index = 2
        category = "Analytes"
    elif "sample" in path or "prep" in path:
        section_index = 3
        category = "Sample Prep"
    elif "dilution" in path:
        section_index = 4
        category = "Dilutions"
    elif section == "Import":
        section_index = 5
        category = "Import Review"

    return IssueViewModel(
        code=issue.code,
        severity=issue.severity.value,
        summary=issue.message,
        section=section,
        category=category,
        entity_context="/".join(issue.entity_keys) or issue.path,
        provenance=issue.source_location or "",
        recommended_action=str(details.get("recommended_action", "Resolve mapped field values and rerun validation.")),
        navigation_target={"section_index": section_index, "entity": entity, "path": issue.path},
    )

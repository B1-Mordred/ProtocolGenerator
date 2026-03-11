from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


class ImportReviewFilter(str, Enum):
    ACTION_REQUIRED = "Action Required"
    ALL = "All"
    CONFLICTS = "Conflicts"
    OVERRIDES = "Overrides"
    MISSING_REQUIRED = "Missing Required"
    IMPORTED_ONLY = "Imported Only"


@dataclass(slots=True)
class ImportReviewRowViewModel:
    path: str
    entity: str
    field: str
    imported_value: str
    effective_value: str
    source: str
    override_status: bool
    conflict_status: bool
    raw_provenance_detail: str
    normalization_notes: str
    jump_target_metadata: dict[str, Any]
    resolution_state: str
    required_classification: str
    fallback_hint: str


class ImportReviewScreenViewModel:
    REQUIRED_PATHS = {"method.method_id", "method.method_version"}

    def __init__(self, app_state: AppState, merge_service: MergeServiceAdapter) -> None:
        self._app_state = app_state
        self._merge_service = merge_service

    def rows(self, filter_name: str = ImportReviewFilter.ACTION_REQUIRED.value) -> list[ImportReviewRowViewModel]:
        rows = [self._build_row(path) for path in sorted(self._review_keys())]
        filter_value = ImportReviewFilter(filter_name)
        return [row for row in rows if self._matches_filter(row, filter_value)]

    def accept_imported(self, path: str) -> None:
        self._merge_service.accept_imported_value(self._app_state, path)

    def accept_default(self, path: str) -> None:
        self._merge_service.revert_default_value(self._app_state, path)
        self._app_state.import_state.review_resolutions[path] = "accepted_default"

    def keep_override(self, path: str) -> None:
        self._merge_service.keep_override_value(self._app_state, path)

    def revert_default(self, path: str) -> None:
        self._merge_service.revert_default_value(self._app_state, path)

    def clear_override(self, path: str) -> None:
        self._merge_service.revert_default_value(self._app_state, path)
        self._app_state.import_state.review_resolutions[path] = "cleared_override"

    def _build_row(self, path: str) -> ImportReviewRowViewModel:
        flattened = {row["path"]: row for row in self._merge_service.flatten_import_review_rows(self._app_state)}
        imported_value = flattened.get(path, {}).get("imported")
        effective_value = flattened.get(path, {}).get("effective")
        provenance_items = self._app_state.import_state.provenance.get(path, [])
        provenance_lookup = self._app_state.import_state.provenance_lookup.get(path, {})
        raw_provenance = "\n".join(
            f"{item.get('source', 'unknown')} @ {item.get('location', '')} ({item.get('note', '')})" for item in provenance_items
        )
        source = provenance_items[-1]["source"] if provenance_items else "merged"
        entity, field = self._split_path(path)
        normalization_notes = ""
        if isinstance(imported_value, str) and imported_value != imported_value.strip():
            normalization_notes = "Trimmed surrounding whitespace."
        elif imported_value in ("", None) and effective_value in ("", None):
            normalization_notes = "Empty optional value normalized to None."

        required_classification = self._required_classification(path, imported_value, effective_value)
        fallback_hint = self._fallback_hint(path, imported_value, provenance_lookup)

        return ImportReviewRowViewModel(
            path=path,
            entity=entity,
            field=field,
            imported_value=self._stringify(imported_value),
            effective_value=self._stringify(effective_value),
            source=source,
            override_status=path in self._app_state.editor_state.manual_overrides,
            conflict_status=path in set(self._app_state.editor_state.unresolved_conflicts),
            raw_provenance_detail=raw_provenance,
            normalization_notes=normalization_notes,
            jump_target_metadata={"section_index": self._section_for_path(path), "entity": entity, "path": path},
            resolution_state=self._app_state.import_state.review_resolutions.get(path, "pending"),
            required_classification=required_classification,
            fallback_hint=fallback_hint,
        )

    def _review_keys(self) -> set[str]:
        keys = set(self._app_state.import_state.provenance)
        keys.update(self._app_state.editor_state.manual_overrides)
        keys.update(self._app_state.editor_state.unresolved_conflicts)
        keys.update(self._imported_lookup())
        keys.update(self.REQUIRED_PATHS)
        return keys

    def _matches_filter(self, row: ImportReviewRowViewModel, filter_name: ImportReviewFilter) -> bool:
        if filter_name == ImportReviewFilter.ACTION_REQUIRED:
            return row.required_classification in {"user-required", "conflict-required"}
        if filter_name == ImportReviewFilter.ALL:
            return True
        if filter_name == ImportReviewFilter.CONFLICTS:
            return row.conflict_status
        if filter_name == ImportReviewFilter.OVERRIDES:
            return row.override_status
        if filter_name == ImportReviewFilter.MISSING_REQUIRED:
            return row.path in self.REQUIRED_PATHS and row.effective_value == ""
        if filter_name == ImportReviewFilter.IMPORTED_ONLY:
            return bool(row.imported_value) and not row.override_status and not row.conflict_status
        return True

    def _imported_lookup(self) -> dict[str, Any]:
        if not self._app_state.import_state.bundles:
            return {}
        imported_bundle = asdict(self._app_state.import_state.bundles[-1])
        return self._flatten_bundle(imported_bundle)

    def _flatten_bundle(self, payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                out.update(self._flatten_bundle(value, path))
            elif isinstance(value, list):
                continue
            else:
                out[path] = value
        return out

    def _required_classification(self, path: str, imported_value: Any, effective_value: Any) -> str:
        if path in self._app_state.editor_state.unresolved_conflicts:
            return "conflict-required"
        if path not in self.REQUIRED_PATHS:
            return "auto-resolved"
        if self._stringify(effective_value).strip() == "":
            return "user-required"
        if self._stringify(imported_value).strip() != "":
            return "auto-resolved"
        return "user-required"

    @staticmethod
    def _fallback_hint(path: str, imported_value: Any, provenance_lookup: dict[str, str]) -> str:
        source_label = str(provenance_lookup.get("source_label") or provenance_lookup.get("source") or "").strip()
        location = str(provenance_lookup.get("location_text") or "").strip()
        if source_label:
            origin = source_label if not location else f"{source_label} ({location})"
            if str(imported_value or "").strip():
                return f"Using imported value from {origin}"
            return f"No imported value from {origin}; default/manual value is in effect"
        if path.startswith("method.") and not str(imported_value or "").strip():
            return "No import provenance available; default/manual value is in effect"
        return ""

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        if "." not in path:
            return path, ""
        entity, field = path.rsplit(".", 1)
        return entity, field

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _section_for_path(path: str) -> int:
        if path.startswith("method"):
            return 0
        if path.startswith("assays"):
            return 1
        if path.startswith("analytes"):
            return 2
        if path.startswith("sample_prep"):
            return 3
        if path.startswith("dilution"):
            return 4
        return 5

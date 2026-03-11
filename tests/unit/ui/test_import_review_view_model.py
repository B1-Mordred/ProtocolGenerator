from __future__ import annotations

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.models.import_review_view_model import ImportReviewFilter, ImportReviewScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


def _state() -> AppState:
    state = AppState()
    state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            method=MethodInputDTO(key="m1", method_id="M-1", method_version="1"),
        )
    ]
    state.import_state.provenance = {
        "method.method_id": [{"source": "excel", "source_label": "Excel", "location_text": "book.xlsx:Basics:2:B", "location": "book.xlsx:Basics:2:B", "note": "method.method_id"}],
        "method.method_version": [{"source": "excel", "source_label": "Excel", "location_text": "book.xlsx:Basics:3:B", "location": "book.xlsx:Basics:3:B", "note": "method.method_version"}],
    }
    state.import_state.provenance_lookup = {
        "method.method_id": {"source": "excel", "source_label": "Excel", "location_text": "book.xlsx:Basics:2:B"},
        "method.method_version": {"source": "excel", "source_label": "Excel", "location_text": "book.xlsx:Basics:3:B"},
    }
    MergeServiceAdapter().recompute(state)
    return state


def test_filter_rows_and_resolution_actions_update_state() -> None:
    state = _state()
    vm = ImportReviewScreenViewModel(state, MergeServiceAdapter())

    state.editor_state.unresolved_conflicts = {"method.method_id": [{"winner": "M-1"}]}
    rows = vm.rows(ImportReviewFilter.CONFLICTS.value)
    assert len(rows) == 1
    assert rows[0].path == "method.method_id"
    assert rows[0].required_classification == "conflict-required"

    vm.accept_imported("method.method_id")
    assert state.editor_state.manual_overrides["method.method_id"] == "M-1"
    assert state.import_state.review_resolutions["method.method_id"] == "accepted_imported"
    assert state.validation_state.stale is True
    assert state.preview_state.stale is True


def test_missing_required_filter_flags_empty_effective_value() -> None:
    state = _state()
    state.editor_state.set_override("method.method_version", None)
    MergeServiceAdapter().recompute(state)
    vm = ImportReviewScreenViewModel(state, MergeServiceAdapter())

    rows = vm.rows(ImportReviewFilter.MISSING_REQUIRED.value)
    assert [row.path for row in rows] == ["method.method_version"]


def test_action_required_filter_hides_auto_resolved_and_surfaces_fallback_hint() -> None:
    state = _state()
    vm = ImportReviewScreenViewModel(state, MergeServiceAdapter())

    rows = vm.rows(ImportReviewFilter.ACTION_REQUIRED.value)
    row_by_path = {row.path: row for row in rows}

    assert "method.method_id" not in row_by_path
    assert "method.method_version" not in row_by_path

    state.editor_state.set_override("method.method_version", None)
    MergeServiceAdapter().recompute(state)
    rows_after = vm.rows(ImportReviewFilter.ACTION_REQUIRED.value)
    target = next(row for row in rows_after if row.path == "method.method_version")
    assert target.required_classification == "user-required"
    assert "Using imported value from Excel" in target.fallback_hint


def test_accept_default_records_resolution_and_clears_override() -> None:
    state = _state()
    state.editor_state.set_override("method.method_id", "MANUAL")
    MergeServiceAdapter().recompute(state)

    vm = ImportReviewScreenViewModel(state, MergeServiceAdapter())
    vm.accept_default("method.method_id")

    assert "method.method_id" not in state.editor_state.manual_overrides
    assert state.import_state.review_resolutions["method.method_id"] == "accepted_default"

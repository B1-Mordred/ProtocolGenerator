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
    state.import_state.provenance = {"method.method_id": [{"source": "excel", "location": "book.xlsx:Basics:2:B", "note": "method.method_id"}]}
    MergeServiceAdapter().recompute(state)
    return state


def test_filter_rows_and_resolution_actions_update_state() -> None:
    state = _state()
    vm = ImportReviewScreenViewModel(state, MergeServiceAdapter())

    state.editor_state.unresolved_conflicts = {"method.method_id": [{"winner": "M-1"}]}
    rows = vm.rows(ImportReviewFilter.CONFLICTS.value)
    assert len(rows) == 1
    assert rows[0].path == "method.method_id"

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

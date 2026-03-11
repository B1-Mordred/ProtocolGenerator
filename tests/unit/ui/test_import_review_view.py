from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.import_review_view import ImportReviewView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_import_review_view_filters_and_navigates(qapp) -> None:
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m1", method_id="M-1", method_version="1"))]
    state.import_state.provenance = {"method.method_id": [{"source": "excel", "location": "book.xlsx", "note": "id"}]}
    MergeServiceAdapter().recompute(state)

    jumped = {}

    view = ImportReviewView(
        app_state=state,
        merge_service=MergeServiceAdapter(),
        navigate_to_owner=lambda payload: jumped.update(payload),
    )
    assert view.filter_box.currentText() == "Action Required"

    view.filter_box.setCurrentText("All")
    assert view.table.rowCount() >= 1

    view.filter_box.setCurrentText("Overrides")
    assert view.table.rowCount() == 0

    view.filter_box.setCurrentText("All")
    view.table.selectRow(0)
    view.jump_btn.click()
    assert "section_index" in jumped


def test_import_review_view_resolution_updates_effective_and_navigation(qapp) -> None:
    state = AppState()
    state.import_state.bundles = [
        InputDTOBundle(source_type="xml", method=MethodInputDTO(key="m1", method_id="M-XML", method_version="1")),
        InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m1", method_id="M-XL", method_version="2")),
    ]
    state.import_state.provenance = {
        "method.method_id": [
            {"source": "xml", "location": "book.xml"},
            {"source": "excel", "location": "book.xlsx"},
        ]
    }
    merge = MergeServiceAdapter()
    merge.recompute(state)

    jumped = {}
    changed = []
    view = ImportReviewView(
        app_state=state,
        merge_service=merge,
        navigate_to_owner=lambda payload: jumped.update(payload),
        on_state_changed=lambda: changed.append("changed"),
    )

    view.filter_box.setCurrentText("All")
    paths = [view._rows[idx].path for idx in range(view.table.rowCount())]
    assert "method.method_id" in paths

    view.filter_box.setCurrentText("Conflicts")
    assert view.table.rowCount() >= 1

    view.filter_box.setCurrentText("All")
    target_idx = next(i for i, row in enumerate(view._rows) if row.path == "method.method_id")
    view.table.selectRow(target_idx)
    view.accept_btn.click()

    assert state.import_state.review_resolutions["method.method_id"] == "accepted_imported"
    assert state.editor_state.manual_overrides["method.method_id"] == "M-XL"
    assert state.editor_state.effective_values["method"]["method_id"] == "M-XL"
    assert state.preview_state.stale is True
    assert state.validation_state.stale is True
    assert changed

    target_idx = next(i for i, row in enumerate(view._rows) if row.path == "method.method_id")
    view.table.selectRow(target_idx)
    view.jump_btn.click()
    assert jumped["section_index"] == 0
    assert jumped["entity"] == "method"


def test_import_review_accept_default_button_clears_override(qapp) -> None:
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m1", method_id="M-1", method_version="1"))]
    merge = MergeServiceAdapter()
    merge.recompute(state)
    state.editor_state.set_override("method.method_id", "MANUAL")
    merge.recompute(state)

    view = ImportReviewView(app_state=state, merge_service=merge)
    view.filter_box.setCurrentText("All")
    target_idx = next(i for i, row in enumerate(view._rows) if row.path == "method.method_id")
    view.table.selectRow(target_idx)
    view.accept_default_btn.click()

    assert "method.method_id" not in state.editor_state.manual_overrides
    assert state.import_state.review_resolutions["method.method_id"] == "accepted_default"

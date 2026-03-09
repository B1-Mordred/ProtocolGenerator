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
    assert view.table.rowCount() >= 1

    view.filter_box.setCurrentText("Overrides")
    assert view.table.rowCount() == 0

    view.filter_box.setCurrentText("All")
    view.table.selectRow(0)
    view.jump_btn.click()
    assert "section_index" in jumped

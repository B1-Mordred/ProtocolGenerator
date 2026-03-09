from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.dilutions_view import DilutionsView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_dilutions_view_selection_and_validation_sync(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel")]
    view = DilutionsView(app_state=state)

    view.add_btn.click()
    assert view.table.model().rowCount() == 1

    view.inputs["name"].setText("D1")
    view.inputs["name"].editingFinished.emit()
    view.inputs["buffer1_ratio"].setText("x")
    view.inputs["buffer1_ratio"].editingFinished.emit()

    assert "invalid-ratio" in view.provenance_labels["buffer1_ratio"].text()
    assert view.status_label.text() in {"incomplete and invalid ratio", "invalid ratio"}

    view.reset_buttons["buffer1_ratio"].click()
    assert "required" in view.provenance_labels["buffer1_ratio"].text()

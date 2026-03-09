from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.sampleprep_view import SamplePrepView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_sampleprep_view_selection_and_form_sync(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel", hidden_vocab={"SamplePrepAction": ["Mix"]})]
    view = SamplePrepView(app_state=state)

    view.add_btn.click()
    assert view.table.model().rowCount() == 1

    view.detail.inputs["Order"].setText("1")
    view.detail.inputs["Order"].editingFinished.emit()
    view.detail.inputs["Action"].setText("Nope")
    view.detail.inputs["Action"].editingFinished.emit()

    assert "invalid-action" in view.provenance_labels["action"].text()
    view.reset_buttons["action"].click()
    assert "required" in view.provenance_labels["action"].text()

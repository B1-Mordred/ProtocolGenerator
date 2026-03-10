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


def test_dilutions_view_emits_state_changed_on_mutations(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel")]
    calls = []
    view = DilutionsView(app_state=state, on_state_changed=lambda: calls.append("changed"))

    view.add_btn.click()
    view.inputs["name"].setText("D1")
    view.inputs["name"].editingFinished.emit()

    assert len(calls) >= 2


def test_dilutions_view_duplicate_delete_invalid_status_and_stale_flags(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel")]
    view = DilutionsView(app_state=state)

    view.add_btn.click()
    first_id = view._vm.selected_dilution_id
    assert first_id is not None
    view.inputs["name"].setText("Base")
    view.inputs["name"].editingFinished.emit()
    view.inputs["buffer1_ratio"].setText("1")
    view.inputs["buffer1_ratio"].editingFinished.emit()
    view.inputs["buffer2_ratio"].setText("2")
    view.inputs["buffer2_ratio"].editingFinished.emit()
    view.inputs["buffer3_ratio"].setText("3")
    view.inputs["buffer3_ratio"].editingFinished.emit()

    view.duplicate_btn.click()
    second_id = view._vm.selected_dilution_id
    assert second_id is not None and second_id != first_id

    view.inputs["buffer1_ratio"].setText("0")
    view.inputs["buffer1_ratio"].editingFinished.emit()
    assert view.status_label.text() in {"incomplete and invalid ratio", "invalid ratio"}
    assert "invalid-ratio" in view.provenance_labels["buffer1_ratio"].text()

    view.delete_btn.click()
    assert len(view._vm.dilutions) == 1
    assert view._vm.dilutions[0].dilution_id == first_id
    assert state.editor_state.manual_overrides["dilution_schemes"][0]["name"] == "Base"
    assert state.preview_state.stale is True
    assert state.validation_state.stale is True

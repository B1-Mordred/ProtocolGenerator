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


def test_sampleprep_view_emits_state_changed_on_mutations(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel")]
    calls = []
    view = SamplePrepView(app_state=state, on_state_changed=lambda: calls.append("changed"))

    view.add_btn.click()
    view.detail.inputs["Order"].setText("1")
    view.detail.inputs["Order"].editingFinished.emit()

    assert len(calls) >= 2


def test_sampleprep_view_add_edit_reorder_duplicate_delete_and_stale_flags(qapp):
    state = AppState()
    state.import_state.bundles = [InputDTOBundle(source_type="excel", hidden_vocab={"SamplePrepAction": ["Mix", "Heat"]})]
    view = SamplePrepView(app_state=state)

    view.add_btn.click()
    first_id = view._vm.selected_step_id
    assert first_id is not None
    view.detail.inputs["Order"].setText("1")
    view.detail.inputs["Order"].editingFinished.emit()
    view.detail.inputs["Action"].setText("Mix")
    view.detail.inputs["Action"].editingFinished.emit()

    view.add_btn.click()
    second_id = view._vm.selected_step_id
    assert second_id is not None and second_id != first_id
    view.detail.inputs["Order"].setText("2")
    view.detail.inputs["Order"].editingFinished.emit()
    view.detail.inputs["Action"].setText("Heat")
    view.detail.inputs["Action"].editingFinished.emit()
    view.detail.inputs["Source"].setText("A")
    view.detail.inputs["Source"].editingFinished.emit()
    view.detail.inputs["Destination"].setText("B")
    view.detail.inputs["Destination"].editingFinished.emit()

    view.table.selectRow(1)
    view.up_btn.click()
    assert view._vm.steps[0].step_id == second_id

    view.duplicate_btn.click()
    cloned_id = view._vm.selected_step_id
    assert cloned_id not in {None, first_id, second_id}
    assert len(view._vm.steps) == 3

    view.delete_btn.click()
    assert len(view._vm.steps) == 2
    assert all(step.step_id != cloned_id for step in view._vm.steps)
    assert state.editor_state.manual_overrides["sample_prep.steps"][0]["action"] == "Heat"
    assert state.preview_state.stale is True
    assert state.validation_state.stale is True

from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.field_mapping_view import FieldMappingView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_field_mapping_view_persists_template_rows(qapp) -> None:
    state = AppState()
    changed = []
    view = FieldMappingView(app_state=state, on_state_changed=lambda: changed.append(True))

    view._add_row()
    row = view.mapping_table.rowCount() - 1
    target = view.mapping_table.cellWidget(row, 1)
    target.setCurrentText("ProtocolFile.json:method.id")
    view.mapping_table.item(row, 2).setText("concat(input:method.kit_name, default:-, custom:v1)")

    view._save_current_template()

    settings = state.editor_state.export_settings["field_mapping"]
    assert settings["active_template"] == view.template_selector.currentText()
    assert settings["templates"][settings["active_template"]][0]["target"] == "ProtocolFile.json:method.id"
    assert changed

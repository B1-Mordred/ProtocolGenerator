from __future__ import annotations

import pytest

from addon_generator.ui.services.expression_validation import validate_mapping_expression

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QComboBox, QHeaderView
    from addon_generator.ui.state.app_state import AppState
    from addon_generator.ui.views.field_mapping_view import FieldMappingView
    QT_AVAILABLE = True
except Exception:  # pragma: no cover
    QT_AVAILABLE = False


@pytest.fixture(scope="module")
def qapp():
    if not QT_AVAILABLE:
        pytest.skip("PySide6 Qt runtime unavailable")
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
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


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_target_column_auto_sizes_to_content(qapp) -> None:
    view = FieldMappingView(app_state=AppState())

    assert view.mapping_table.horizontalHeader().sectionResizeMode(1) == QHeaderView.ResizeMode.ResizeToContents

    view._add_row()
    target_widget = view.mapping_table.cellWidget(0, 1)
    assert isinstance(target_widget, QComboBox)
    assert target_widget.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents


@pytest.mark.parametrize(
    ("expression", "is_valid"),
    [
        ("input:method.kit_name", True),
        ("default:BASIC", True),
        ("custom:My Value", True),
        ("concat(input:method.kit_name, default:-, custom:v1)", True),
        ("concat(delimiter='-', input:method.kit_name, custom:v1)", True),
        ("concat(delimiter=-, input:method.kit_name)", False),
        ("concat(input:method.kit_name", False),
        ("unsupported:value", False),
        ("input:method.kit_name, default:v2", False),
    ],
)
def test_validate_mapping_expression(expression: str, is_valid: bool) -> None:
    assert validate_mapping_expression(expression).is_valid is is_valid


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_save_blocked_for_invalid_enabled_rows(qapp, monkeypatch) -> None:
    state = AppState()
    view = FieldMappingView(app_state=state)
    called = []
    monkeypatch.setattr("addon_generator.ui.views.field_mapping_view.QMessageBox.warning", lambda *args, **kwargs: called.append(True))

    view._add_row()
    row = view.mapping_table.rowCount() - 1
    target_widget = view.mapping_table.cellWidget(row, 1)
    target_widget.setCurrentText("ProtocolFile.json:method.id")
    view.mapping_table.item(row, 2).setText("unsupported:value")

    view._save_current_template()

    assert called
    assert view.mapping_table.item(row, 3).text().startswith("❌ Error:")
    active = state.editor_state.export_settings["field_mapping"]["active_template"]
    assert state.editor_state.export_settings["field_mapping"]["templates"][active] == []


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_allows_save_for_invalid_disabled_rows(qapp) -> None:
    state = AppState()
    view = FieldMappingView(app_state=state)

    view._add_row()
    row = view.mapping_table.rowCount() - 1
    view.mapping_table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)
    target_widget = view.mapping_table.cellWidget(row, 1)
    target_widget.setCurrentText("ProtocolFile.json:method.id")
    view.mapping_table.item(row, 2).setText("unsupported:value")

    view._save_current_template()

    active = state.editor_state.export_settings["field_mapping"]["active_template"]
    saved = state.editor_state.export_settings["field_mapping"]["templates"][active]
    assert saved and saved[0]["enabled"] is False
    assert view.mapping_table.item(row, 3).text().startswith("⚠️ Disabled row:")

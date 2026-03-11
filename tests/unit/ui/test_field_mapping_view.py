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
    target.setCurrentText("ProtocolFile.json:MethodInformation.Id")
    view.mapping_table.item(row, 2).setText("concat(input:method.kit_name, default:-, custom:v1)")

    view._save_current_template()

    settings = state.editor_state.export_settings["field_mapping"]
    assert settings["active_template"] == view.template_selector.currentText()
    assert settings["templates"][settings["active_template"]][0]["target"] == "ProtocolFile.json:MethodInformation.Id"
    assert changed


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_target_column_auto_sizes_to_content(qapp) -> None:
    view = FieldMappingView(app_state=AppState())

    assert view.mapping_table.horizontalHeader().sectionResizeMode(1) == QHeaderView.ResizeMode.ResizeToContents

    view._add_row()
    target_widget = view.mapping_table.cellWidget(0, 1)
    assert isinstance(target_widget, QComboBox)
    assert target_widget.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_target_picker_keeps_legacy_serialized_value(qapp) -> None:
    legacy_target = "ProtocolFile.json:method.id"
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {"Default": [{"enabled": True, "target": legacy_target, "expression": "input:method.kit_name"}]},
    }

    view = FieldMappingView(app_state=state)
    target_widget = view.mapping_table.cellWidget(0, 1)
    assert isinstance(target_widget, QComboBox)
    assert target_widget.currentText() == legacy_target

    saved_rows = view._collect_rows()
    assert saved_rows[0]["target"] == legacy_target


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_preview_normalizes_legacy_target_paths(qapp) -> None:
    state = AppState()
    state.editor_state.effective_values = {"method": {"kit_name": "Kit-A"}}
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {
            "Default": [
                {"enabled": True, "target": "ProtocolFile.json:method.id", "expression": "input:method.kit_name"},
            ]
        },
    }

    view = FieldMappingView(app_state=state)
    protocol_preview = view._preview_text_by_artifact["ProtocolFile.json"].toPlainText()
    assert "MethodInformation.Id = Kit-A" in protocol_preview


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_token_picker_keeps_legacy_serialized_value(qapp) -> None:
    view = FieldMappingView(app_state=AppState())

    view.token_selector.setCurrentText("input:method.kit_name")
    assert view._combo_value(view.token_selector) == "input:method.kit_name"


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_target_picker_items_have_help_tooltips(qapp) -> None:
    view = FieldMappingView(app_state=AppState())

    view._add_row()
    target_widget = view.mapping_table.cellWidget(0, 1)
    assert isinstance(target_widget, QComboBox)
    first_selectable = next(i for i in range(target_widget.count()) if target_widget.itemData(i) is not None)
    tooltip = target_widget.itemData(first_selectable, Qt.ItemDataRole.ToolTipRole)
    assert isinstance(tooltip, str) and tooltip




@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_new_template_uses_next_available_name(qapp) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {"Default": [], "Template": [], "Template 2": []},
    }
    view = FieldMappingView(app_state=state)

    view._new_template()

    assert "Template 3" in state.editor_state.export_settings["field_mapping"]["templates"]


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_duplicate_template_generates_conflict_free_name(qapp) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {"Default": [], "Default Copy": [], "Default Copy 2": []},
    }
    view = FieldMappingView(app_state=state)

    view._duplicate_template()

    assert "Default Copy 3" in state.editor_state.export_settings["field_mapping"]["templates"]


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_validate_template_name_rules(qapp) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {"Default": [], "Existing": []},
    }
    view = FieldMappingView(app_state=state)

    assert view._validate_template_name("   ") == (None, "Template name is required.")
    assert view._validate_template_name(" Default ", current_name="Existing") == (None, "Template name 'Default' is reserved.")
    assert view._validate_template_name("Existing") == (None, "Template 'Existing' already exists.")
    assert view._validate_template_name("Default", current_name="Default") == (None, "Default template cannot be renamed.")
    assert view._validate_template_name("  New Name  ") == ("New Name", None)


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_rename_template_rejects_duplicates(qapp, monkeypatch) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Custom",
        "templates": {"Default": [], "Custom": [], "Custom 2": []},
    }
    view = FieldMappingView(app_state=state)
    warned = []
    monkeypatch.setattr("addon_generator.ui.views.field_mapping_view.QInputDialog.getText", lambda *a, **k: ("Custom 2", True))
    monkeypatch.setattr("addon_generator.ui.views.field_mapping_view.QMessageBox.warning", lambda *a, **k: warned.append(True))

    view.template_selector.setCurrentText("Custom")
    view._rename_template()

    assert warned
    assert "Custom" in state.editor_state.export_settings["field_mapping"]["templates"]
    assert "Custom 2" in state.editor_state.export_settings["field_mapping"]["templates"]


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_delete_template_requires_confirmation_and_shows_usage(qapp, monkeypatch) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {"Default": [], "Custom": []},
    }
    view = FieldMappingView(app_state=state)
    prompts = []

    def fake_question(*args, **kwargs):
        prompts.append(args[2])
        return QMessageBox.StandardButton.No

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("addon_generator.ui.views.field_mapping_view.QMessageBox.question", fake_question)

    view.template_selector.setCurrentText("Custom")
    view._delete_template()

    assert prompts
    assert "Active template remains 'Default'." in prompts[0]
    assert "Custom" in state.editor_state.export_settings["field_mapping"]["templates"]



@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_delete_active_template_confirmation_updates_active(qapp, monkeypatch) -> None:
    state = AppState()
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Custom",
        "templates": {"Default": [], "Custom": []},
    }
    view = FieldMappingView(app_state=state)
    prompts = []

    def fake_question(*args, **kwargs):
        prompts.append(args[2])
        return QMessageBox.StandardButton.Yes

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("addon_generator.ui.views.field_mapping_view.QMessageBox.question", fake_question)

    view.template_selector.setCurrentText("Custom")
    view._delete_template()

    assert prompts
    assert "This template is currently active." in prompts[0]
    assert "Custom" not in state.editor_state.export_settings["field_mapping"]["templates"]
    assert state.editor_state.export_settings["field_mapping"]["active_template"] == "Default"

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
    target_widget.setCurrentText("ProtocolFile.json:MethodInformation.Id")
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
    target_widget.setCurrentText("ProtocolFile.json:MethodInformation.Id")
    view.mapping_table.item(row, 2).setText("unsupported:value")

    view._save_current_template()

    active = state.editor_state.export_settings["field_mapping"]["active_template"]
    saved = state.editor_state.export_settings["field_mapping"]["templates"][active]
    assert saved and saved[0]["enabled"] is False
    assert view.mapping_table.item(row, 3).text().startswith("⚠️ Disabled row:")


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_preview_updates_after_row_edits(qapp) -> None:
    state = AppState()
    state.editor_state.effective_values = {
        "method": {"kit_name": "Kit-A"},
        "analytes": [{"name": "Na"}, {"name": "K"}],
    }
    view = FieldMappingView(app_state=state)

    view._add_row()
    target_widget = view.mapping_table.cellWidget(0, 1)
    assert isinstance(target_widget, QComboBox)
    target_widget.setCurrentText("ProtocolFile.json:MethodInformation.Id")
    view.mapping_table.item(0, 2).setText("input:method.kit_name")

    protocol_preview = view._preview_text_by_artifact["ProtocolFile.json"].toPlainText()
    assert "MethodInformation.Id = Kit-A" in protocol_preview

    view.mapping_table.item(0, 2).setText("input:method.missing_value")
    protocol_preview = view._preview_text_by_artifact["ProtocolFile.json"].toPlainText()
    assert "MethodInformation.Id = <missing:method.missing_value>" in protocol_preview
    assert "No source value for input:method.missing_value" in view.preview_status_label.toolTip()


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_preview_updates_when_switching_templates(qapp) -> None:
    state = AppState()
    state.editor_state.effective_values = {
        "method": {"kit_name": "Kit-A", "kit_series": "Series-1"},
    }
    state.editor_state.export_settings["field_mapping"] = {
        "active_template": "Default",
        "templates": {
            "Default": [{"enabled": True, "target": "ProtocolFile.json:MethodInformation.Id", "expression": "input:method.kit_name"}],
            "Alt": [{"enabled": True, "target": "ProtocolFile.json:MethodInformation.Version", "expression": "input:method.kit_series"}],
        },
    }
    view = FieldMappingView(app_state=state)

    assert "MethodInformation.Id = Kit-A" in view._preview_text_by_artifact["ProtocolFile.json"].toPlainText()

    view.template_selector.setCurrentText("Alt")

    updated = view._preview_text_by_artifact["ProtocolFile.json"].toPlainText()
    assert "MethodInformation.Version = Series-1" in updated
    assert "MethodInformation.Id = Kit-A" not in updated


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_remove_selected_rows_removes_all_selected(qapp) -> None:
    view = FieldMappingView(app_state=AppState())

    for _ in range(4):
        view._add_row()

    model = view.mapping_table.selectionModel()
    model.select(view.mapping_table.model().index(1, 0), model.SelectionFlag.Select | model.SelectionFlag.Rows)
    model.select(view.mapping_table.model().index(3, 0), model.SelectionFlag.Select | model.SelectionFlag.Rows)

    view._remove_row()

    assert view.mapping_table.rowCount() == 2


@pytest.mark.skipif(not QT_AVAILABLE, reason="PySide6 Qt runtime unavailable")
def test_field_mapping_row_reorder_persists_after_save_and_reload(qapp) -> None:
    state = AppState()
    view = FieldMappingView(app_state=state)

    view._add_row()
    view._add_row()

    first_target = view.mapping_table.cellWidget(0, 1)
    first_target.setCurrentText("ProtocolFile.json:MethodInformation.Id")
    view.mapping_table.item(0, 2).setText("input:method.kit_name")

    second_target = view.mapping_table.cellWidget(1, 1)
    second_target.setCurrentText("ProtocolFile.json:MethodInformation.Version")
    view.mapping_table.item(1, 2).setText("default:v2")

    view.mapping_table.selectRow(1)
    view._move_selected_rows(-1)
    view._save_current_template()

    view._load_template(view.template_selector.currentText())
    saved_rows = view._collect_rows()

    assert saved_rows[0]["target"] == "ProtocolFile.json:MethodInformation.Version"
    assert saved_rows[0]["expression"] == "default:v2"
    assert saved_rows[1]["target"] == "ProtocolFile.json:MethodInformation.Id"
    assert saved_rows[1]["expression"] == "input:method.kit_name"

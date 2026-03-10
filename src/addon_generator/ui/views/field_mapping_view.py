from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from addon_generator.ui.state.app_state import AppState


TARGET_OPTIONS = [
    "Analytes.xml:Analyte@name",
    "Analytes.xml:Analyte@unit",
    "AddOn.xml:MethodInformation/MethodName",
    "AddOn.xml:MethodInformation/MethodId",
    "ProtocolFile.json:method.id",
    "ProtocolFile.json:method.version",
    "ProtocolFile.json:analytes[].name",
]

SOURCE_TOKEN_OPTIONS = [
    "input:method.kit_series",
    "input:method.kit_name",
    "input:method.kit_product_number",
    "input:method.addon_product_name",
    "input:assays[].component_name",
    "input:assays[].parameter_set_name",
    "input:analytes[].name",
    "default:BASIC Kit",
    "default:1",
    "custom:",
]


@dataclass
class MappingRow:
    target: str
    expression: str
    enabled: bool = True


class FieldMappingView(QWidget):
    def __init__(self, parent=None, *, app_state: AppState | None = None, on_state_changed: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        self._app_state = app_state or AppState()
        self._on_state_changed = on_state_changed

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Configure field mapping templates for Analytes.xml/AddOn.xml/ProtocolFile.json"))

        template_row = QHBoxLayout()
        self.template_selector = QComboBox(self)
        self.new_template_btn = QPushButton("New Template", self)
        self.duplicate_template_btn = QPushButton("Duplicate", self)
        self.delete_template_btn = QPushButton("Delete", self)
        self.set_active_btn = QPushButton("Set Active", self)
        for w in (self.template_selector, self.new_template_btn, self.duplicate_template_btn, self.delete_template_btn, self.set_active_btn):
            template_row.addWidget(w)
        root.addLayout(template_row)

        self.mapping_table = QTableWidget(self)
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(["Enabled", "Target Field", "Source Expression"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.mapping_table)

        map_actions = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Mapping", self)
        self.remove_row_btn = QPushButton("Remove Selected", self)
        self.save_template_btn = QPushButton("Save Template", self)
        for w in (self.add_row_btn, self.remove_row_btn, self.save_template_btn):
            map_actions.addWidget(w)
        map_actions.addStretch(1)
        root.addLayout(map_actions)

        helper = QGroupBox("Expression Builder", self)
        helper_layout = QFormLayout(helper)
        self.token_selector = QComboBox(self)
        self.token_selector.addItems(SOURCE_TOKEN_OPTIONS)
        self.custom_literal = QLineEdit(self)
        self.custom_literal.setPlaceholderText("custom literal value")
        self.delimiter_input = QLineEdit(self)
        self.delimiter_input.setPlaceholderText("concat delimiter, default=' '")
        self.append_token_btn = QPushButton("Append Token to Selected", self)
        self.wrap_concat_btn = QPushButton("Wrap Selected as concat(...) ", self)
        self.expression_help = QTextEdit(self)
        self.expression_help.setReadOnly(True)
        self.expression_help.setPlainText(
            "Use expressions like:\n"
            "- input:method.kit_name\n"
            "- default:BASIC Kit\n"
            "- custom:My Value\n"
            "- concat(input:method.kit_name, default:-, custom:v1)"
        )
        helper_layout.addRow("Token", self.token_selector)
        helper_layout.addRow("Custom", self.custom_literal)
        helper_layout.addRow("Delimiter", self.delimiter_input)
        helper_layout.addRow(self.append_token_btn)
        helper_layout.addRow(self.wrap_concat_btn)
        helper_layout.addRow(self.expression_help)
        root.addWidget(helper)

        self.new_template_btn.clicked.connect(self._new_template)
        self.duplicate_template_btn.clicked.connect(self._duplicate_template)
        self.delete_template_btn.clicked.connect(self._delete_template)
        self.set_active_btn.clicked.connect(self._set_active_template)
        self.add_row_btn.clicked.connect(self._add_row)
        self.remove_row_btn.clicked.connect(self._remove_row)
        self.save_template_btn.clicked.connect(self._save_current_template)
        self.template_selector.currentTextChanged.connect(self._load_template)
        self.append_token_btn.clicked.connect(self._append_token)
        self.wrap_concat_btn.clicked.connect(self._wrap_concat)

        self._ensure_mapping_settings()
        self._refresh_templates()

    def _ensure_mapping_settings(self) -> None:
        settings = self._app_state.editor_state.export_settings
        mapping_settings = settings.setdefault("field_mapping", {})
        mapping_settings.setdefault("templates", {"Default": []})
        mapping_settings.setdefault("active_template", "Default")

    def _refresh_templates(self) -> None:
        templates = self._templates()
        active = self._active_template_name()
        self.template_selector.blockSignals(True)
        self.template_selector.clear()
        self.template_selector.addItems(list(templates.keys()))
        if active in templates:
            self.template_selector.setCurrentText(active)
        self.template_selector.blockSignals(False)
        self._load_template(self.template_selector.currentText() or active)

    def _templates(self) -> dict[str, list[dict[str, object]]]:
        return self._app_state.editor_state.export_settings["field_mapping"]["templates"]

    def _active_template_name(self) -> str:
        return str(self._app_state.editor_state.export_settings["field_mapping"].get("active_template", "Default"))

    def _load_template(self, name: str) -> None:
        rows = self._templates().get(name, [])
        self.mapping_table.setRowCount(len(rows))
        for idx, row in enumerate(rows):
            enabled = bool(row.get("enabled", True))
            enabled_item = QTableWidgetItem("Yes" if enabled else "No")
            enabled_item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.mapping_table.setItem(idx, 0, enabled_item)

            target_box = QComboBox(self.mapping_table)
            target_box.addItems(TARGET_OPTIONS)
            target_box.setEditable(True)
            target_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            target_box.setCurrentText(str(row.get("target", "")))
            self.mapping_table.setCellWidget(idx, 1, target_box)

            expr_item = QTableWidgetItem(str(row.get("expression", "")))
            self.mapping_table.setItem(idx, 2, expr_item)
        self.mapping_table.resizeColumnsToContents()

    def _collect_rows(self) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for idx in range(self.mapping_table.rowCount()):
            enabled_item = self.mapping_table.item(idx, 0)
            enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
            target_widget = self.mapping_table.cellWidget(idx, 1)
            target = target_widget.currentText().strip() if isinstance(target_widget, QComboBox) else ""
            expr_item = self.mapping_table.item(idx, 2)
            expression = expr_item.text().strip() if expr_item else ""
            if target or expression:
                output.append({"enabled": enabled, "target": target, "expression": expression})
        return output

    def _save_current_template(self) -> None:
        name = self.template_selector.currentText().strip() or self._active_template_name()
        if not name:
            return
        self._templates()[name] = self._collect_rows()
        self._app_state.editor_state.export_settings["field_mapping"]["active_template"] = name
        self._notify_change()

    def _new_template(self) -> None:
        name = f"Template {len(self._templates()) + 1}"
        self._templates()[name] = []
        self._refresh_templates()
        self.template_selector.setCurrentText(name)

    def _duplicate_template(self) -> None:
        source = self.template_selector.currentText().strip()
        if not source:
            return
        clone_name = f"{source} Copy"
        self._templates()[clone_name] = [dict(row) for row in self._templates().get(source, [])]
        self._refresh_templates()
        self.template_selector.setCurrentText(clone_name)

    def _delete_template(self) -> None:
        name = self.template_selector.currentText().strip()
        templates = self._templates()
        if name == "Default":
            QMessageBox.information(self, "Field Mapping", "Default template cannot be deleted.")
            return
        templates.pop(name, None)
        if not templates:
            templates["Default"] = []
        self._app_state.editor_state.export_settings["field_mapping"]["active_template"] = next(iter(templates.keys()))
        self._refresh_templates()
        self._notify_change()

    def _set_active_template(self) -> None:
        name = self.template_selector.currentText().strip()
        if not name:
            return
        self._save_current_template()
        QMessageBox.information(self, "Field Mapping", f"Active mapping template set to '{name}'.")

    def _add_row(self) -> None:
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        enabled_item = QTableWidgetItem("Yes")
        enabled_item.setCheckState(Qt.CheckState.Checked)
        self.mapping_table.setItem(row, 0, enabled_item)
        target_box = QComboBox(self.mapping_table)
        target_box.setEditable(True)
        target_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        target_box.addItems(TARGET_OPTIONS)
        self.mapping_table.setCellWidget(row, 1, target_box)
        self.mapping_table.setItem(row, 2, QTableWidgetItem(""))

    def _remove_row(self) -> None:
        selected = self.mapping_table.selectionModel().selectedRows()
        if not selected:
            return
        self.mapping_table.removeRow(selected[0].row())

    def _append_token(self) -> None:
        selected = self.mapping_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        expr_item = self.mapping_table.item(row, 2)
        if expr_item is None:
            expr_item = QTableWidgetItem("")
            self.mapping_table.setItem(row, 2, expr_item)
        token = self.token_selector.currentText().strip()
        if token == "custom:":
            token = f"custom:{self.custom_literal.text().strip()}"
        prefix = expr_item.text().strip()
        expr_item.setText(f"{prefix}, {token}" if prefix else token)

    def _wrap_concat(self) -> None:
        selected = self.mapping_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        expr_item = self.mapping_table.item(row, 2)
        if expr_item is None:
            return
        expr = expr_item.text().strip()
        if not expr:
            return
        delimiter = self.delimiter_input.text().strip()
        if delimiter:
            expr_item.setText(f"concat(delimiter='{delimiter}', {expr})")
        else:
            expr_item.setText(f"concat({expr})")

    def _notify_change(self) -> None:
        if self._on_state_changed:
            self._on_state_changed()

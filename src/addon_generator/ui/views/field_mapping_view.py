from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QStandardItem
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QMenu,
    QPushButton,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.services.expression_validation import validate_mapping_expression


@dataclass(frozen=True)
class PickerOption:
    label: str
    value: str
    help_text: str


TARGET_OPTIONS = [
    PickerOption("Analyte Name", "Analytes.xml:Analyte@name", "Writes into each analyte's @name attribute in Analytes.xml."),
    PickerOption("Analyte Unit", "Analytes.xml:Analyte@unit", "Writes into each analyte's @unit attribute in Analytes.xml."),
    PickerOption("Method Name", "AddOn.xml:MethodInformation/MethodName", "Writes to AddOn.xml MethodInformation/MethodName."),
    PickerOption("Method ID", "AddOn.xml:MethodInformation/MethodId", "Writes to AddOn.xml MethodInformation/MethodId."),
    PickerOption("Method ID", "ProtocolFile.json:method.id", "Writes to ProtocolFile.json method.id."),
    PickerOption("Method Version", "ProtocolFile.json:method.version", "Writes to ProtocolFile.json method.version."),
    PickerOption("Analyte Names", "ProtocolFile.json:analytes[].name", "Writes each analyte name entry into ProtocolFile.json analytes[].name."),
]

SOURCE_TOKEN_OPTIONS = [
    PickerOption("Kit Series", "input:method.kit_series", "Reads the imported/manual method.kit_series input field."),
    PickerOption("Kit Name", "input:method.kit_name", "Reads the imported/manual method.kit_name input field."),
    PickerOption("Kit Product Number", "input:method.kit_product_number", "Reads the imported/manual method.kit_product_number input field."),
    PickerOption("Addon Product Name", "input:method.addon_product_name", "Reads the imported/manual method.addon_product_name input field."),
    PickerOption("Assay Component Name", "input:assays[].component_name", "Reads each assay component_name input value."),
    PickerOption("Assay Parameter Set", "input:assays[].parameter_set_name", "Reads each assay parameter_set_name input value."),
    PickerOption("Analyte Name", "input:analytes[].name", "Reads each analyte name from input rows."),
    PickerOption("Default BASIC Kit", "default:BASIC Kit", "Uses a constant literal value BASIC Kit for every mapped row."),
    PickerOption("Default 1", "default:1", "Uses a constant literal value 1 for every mapped row."),
    PickerOption("Custom Literal", "custom:", "Begins a custom literal token; value comes from the Custom input textbox."),
]

TARGET_OPTION_GROUPS = {
    "Analytes.xml": ("Analytes.xml:Analyte@name", "Analytes.xml:Analyte@unit"),
    "AddOn.xml": ("AddOn.xml:MethodInformation/MethodName", "AddOn.xml:MethodInformation/MethodId"),
    "ProtocolFile.json": ("ProtocolFile.json:method.id", "ProtocolFile.json:method.version", "ProtocolFile.json:analytes[].name"),
}

SOURCE_OPTION_GROUPS = {
    "Method Inputs": (
        "input:method.kit_series",
        "input:method.kit_name",
        "input:method.kit_product_number",
        "input:method.addon_product_name",
    ),
    "Assay Inputs": ("input:assays[].component_name", "input:assays[].parameter_set_name"),
    "Analyte Inputs": ("input:analytes[].name",),
    "Defaults / Custom": ("default:BASIC Kit", "default:1", "custom:"),
}


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
        self.rename_template_btn = QPushButton("Rename", self)
        self.delete_template_btn = QPushButton("Delete", self)
        self.set_active_btn = QPushButton("Set Active", self)
        for w in (
            self.template_selector,
            self.new_template_btn,
            self.duplicate_template_btn,
            self.rename_template_btn,
            self.delete_template_btn,
            self.set_active_btn,
        ):
            template_row.addWidget(w)
        root.addLayout(template_row)

        self.mapping_table = QTableWidget(self)
        self.mapping_table.setColumnCount(4)
        self.mapping_table.setHorizontalHeaderLabels(["Enabled", "Target Field", "Source Expression", "Status"])
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mapping_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.mapping_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.mapping_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.mapping_table.horizontalHeader().setStretchLastSection(False)
        self.mapping_table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.mapping_table)

        map_actions = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Mapping", self)
        self.remove_row_btn = QPushButton("Remove Selected", self)
        self.duplicate_row_btn = QPushButton("Duplicate Selected", self)
        self.move_row_up_btn = QPushButton("Move Up", self)
        self.move_row_down_btn = QPushButton("Move Down", self)
        self.enable_rows_btn = QPushButton("Enable Selected", self)
        self.disable_rows_btn = QPushButton("Disable Selected", self)
        self.save_template_btn = QPushButton("Save Template", self)
        for w in (
            self.add_row_btn,
            self.remove_row_btn,
            self.duplicate_row_btn,
            self.move_row_up_btn,
            self.move_row_down_btn,
            self.enable_rows_btn,
            self.disable_rows_btn,
            self.save_template_btn,
        ):
            map_actions.addWidget(w)
        map_actions.addStretch(1)
        root.addLayout(map_actions)

        preview_group = QGroupBox("Preview", self)
        preview_layout = QVBoxLayout(preview_group)
        preview_header = QHBoxLayout()
        self.preview_status_label = QLabel("", preview_group)
        self.refresh_preview_btn = QPushButton("Refresh Preview", preview_group)
        preview_header.addWidget(self.preview_status_label)
        preview_header.addStretch(1)
        preview_header.addWidget(self.refresh_preview_btn)
        preview_layout.addLayout(preview_header)

        self.preview_tabs = QTabWidget(preview_group)
        self._preview_text_by_artifact: dict[str, QTextEdit] = {}
        for artifact_name in ("Analytes.xml", "AddOn.xml", "ProtocolFile.json"):
            artifact_text = QTextEdit(self.preview_tabs)
            artifact_text.setReadOnly(True)
            self._preview_text_by_artifact[artifact_name] = artifact_text
            self.preview_tabs.addTab(artifact_text, artifact_name)
        preview_layout.addWidget(self.preview_tabs)
        root.addWidget(preview_group)

        helper = QGroupBox("Expression Builder", self)
        helper_layout = QFormLayout(helper)
        self.token_selector = self._create_picker_combo(SOURCE_TOKEN_OPTIONS, SOURCE_OPTION_GROUPS)
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
            "- concat(input:method.kit_name, default:-, custom:v1)\n"
            "- concat(delimiter='-', input:method.kit_name, custom:v1)"
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
        self.rename_template_btn.clicked.connect(self._rename_template)
        self.delete_template_btn.clicked.connect(self._delete_template)
        self.set_active_btn.clicked.connect(self._set_active_template)
        self.add_row_btn.clicked.connect(self._add_row)
        self.remove_row_btn.clicked.connect(self._remove_row)
        self.duplicate_row_btn.clicked.connect(self._duplicate_selected_rows)
        self.move_row_up_btn.clicked.connect(lambda: self._move_selected_rows(-1))
        self.move_row_down_btn.clicked.connect(lambda: self._move_selected_rows(1))
        self.enable_rows_btn.clicked.connect(lambda: self._set_selected_enabled(True))
        self.disable_rows_btn.clicked.connect(lambda: self._set_selected_enabled(False))
        self.save_template_btn.clicked.connect(self._save_current_template)
        self.template_selector.currentTextChanged.connect(self._load_template)
        self.append_token_btn.clicked.connect(self._append_token)
        self.wrap_concat_btn.clicked.connect(self._wrap_concat)
        self.refresh_preview_btn.clicked.connect(self._refresh_preview)
        self.mapping_table.customContextMenuRequested.connect(self._show_mapping_table_context_menu)

        QShortcut(QKeySequence(Qt.Key.Key_Delete), self.mapping_table, activated=self._remove_row)
        QShortcut(QKeySequence("Ctrl+D"), self.mapping_table, activated=self._duplicate_selected_rows)
        QShortcut(QKeySequence("Alt+Up"), self.mapping_table, activated=lambda: self._move_selected_rows(-1))
        QShortcut(QKeySequence("Alt+Down"), self.mapping_table, activated=lambda: self._move_selected_rows(1))

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

            target_box = self._create_picker_combo(TARGET_OPTIONS, TARGET_OPTION_GROUPS)
            target_box.setCurrentText(str(row.get("target", "")))
            target_box.currentTextChanged.connect(lambda _value, combo=target_box: self._on_target_changed_for_combo(combo))
            self.mapping_table.setCellWidget(idx, 1, target_box)

            expr_item = QTableWidgetItem(str(row.get("expression", "")))
            self.mapping_table.setItem(idx, 2, expr_item)
            self._set_status_item(idx, "")
            self._validate_row(idx)
        self.mapping_table.resizeColumnsToContents()
        self._refresh_preview()

    def _collect_rows(self) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for idx in range(self.mapping_table.rowCount()):
            enabled_item = self.mapping_table.item(idx, 0)
            enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
            target_widget = self.mapping_table.cellWidget(idx, 1)
            target = self._combo_value(target_widget) if isinstance(target_widget, QComboBox) else ""
            expr_item = self.mapping_table.item(idx, 2)
            expression = expr_item.text().strip() if expr_item else ""
            if target or expression:
                output.append({"enabled": enabled, "target": target, "expression": expression})
        return output

    def _save_current_template(self) -> None:
        name = self.template_selector.currentText().strip() or self._active_template_name()
        if not name:
            return
        if not self._validate_all_rows_for_save():
            QMessageBox.warning(self, "Field Mapping", "Cannot save while enabled rows contain invalid expressions.")
            return
        self._templates()[name] = self._collect_rows()
        self._app_state.editor_state.export_settings["field_mapping"]["active_template"] = name
        self._notify_change()
        self._refresh_preview()

    def _new_template(self) -> None:
        name = self._next_available_template_name("Template")
        self._templates()[name] = []
        self._refresh_templates()
        self.template_selector.setCurrentText(name)

    def _duplicate_template(self) -> None:
        source = self.template_selector.currentText().strip()
        if not source:
            return
        clone_name = self._next_available_template_name(f"{source} Copy")
        self._templates()[clone_name] = [dict(row) for row in self._templates().get(source, [])]
        self._refresh_templates()
        self.template_selector.setCurrentText(clone_name)

    def _rename_template(self) -> None:
        current_name = self.template_selector.currentText().strip()
        if not current_name:
            return
        entered_name, accepted = QInputDialog.getText(self, "Rename Template", "New template name:", text=current_name)
        if not accepted:
            return
        valid_name, error = self._validate_template_name(entered_name, current_name=current_name)
        if error:
            QMessageBox.warning(self, "Field Mapping", error)
            return
        if not valid_name or valid_name == current_name:
            return

        templates = self._templates()
        templates[valid_name] = templates.pop(current_name)
        if self._active_template_name() == current_name:
            self._app_state.editor_state.export_settings["field_mapping"]["active_template"] = valid_name
        self._refresh_templates()
        self.template_selector.setCurrentText(valid_name)
        self._notify_change()

    def _delete_template(self) -> None:
        name = self.template_selector.currentText().strip()
        templates = self._templates()
        if name == "Default":
            QMessageBox.information(self, "Field Mapping", "Default template cannot be deleted.")
            return
        active_name = self._active_template_name()
        usage_context = "This template is currently active." if name == active_name else f"Active template remains '{active_name}'."
        response = QMessageBox.question(
            self,
            "Delete Template",
            f"Delete template '{name}'?\n{usage_context}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        templates.pop(name, None)
        if not templates:
            templates["Default"] = []
        if name == active_name:
            self._app_state.editor_state.export_settings["field_mapping"]["active_template"] = next(iter(templates.keys()))
        self._refresh_templates()
        self._notify_change()

    def _validate_template_name(self, name: str, *, current_name: str | None = None) -> tuple[str | None, str | None]:
        normalized = name.strip()
        if not normalized:
            return None, "Template name is required."
        if current_name == "Default":
            return None, "Default template cannot be renamed."
        if normalized == "Default" and current_name != "Default":
            return None, "Template name 'Default' is reserved."
        if normalized in self._templates() and normalized != current_name:
            return None, f"Template '{normalized}' already exists."
        return normalized, None

    def _next_available_template_name(self, base_name: str) -> str:
        normalized = base_name.strip() or "Template"
        templates = self._templates()
        if normalized not in templates:
            return normalized
        index = 2
        while True:
            candidate = f"{normalized} {index}"
            if candidate not in templates:
                return candidate
            index += 1

    def _set_active_template(self) -> None:
        name = self.template_selector.currentText().strip()
        if not name:
            return
        if not self._validate_all_rows_for_save():
            QMessageBox.warning(self, "Field Mapping", "Cannot activate while enabled rows contain invalid expressions.")
            return
        self._save_current_template()
        QMessageBox.information(self, "Field Mapping", f"Active mapping template set to '{name}'.")

    def _add_row(self) -> None:
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        enabled_item = QTableWidgetItem("Yes")
        enabled_item.setCheckState(Qt.CheckState.Checked)
        self.mapping_table.setItem(row, 0, enabled_item)
        target_box = self._create_picker_combo(TARGET_OPTIONS, TARGET_OPTION_GROUPS)
        target_box.currentTextChanged.connect(lambda _value, combo=target_box: self._on_target_changed_for_combo(combo))
        self.mapping_table.setCellWidget(row, 1, target_box)
        self.mapping_table.setItem(row, 2, QTableWidgetItem(""))
        self._set_status_item(row, "⚠️ Error: Expression is required")
        self._refresh_preview()

    def _remove_row(self) -> None:
        selected_rows = self._selected_row_indexes()
        if not selected_rows:
            return
        for row in sorted(selected_rows, reverse=True):
            self.mapping_table.removeRow(row)
        self._refresh_preview()

    def _duplicate_selected_rows(self) -> None:
        selected_rows = self._selected_row_indexes()
        if not selected_rows:
            return
        rows = self._table_row_snapshots()
        inserts = [(row + 1 + offset, rows[row]) for offset, row in enumerate(selected_rows)]
        for insert_idx, row_data in inserts:
            rows.insert(insert_idx, row_data)
        duplicated_rows = [insert_idx for insert_idx, _row_data in inserts]
        self._apply_table_row_snapshots(rows, selected_rows=duplicated_rows)

    def _move_selected_rows(self, direction: int) -> None:
        selected_rows = self._selected_row_indexes()
        if not selected_rows:
            return
        rows = self._table_row_snapshots()
        row_count = len(rows)
        if direction < 0:
            for row in selected_rows:
                if row > 0 and (row - 1) not in selected_rows:
                    rows[row - 1], rows[row] = rows[row], rows[row - 1]
            new_selection = [max(0, row - 1) if row > 0 and (row - 1) not in selected_rows else row for row in selected_rows]
        else:
            for row in reversed(selected_rows):
                if row < row_count - 1 and (row + 1) not in selected_rows:
                    rows[row + 1], rows[row] = rows[row], rows[row + 1]
            new_selection = [min(row_count - 1, row + 1) if row < row_count - 1 and (row + 1) not in selected_rows else row for row in selected_rows]
        self._apply_table_row_snapshots(rows, selected_rows=new_selection)

    def _set_selected_enabled(self, enabled: bool) -> None:
        selected_rows = self._selected_row_indexes()
        if not selected_rows:
            return
        state = Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
        for row in selected_rows:
            enabled_item = self.mapping_table.item(row, 0)
            if enabled_item is None:
                enabled_item = QTableWidgetItem("Yes" if enabled else "No")
                self.mapping_table.setItem(row, 0, enabled_item)
            enabled_item.setCheckState(state)
            self._validate_row(row)
        self._refresh_preview()

    def _append_token(self) -> None:
        selected = self.mapping_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        expr_item = self.mapping_table.item(row, 2)
        if expr_item is None:
            expr_item = QTableWidgetItem("")
            self.mapping_table.setItem(row, 2, expr_item)
        token = self._combo_value(self.token_selector)
        if token == "custom:":
            token = f"custom:{self.custom_literal.text().strip()}"
        prefix = expr_item.text().strip()
        expr_item.setText(f"{prefix}, {token}" if prefix else token)
        self._validate_row(row)
        self._refresh_preview()

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
        self._validate_row(row)
        self._refresh_preview()

    def _on_target_changed(self, row: int) -> None:
        self._validate_row(row)
        self._refresh_preview()

    def _on_target_changed_for_combo(self, combo: QComboBox) -> None:
        for row in range(self.mapping_table.rowCount()):
            if self.mapping_table.cellWidget(row, 1) is combo:
                self._on_target_changed(row)
                return

    def _show_mapping_table_context_menu(self, pos) -> None:
        menu = QMenu(self.mapping_table)
        actions = [
            ("Remove Selected", self._remove_row),
            ("Duplicate Selected", self._duplicate_selected_rows),
            ("Move Up", lambda: self._move_selected_rows(-1)),
            ("Move Down", lambda: self._move_selected_rows(1)),
            ("Enable Selected", lambda: self._set_selected_enabled(True)),
            ("Disable Selected", lambda: self._set_selected_enabled(False)),
        ]
        for text, callback in actions:
            action = QAction(text, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.exec(self.mapping_table.viewport().mapToGlobal(pos))

    def _selected_row_indexes(self) -> list[int]:
        selected = self.mapping_table.selectionModel().selectedRows()
        return sorted({index.row() for index in selected})

    def _table_row_snapshots(self) -> list[MappingRow]:
        snapshots: list[MappingRow] = []
        for row in range(self.mapping_table.rowCount()):
            enabled_item = self.mapping_table.item(row, 0)
            enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
            target_widget = self.mapping_table.cellWidget(row, 1)
            target = self._combo_value(target_widget) if isinstance(target_widget, QComboBox) else ""
            expr_item = self.mapping_table.item(row, 2)
            expression = expr_item.text() if expr_item else ""
            snapshots.append(MappingRow(target=target, expression=expression, enabled=enabled))
        return snapshots

    def _apply_table_row_snapshots(self, rows: list[MappingRow], *, selected_rows: list[int] | None = None) -> None:
        self.mapping_table.setRowCount(0)
        for idx, row in enumerate(rows):
            self.mapping_table.insertRow(idx)
            enabled_item = QTableWidgetItem("Yes" if row.enabled else "No")
            enabled_item.setCheckState(Qt.CheckState.Checked if row.enabled else Qt.CheckState.Unchecked)
            self.mapping_table.setItem(idx, 0, enabled_item)
            target_box = self._create_picker_combo(TARGET_OPTIONS, TARGET_OPTION_GROUPS)
            target_box.setCurrentText(row.target)
            target_box.currentTextChanged.connect(lambda _value, combo=target_box: self._on_target_changed_for_combo(combo))
            self.mapping_table.setCellWidget(idx, 1, target_box)
            self.mapping_table.setItem(idx, 2, QTableWidgetItem(row.expression))
            self._set_status_item(idx, "")
            self._validate_row(idx)

        self.mapping_table.clearSelection()
        for row in selected_rows or []:
            if 0 <= row < self.mapping_table.rowCount():
                self.mapping_table.selectRow(row)
        self._refresh_preview()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() in (0, 2):
            self._validate_row(item.row())
            self._refresh_preview()

    def _set_status_item(self, row: int, text: str) -> None:
        current = self.mapping_table.item(row, 3)
        if current is None:
            current = QTableWidgetItem(text)
            current.setFlags(current.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(row, 3, current)
        else:
            current.setText(text)

    def _validate_row(self, row: int) -> bool:
        enabled_item = self.mapping_table.item(row, 0)
        enabled = enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True
        target_widget = self.mapping_table.cellWidget(row, 1)
        target = self._combo_value(target_widget) if isinstance(target_widget, QComboBox) else ""
        expr_item = self.mapping_table.item(row, 2)
        expression = expr_item.text().strip() if expr_item else ""

        if not target and not expression:
            self._set_status_item(row, "")
            return True
        result = validate_mapping_expression(expression)
        if result.is_valid:
            self._set_status_item(row, "✅ Valid")
            return True
        if not enabled:
            self._set_status_item(row, f"⚠️ Disabled row: {result.error}")
            return True
        self._set_status_item(row, f"❌ Error: {result.error}")
        return False

    def _validate_all_rows_for_save(self) -> bool:
        valid = True
        for row in range(self.mapping_table.rowCount()):
            if not self._validate_row(row):
                valid = False
        return valid

    def _notify_change(self) -> None:
        if self._on_state_changed:
            self._on_state_changed()

    def _refresh_preview(self) -> None:
        artifact_lines = {"Analytes.xml": [], "AddOn.xml": [], "ProtocolFile.json": []}
        warnings: list[str] = []
        for row in self._collect_rows():
            if not bool(row.get("enabled", True)):
                continue
            target = str(row.get("target", "")).strip()
            expression = str(row.get("expression", "")).strip()
            if not target or not expression:
                continue
            artifact, _, target_path = target.partition(":")
            if artifact not in artifact_lines:
                continue
            values, row_warnings = self._resolve_expression_values(expression)
            warnings.extend(row_warnings)
            for value in values:
                artifact_lines[artifact].append(f"{target_path} = {value}")

        for artifact, widget in self._preview_text_by_artifact.items():
            widget.setPlainText("\n".join(artifact_lines[artifact] or ["(no enabled mappings for this artifact)"]))

        if warnings:
            self.preview_status_label.setText(f"⚠️ {len(warnings)} warning(s) while resolving source values")
            self.preview_status_label.setToolTip("\n".join(warnings))
        else:
            self.preview_status_label.setText("✅ Preview current")
            self.preview_status_label.setToolTip("")

    def _resolve_expression_values(self, expression: str) -> tuple[list[str], list[str]]:
        if expression.startswith("concat(") and expression.endswith(")"):
            return self._resolve_concat_values(expression)
        return self._resolve_token_values(expression)

    def _resolve_concat_values(self, expression: str) -> tuple[list[str], list[str]]:
        content = expression[len("concat(") : -1].strip()
        parts = self._split_arguments(content)
        delimiter = ""
        token_parts = parts
        if parts and parts[0].startswith("delimiter"):
            _, _, raw = parts[0].partition("=")
            cleaned = raw.strip()
            if len(cleaned) >= 2 and cleaned[0] in ("'", '"') and cleaned[-1] == cleaned[0]:
                delimiter = cleaned[1:-1]
            token_parts = parts[1:]

        resolved_values: list[list[str]] = []
        warnings: list[str] = []
        for token in token_parts:
            values, token_warnings = self._resolve_token_values(token)
            if values:
                resolved_values.append(values)
            warnings.extend(token_warnings)

        row_count = max((len(values) for values in resolved_values), default=1)
        lines: list[str] = []
        for idx in range(row_count):
            pieces = [values[idx] if idx < len(values) else values[-1] for values in resolved_values]
            lines.append(delimiter.join(pieces))
        return lines, warnings

    def _resolve_token_values(self, token: str) -> tuple[list[str], list[str]]:
        value = token.strip()
        if value.startswith("default:"):
            return [value[len("default:") :]], []
        if value.startswith("custom:"):
            return [value[len("custom:") :]], []
        if value.startswith("input:"):
            return self._resolve_input_values(value)
        return [f"<invalid:{value}>"] if value else ["<invalid>"], []

    def _resolve_input_values(self, token: str) -> tuple[list[str], list[str]]:
        path = token[len("input:") :].strip()
        segments = [segment for segment in path.split(".") if segment]
        cursor: list[object] = [self._app_state.editor_state.effective_values]
        for segment in segments:
            is_list = segment.endswith("[]")
            key = segment[:-2] if is_list else segment
            next_cursor: list[object] = []
            for current in cursor:
                if not isinstance(current, dict):
                    continue
                raw = current.get(key)
                if raw is None:
                    continue
                if is_list and isinstance(raw, list):
                    next_cursor.extend(raw)
                else:
                    next_cursor.append(raw)
            cursor = next_cursor
            if not cursor:
                warning = f"No source value for input:{path}"
                return [f"<missing:{path}>"], [warning]

        normalized = [str(item).strip() for item in cursor if str(item).strip()]
        if not normalized:
            warning = f"No source value for input:{path}"
            return [f"<missing:{path}>"], [warning]
        return normalized, []

    def _split_arguments(self, value: str) -> list[str]:
        parts: list[str] = []
        current: list[str] = []
        quote: str | None = None
        depth = 0
        for char in value:
            if quote:
                current.append(char)
                if char == quote:
                    quote = None
                continue
            if char in ("'", '"'):
                quote = char
                current.append(char)
                continue
            if char == "(":
                depth += 1
                current.append(char)
                continue
            if char == ")":
                depth = max(0, depth - 1)
                current.append(char)
                continue
            if char == "," and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue
            current.append(char)
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts

    def _create_picker_combo(self, options: list[PickerOption], groups: dict[str, tuple[str, ...]]) -> QComboBox:
        combo = QComboBox(self.mapping_table)
        combo.setEditable(True)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        index_by_value = {option.value: option for option in options}
        model = combo.model()
        for group_name, values in groups.items():
            header_item = QStandardItem(group_name)
            header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            model.appendRow(header_item)
            for value in values:
                option = index_by_value[value]
                combo.addItem(f"{option.label} ({option.value})", option.value)
                option_index = combo.count() - 1
                combo.setItemData(option_index, option.help_text, Qt.ItemDataRole.ToolTipRole)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        combo.highlighted.connect(lambda idx: combo.setToolTip(combo.itemData(idx, Qt.ItemDataRole.ToolTipRole) or ""))
        combo.currentIndexChanged.connect(lambda idx: combo.setToolTip(combo.itemData(idx, Qt.ItemDataRole.ToolTipRole) or ""))
        return combo

    def _combo_value(self, combo: QComboBox) -> str:
        selected = combo.currentData(Qt.ItemDataRole.UserRole)
        if isinstance(selected, str) and selected:
            return selected.strip()
        return combo.currentText().strip()

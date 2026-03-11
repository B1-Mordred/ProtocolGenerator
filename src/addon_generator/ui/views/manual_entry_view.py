from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.normalizers import normalize_for_matching


class ManualEntryView(QWidget):
    _BASICS_FIELD_WIDTH_CHARS = 36
    _TABLE_COLUMN_WIDTH_HINTS: dict[str, dict[str, int]] = {
        "Kit Components": {
            "Product Number": 20,
            "Component Name": 28,
            "Parameter Set Number": 22,
            "Assay Abbreviation": 18,
            'Parameter Set Name (or "BASIC Kit")': 34,
            "Type": 14,
            "Container Type (if Liquid)": 24,
        },
        "Dilutions": {
            "Dilution Key": 22,
            "Buffer1 Ratio": 16,
            "Buffer2 Ratio": 16,
            "Buffer3 Ratio": 16,
        },
        "Analytes": {
            "Analyte Name": 28,
            "Assay": 24,
            "Unit of Measurement": 22,
        },
        "Sample Prep": {
            "Action": 16,
            "Source": 24,
            "Destination": 24,
            "Volume": 16,
            "Duration": 16,
            "Force": 16,
        },
    }

    def __init__(self, parent=None, *, on_data_changed: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        self._on_data_changed = on_data_changed
        self._suspend_data_changed = False
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Enter AddOn data manually. Changes are autosaved as you type."))
        self.linkage_guidance_label = QLabel(
            "Assay linkage guidance: ProtocolFile AssayInformation[].Type must link to Analytes.xml Assay.Name "
            "based on assay_mapping.cross_file_match.mode. ProtocolFile AssayInformation[].DisplayName is a UI label "
            "and does not drive linkage."
        )
        self.linkage_guidance_label.setWordWrap(True)
        root.addWidget(self.linkage_guidance_label)
        self.linkage_warning_label = QLabel("")
        self.linkage_warning_label.setWordWrap(True)
        self.linkage_warning_label.hide()
        root.addWidget(self.linkage_warning_label)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        self.basics_fields: dict[str, QLineEdit] = {}
        self._dropdown_options: dict[str, list[str]] = {
            "kit_type": ["Solid", "Liquid"],
            "kit_container_type": ["Tube", "Bottle", "Vial"],
            "analyte_unit": ["mg/dL", "mmol/L", "ng/mL"],
            "sample_prep_action": ["Mix", "Incubate", "Heat"],
        }
        self._build_basics_tab()
        self.assays_table = self._build_table_tab(
            [
                "Product Number",
                "Component Name",
                "Parameter Set Number",
                "Assay Abbreviation",
                'Parameter Set Name (or "BASIC Kit")',
                "Type",
                "Container Type (if Liquid)",
            ],
            tab_name="Kit Components",
            guidance=(
                "Maps to ProtocolFile AssayInformation fields. 'Type' populates AssayInformation[].Type and should match "
                "Analytes.xml Assay.Name under current matching mode. 'Component Name' maps to DisplayName."
            ),
        )
        self.dilutions_table = self._build_table_tab(
            ["Dilution Key", "Buffer1 Ratio", "Buffer2 Ratio", "Buffer3 Ratio"],
            tab_name="Dilutions",
        )
        self.analytes_table = self._build_table_tab(
            ["Analyte Name", "Assay", "Unit of Measurement"],
            tab_name="Analytes",
            guidance=(
                "Analyte 'Assay' should reference the same assay identity used for Analytes.xml Assay.Name. "
                "Assay.Name is cross-file matched against ProtocolFile AssayInformation[].Type."
            ),
        )
        self.sample_prep_table = self._build_table_tab(
            ["Action", "Source", "Destination", "Volume", "Duration", "Force"],
            tab_name="Sample Prep",
        )
        self._update_linkage_warning()

    def _build_basics_tab(self) -> None:
        widget = QWidget(self)
        layout = QFormLayout(widget)
        fields = [
            ("kit_series", "Kit Series"),
            ("kit_name", "Kit Name"),
            ("kit_product_number", "Kit Product Number"),
            ("addon_series", "AddOn Series"),
            ("addon_product_name", "AddOn Product Name"),
            ("addon_product_number", "AddOn Product Number"),
        ]
        for key, label in fields:
            line = QLineEdit(widget)
            self._set_line_edit_width(line, self._BASICS_FIELD_WIDTH_CHARS)
            line.textChanged.connect(self._emit_data_changed)
            self.basics_fields[key] = line
            layout.addRow(label, line)
        self.tabs.addTab(widget, "Basics")

    def _build_table_tab(self, headers: list[str], *, tab_name: str, guidance: str | None = None) -> QTableWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        if guidance:
            guidance_label = QLabel(guidance, container)
            guidance_label.setWordWrap(True)
            layout.addWidget(guidance_label)
        table = QTableWidget(1, len(headers), container)
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        self._apply_table_widths(table, headers, tab_name)
        table.itemChanged.connect(lambda _item: self._emit_data_changed())
        layout.addWidget(table)

        add_button = QPushButton("Add Row", container)
        add_button.clicked.connect(lambda: self._append_row(table))
        row = QHBoxLayout()
        row.addWidget(add_button)
        row.addStretch(1)
        layout.addLayout(row)

        self.tabs.addTab(container, tab_name)
        return table

    def set_dropdown_options(
        self,
        *,
        kit_types: list[str],
        container_types: list[str],
        analyte_units: list[str],
        sample_prep_actions: list[str],
    ) -> None:
        self._dropdown_options["kit_type"] = [v for v in kit_types if v]
        self._dropdown_options["kit_container_type"] = [v for v in container_types if v]
        self._dropdown_options["analyte_unit"] = [v for v in analyte_units if v]
        self._dropdown_options["sample_prep_action"] = [v for v in sample_prep_actions if v]
        self._apply_table_dropdowns()

    def refresh_dynamic_dropdowns(self) -> None:
        self._apply_table_dropdowns()

    def _apply_table_dropdowns(self) -> None:
        for row in range(self.assays_table.rowCount()):
            self._ensure_dropdown_cell(self.assays_table, row, 5, self._dropdown_options["kit_type"])
            self._ensure_dropdown_cell(self.assays_table, row, 6, self._dropdown_options["kit_container_type"])
        for row in range(self.analytes_table.rowCount()):
            self._ensure_dropdown_cell(self.analytes_table, row, 2, self._dropdown_options["analyte_unit"])
            self._ensure_dropdown_cell(self.analytes_table, row, 1, self._assay_dropdown_values())
        kit_component_names = self._kit_component_dropdown_values()
        for row in range(self.sample_prep_table.rowCount()):
            self._ensure_dropdown_cell(self.sample_prep_table, row, 0, self._dropdown_options["sample_prep_action"])
            self._ensure_dropdown_cell(self.sample_prep_table, row, 1, kit_component_names)
            self._ensure_dropdown_cell(self.sample_prep_table, row, 2, kit_component_names)

    def _kit_component_dropdown_values(self) -> list[str]:
        values: list[str] = []
        for row in range(self.assays_table.rowCount()):
            value = self._cell_text(self.assays_table, row, 1)
            if value and value not in values:
                values.append(value)
        return values

    def _assay_dropdown_values(self) -> list[str]:
        values: list[str] = []
        for row in range(self.assays_table.rowCount()):
            value = self._cell_text(self.assays_table, row, 3)
            if value and value not in values:
                values.append(value)
        return values

    def _ensure_dropdown_cell(self, table: QTableWidget, row: int, col: int, options: list[str]) -> None:
        existing = self._cell_text(table, row, col)
        table.takeItem(row, col)
        combo = table.cellWidget(row, col)
        if not isinstance(combo, QComboBox):
            combo = QComboBox(table)
            combo.currentTextChanged.connect(lambda _text: self._emit_data_changed())
            table.setCellWidget(row, col, combo)
        combo.setMinimumContentsLength(max(12, max((len(option) for option in options), default=0)))
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        for option in options:
            combo.addItem(option)
        if existing:
            if combo.findText(existing) < 0:
                combo.addItem(existing)
            combo.setCurrentText(existing)
        combo.blockSignals(False)

    def _append_row(self, table: QTableWidget) -> None:
        table.insertRow(table.rowCount())
        self._apply_table_dropdowns()

    def _emit_data_changed(self) -> None:
        self._update_linkage_warning()
        if self._suspend_data_changed:
            return
        if self._on_data_changed:
            self._on_data_changed()

    def _update_linkage_warning(self) -> None:
        mode, alias_map = self._cross_file_match_settings()
        mismatches = self._linkage_mismatches(mode, alias_map)
        if not mismatches:
            self.linkage_warning_label.hide()
            self.linkage_warning_label.setText("")
            return
        sample_pairs = ", ".join(f"Type='{p}' vs XML Name='{x}'" for p, x in mismatches[:3])
        self.linkage_warning_label.setText(
            f"Warning: {len(mismatches)} assay linkage mismatch(es) for mode '{mode}'. {sample_pairs}. "
            "Set XML assay name equal to Type or change matching mode to alias_map/normalized."
        )
        self.linkage_warning_label.show()

    def _cross_file_match_settings(self) -> tuple[str, dict[str, str]]:
        try:
            config = load_mapping_config("config/mapping.v1.yaml")
            cross_file = config.raw.get("assay_mapping", {}).get("cross_file_match", {})
            mode = str(cross_file.get("mode", "exact"))
            alias_map = cross_file.get("alias_map", {})
            normalized_alias_map = alias_map if isinstance(alias_map, dict) else {}
            return mode, {str(k): str(v) for k, v in normalized_alias_map.items()}
        except Exception:
            return "exact", {}

    def _linkage_mismatches(self, mode: str, alias_map: dict[str, str]) -> list[tuple[str, str]]:
        mismatches: list[tuple[str, str]] = []
        for row in range(self.assays_table.rowCount()):
            protocol_type = self._cell_text(self.assays_table, row, 5)
            xml_name = self._cell_text(self.assays_table, row, 4) or self._cell_text(self.assays_table, row, 1)
            if not protocol_type and not xml_name:
                continue
            if mode == "normalized":
                matches = normalize_for_matching(protocol_type) == normalize_for_matching(xml_name)
            elif mode == "alias_map":
                protocol_value = alias_map.get(protocol_type, protocol_type)
                xml_value = alias_map.get(xml_name, xml_name)
                matches = protocol_value == xml_value
            else:
                matches = protocol_type == xml_name
            if not matches:
                mismatches.append((protocol_type, xml_name))
        return mismatches

    def _set_data_change_suspended(self, suspended: bool) -> None:
        self._suspend_data_changed = suspended

    @staticmethod
    def _cell_text(table: QTableWidget, row: int, col: int) -> str:
        combo = table.cellWidget(row, col)
        if isinstance(combo, QComboBox):
            return combo.currentText().strip()
        item = table.item(row, col)
        return item.text().strip() if item else ""

    @classmethod
    def _rows(cls, table: QTableWidget, keys: list[str]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in range(table.rowCount()):
            values = {}
            empty = True
            for col, key in enumerate(keys):
                text = cls._cell_text(table, row, col)
                if text:
                    empty = False
                values[key] = text
            if not empty:
                rows.append(values)
        return rows

    def payload(self) -> dict[str, object]:
        basics = {k: v.text().strip() for k, v in self.basics_fields.items()}
        return {
            "method": basics,
            "assays": self._rows(
                self.assays_table,
                [
                    "product_number",
                    "component_name",
                    "parameter_set_number",
                    "assay_abbreviation",
                    "parameter_set_name",
                    "type",
                    "container_type",
                ],
            ),
            "analytes": self._rows(
                self.analytes_table,
                ["name", "assay_key", "unit_names"],
            ),
            "sample_prep": self._rows(
                self.sample_prep_table,
                ["action", "source", "destination", "volume", "duration", "force"],
            ),
            "dilutions": self._rows(
                self.dilutions_table,
                ["key", "buffer1_ratio", "buffer2_ratio", "buffer3_ratio"],
            ),
        }


    def _reset_table_cells(self, table: QTableWidget) -> None:
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                table.setCellWidget(row, col, None)
                table.setItem(row, col, None)

    @staticmethod
    def _set_line_edit_width(edit: QLineEdit, characters: int) -> None:
        metrics = QFontMetrics(edit.font())
        width = metrics.horizontalAdvance("M" * characters) + 24
        edit.setMinimumWidth(width)

    def _apply_table_widths(self, table: QTableWidget, headers: list[str], tab_name: str) -> None:
        metrics = QFontMetrics(table.font())
        width_hints = self._TABLE_COLUMN_WIDTH_HINTS.get(tab_name, {})
        for index, header in enumerate(headers):
            expected_chars = width_hints.get(header, len(header) + 6)
            target_width = metrics.horizontalAdvance("M" * expected_chars) + 36
            table.setColumnWidth(index, target_width)



    def set_basics_values(self, values: dict[str, str]) -> None:
        self._set_data_change_suspended(True)
        try:
            for key, field in self.basics_fields.items():
                field.blockSignals(True)
                field.setText(values.get(key, ""))
                field.blockSignals(False)
        finally:
            self._set_data_change_suspended(False)

    def set_assays_rows(self, rows: list[dict[str, str]]) -> None:
        self._set_data_change_suspended(True)
        try:
            self.assays_table.blockSignals(True)
            self.assays_table.setRowCount(max(1, len(rows)))
            self._reset_table_cells(self.assays_table)
            keys = [
                "product_number",
                "component_name",
                "parameter_set_number",
                "assay_abbreviation",
                "parameter_set_name",
                "type",
                "container_type",
            ]
            for row_idx, row in enumerate(rows):
                for col_idx, key in enumerate(keys):
                    value = str(row.get(key, ""))
                    self.assays_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
            self.assays_table.blockSignals(False)
            self._apply_table_dropdowns()
        finally:
            self._set_data_change_suspended(False)

    def set_analytes_rows(self, rows: list[dict[str, str]]) -> None:
        self._set_data_change_suspended(True)
        try:
            self.analytes_table.blockSignals(True)
            self.analytes_table.setRowCount(max(1, len(rows)))
            self._reset_table_cells(self.analytes_table)
            keys = ["name", "assay_key", "unit_names"]
            for row_idx, row in enumerate(rows):
                for col_idx, key in enumerate(keys):
                    value = str(row.get(key, ""))
                    self.analytes_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
            self.analytes_table.blockSignals(False)
            self._apply_table_dropdowns()
        finally:
            self._set_data_change_suspended(False)

    def set_sample_prep_rows(self, rows: list[dict[str, str]]) -> None:
        self._set_data_change_suspended(True)
        try:
            self.sample_prep_table.blockSignals(True)
            self.sample_prep_table.setRowCount(max(1, len(rows)))
            self._reset_table_cells(self.sample_prep_table)
            keys = ["action", "source", "destination", "volume", "duration", "force"]
            for row_idx, row in enumerate(rows):
                for col_idx, key in enumerate(keys):
                    value = str(row.get(key, ""))
                    self.sample_prep_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
            self.sample_prep_table.blockSignals(False)
            self._apply_table_dropdowns()
        finally:
            self._set_data_change_suspended(False)

    def set_dilutions_rows(self, rows: list[dict[str, str]]) -> None:
        self._set_data_change_suspended(True)
        try:
            self.dilutions_table.blockSignals(True)
            self.dilutions_table.setRowCount(max(1, len(rows)))
            self._reset_table_cells(self.dilutions_table)
            keys = ["key", "buffer1_ratio", "buffer2_ratio", "buffer3_ratio"]
            for row_idx, row in enumerate(rows):
                for col_idx, key in enumerate(keys):
                    value = str(row.get(key, ""))
                    self.dilutions_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
            self.dilutions_table.blockSignals(False)
            self._apply_table_dropdowns()
        finally:
            self._set_data_change_suspended(False)

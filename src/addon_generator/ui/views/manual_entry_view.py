from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QFormLayout,
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


class ManualEntryView(QWidget):
    def __init__(self, parent=None, *, on_data_changed: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        self._on_data_changed = on_data_changed
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Enter AddOn data manually. Changes are autosaved as you type."))

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        self.basics_fields: dict[str, QLineEdit] = {}
        self._build_basics_tab()
        self.assays_table = self._build_table_tab(
            [
                "Product Number",
                "Component Name",
                "Parameter Set Number",
                "Assay Abbreviation",
                'Parameter Set Name (or "BASIC Kit")',
                "Type",
                "Container Type (if liquid)",
            ],
            tab_name="Kit Components",
        )
        self.dilutions_table = self._build_table_tab(
            ["Dilution Key", "Buffer1 Ratio", "Buffer2 Ratio", "Buffer3 Ratio"],
            tab_name="Dilutions",
        )
        self.analytes_table = self._build_table_tab(
            ["Analyte Key", "Analyte Name", "Assay Key", "Assay Information Type", "Unit Names"],
            tab_name="Analytes",
        )
        self.sample_prep_table = self._build_table_tab(
            ["Step Key", "Action", "Source", "Destination", "Volume", "Duration", "Force"],
            tab_name="Sample Prep",
        )

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
            line.textChanged.connect(self._emit_data_changed)
            self.basics_fields[key] = line
            layout.addRow(label, line)
        self.tabs.addTab(widget, "Basics")

    def _build_table_tab(self, headers: list[str], *, tab_name: str) -> QTableWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        table = QTableWidget(1, len(headers), container)
        table.setHorizontalHeaderLabels(headers)
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

    def _append_row(self, table: QTableWidget) -> None:
        table.insertRow(table.rowCount())

    def _emit_data_changed(self) -> None:
        if self._on_data_changed:
            self._on_data_changed()

    @staticmethod
    def _rows(table: QTableWidget, keys: list[str]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in range(table.rowCount()):
            values = {}
            empty = True
            for col, key in enumerate(keys):
                item = table.item(row, col)
                text = item.text().strip() if item else ""
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
                ["key", "name", "assay_key", "assay_information_type", "unit_names"],
            ),
            "sample_prep": self._rows(
                self.sample_prep_table,
                ["key", "action", "source", "destination", "volume", "duration", "force"],
            ),
            "dilutions": self._rows(
                self.dilutions_table,
                ["key", "buffer1_ratio", "buffer2_ratio", "buffer3_ratio"],
            ),
        }


    def set_basics_values(self, values: dict[str, str]) -> None:
        for key, field in self.basics_fields.items():
            field.blockSignals(True)
            field.setText(values.get(key, ""))
            field.blockSignals(False)

    def set_assays_rows(self, rows: list[dict[str, str]]) -> None:
        self.assays_table.blockSignals(True)
        self.assays_table.setRowCount(max(1, len(rows)))
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
                value = row.get(key, "")
                if value:
                    self.assays_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
        self.assays_table.blockSignals(False)

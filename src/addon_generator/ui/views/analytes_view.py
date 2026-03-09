from __future__ import annotations

from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from addon_generator.ui.widgets.detail_form import DetailForm
from addon_generator.ui.widgets.entity_table import EntityTable


class AnalytesView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        splitter = QSplitter(self)
        self.table = EntityTable(self)
        self.table.set_table_data(["Analyte Name", "Unit", "Linked Assay", "Status"], [])
        splitter.addWidget(self.table)
        splitter.addWidget(DetailForm(["Analyte Name", "Unit", "Linked Assay", "Parameter Set"]))
        layout.addWidget(splitter)

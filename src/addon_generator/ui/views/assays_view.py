from __future__ import annotations

from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from addon_generator.ui.widgets.detail_form import DetailForm
from addon_generator.ui.widgets.entity_table import EntityTable


class AssaysView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        splitter = QSplitter(self)
        self.table = EntityTable(self)
        self.table.set_table_data(["Internal Key", "Protocol Type", "Source"], [])
        splitter.addWidget(self.table)
        splitter.addWidget(DetailForm(["Internal Key", "Protocol Type", "Protocol Display Name", "XML Assay Name"]))
        layout.addWidget(splitter)

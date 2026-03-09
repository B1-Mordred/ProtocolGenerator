from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from addon_generator.ui.widgets.entity_table import EntityTable


class DilutionsView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        table = EntityTable(self)
        table.set_table_data(["Dilution Name", "Buffer 1 Ratio", "Buffer 2 Ratio", "Buffer 3 Ratio", "Status"], [])
        layout.addWidget(table)

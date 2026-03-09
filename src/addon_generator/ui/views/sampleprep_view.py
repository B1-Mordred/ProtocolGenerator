from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from addon_generator.ui.widgets.entity_table import EntityTable


class SamplePrepView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        table = EntityTable(self)
        table.set_table_data(["Order", "Action", "Source", "Destination", "Volume", "Duration", "Force"], [])
        layout.addWidget(table)

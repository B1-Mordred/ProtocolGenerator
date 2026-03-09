from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from addon_generator.ui.widgets.entity_table import EntityTable
from addon_generator.ui.widgets.field_help_panel import FieldHelpPanel


class ImportReviewView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        table = EntityTable(self)
        table.set_table_data(["Entity/Field", "Imported", "Effective", "Source", "Override", "Resolution"], [])
        layout.addWidget(table)
        layout.addWidget(FieldHelpPanel("Provenance", "Select a conflict to inspect source and resolution details."))

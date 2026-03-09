from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit, QWidget


class DetailForm(QWidget):
    def __init__(self, fields: list[str], parent=None) -> None:
        super().__init__(parent)
        self.inputs: dict[str, QLineEdit] = {}
        layout = QFormLayout(self)
        for field in fields:
            edit = QLineEdit(self)
            layout.addRow(field, edit)
            self.inputs[field] = edit

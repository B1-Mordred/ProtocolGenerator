from __future__ import annotations

from PySide6.QtWidgets import QLabel


class FieldHelpPanel(QLabel):
    def __init__(self, title: str, details: str, parent=None) -> None:
        super().__init__(parent)
        self.set_help(title, details)

    def set_help(self, title: str, details: str) -> None:
        self.setText(f"{title}\n\n{details}")

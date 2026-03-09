from __future__ import annotations

from PySide6.QtWidgets import QLabel


class FieldHelpPanel(QLabel):
    def set_help(self, title: str, details: str) -> None:
        self.setText(f"{title}\n\n{details}")

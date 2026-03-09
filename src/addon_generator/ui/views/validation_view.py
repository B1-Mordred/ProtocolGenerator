from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from addon_generator.ui.widgets.issue_list import IssueList


class ValidationView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.issues = IssueList(self)
        layout.addWidget(self.issues)

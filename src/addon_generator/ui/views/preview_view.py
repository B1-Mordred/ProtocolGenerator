from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from addon_generator.ui.widgets.preview_tabs import PreviewTabs


class PreviewView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.regenerate_button = QPushButton("Regenerate", self)
        self.tabs = PreviewTabs(self)
        layout.addWidget(self.regenerate_button)
        layout.addWidget(self.tabs)

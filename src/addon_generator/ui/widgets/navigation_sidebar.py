from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class NavigationSidebar(QListWidget):
    section_changed = Signal(int)

    def __init__(self, sections: list[str], parent=None) -> None:
        super().__init__(parent)
        for index, section in enumerate(sections):
            item = QListWidgetItem(section)
            item.setData(32, index)
            self.addItem(item)
        self.currentRowChanged.connect(self.section_changed.emit)

    def set_issue_count(self, index: int, count: int) -> None:
        item = self.item(index)
        if item is not None:
            base = item.text().split(" (")[0]
            item.setText(f"{base} ({count})" if count else base)

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class DataEntryHomeView(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        on_manual_selected: Callable[[], None] | None = None,
        on_excel_selected: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("AddOn Data Entry"))

        manual = QPushButton("Enter Data Manually", self)
        excel = QPushButton("Import Excel File", self)
        manual.clicked.connect(lambda: on_manual_selected and on_manual_selected())
        excel.clicked.connect(lambda: on_excel_selected and on_excel_selected())
        layout.addWidget(manual)
        layout.addWidget(excel)
        layout.addStretch(1)

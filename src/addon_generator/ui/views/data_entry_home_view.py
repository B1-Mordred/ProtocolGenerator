from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget


class DataEntryHomeView(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        on_manual_selected: Callable[[], None] | None = None,
        on_excel_selected: Callable[[], None] | None = None,
        on_rule_pack_changed: Callable[[str], None] | None = None,
        available_rule_packs: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("AddOn Data Entry"))

        self.rule_pack_combo = QComboBox(self)
        self.rule_pack_combo.addItems(available_rule_packs or ["default"])
        self.rule_pack_combo.currentTextChanged.connect(lambda value: on_rule_pack_changed and on_rule_pack_changed(value))
        layout.addWidget(QLabel("Rule Pack"))
        layout.addWidget(self.rule_pack_combo)

        manual = QPushButton("Enter Data Manually", self)
        excel = QPushButton("Import Excel File", self)
        manual.clicked.connect(lambda: on_manual_selected and on_manual_selected())
        excel.clicked.connect(lambda: on_excel_selected and on_excel_selected())
        layout.addWidget(manual)
        layout.addWidget(excel)
        layout.addStretch(1)

    def set_selected_rule_pack(self, name: str) -> None:
        index = self.rule_pack_combo.findText(name)
        if index >= 0:
            self.rule_pack_combo.setCurrentIndex(index)

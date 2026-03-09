from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from addon_generator.ui.widgets.detail_form import DetailForm


class MethodView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(
            DetailForm(
                [
                    "Method ID",
                    "Method Version",
                    "Display Name",
                    "Kit Series",
                    "Kit Product Number",
                    "AddOn Series",
                    "AddOn Product Name",
                    "AddOn Product Number",
                ]
            )
        )

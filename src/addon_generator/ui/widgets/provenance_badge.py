from __future__ import annotations

from PySide6.QtWidgets import QLabel


class ProvenanceBadge(QLabel):
    def __init__(self, text: str = "Default", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("provenanceBadge")

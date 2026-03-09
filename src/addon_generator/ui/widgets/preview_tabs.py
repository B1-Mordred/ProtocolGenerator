from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QTabWidget, QWidget, QVBoxLayout


class PreviewTabs(QTabWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.protocol = QPlainTextEdit(self)
        self.protocol.setReadOnly(True)
        self.analytes = QPlainTextEdit(self)
        self.analytes.setReadOnly(True)
        self.summary = QPlainTextEdit(self)
        self.summary.setReadOnly(True)
        self.addTab(self.protocol, "ProtocolFile.json")
        self.addTab(self.analytes, "Analytes.xml")
        self.addTab(self.summary, "Summary")

    def set_preview(self, protocol: str, analytes: str, summary: str) -> None:
        self.protocol.setPlainText(protocol)
        self.analytes.setPlainText(analytes)
        self.summary.setPlainText(summary)

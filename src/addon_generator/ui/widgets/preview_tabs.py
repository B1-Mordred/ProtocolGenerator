from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget


class PreviewTabs(QTabWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.protocol = self._build_editor()
        self.analytes = self._build_editor()
        self.summary = self._build_editor()
        self.addTab(self._wrap_with_copy(self.protocol), "ProtocolFile.json")
        self.addTab(self._wrap_with_copy(self.analytes), "Analytes.xml")
        self.addTab(self._wrap_with_copy(self.summary), "Summary")

    def _build_editor(self) -> QPlainTextEdit:
        editor = QPlainTextEdit(self)
        editor.setReadOnly(True)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        return editor

    def _wrap_with_copy(self, editor: QPlainTextEdit) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        controls = QHBoxLayout()
        controls.addStretch(1)
        copy_btn = QPushButton("Copy", container)
        copy_btn.clicked.connect(lambda: self._copy_editor_text(editor))
        controls.addWidget(copy_btn)
        layout.addLayout(controls)
        layout.addWidget(editor)
        return container

    def _copy_editor_text(self, editor: QPlainTextEdit) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(editor.toPlainText())

    def set_preview(self, protocol: str, analytes: str, summary: str) -> None:
        self.protocol.setPlainText(protocol)
        self.analytes.setPlainText(analytes)
        self.summary.setPlainText(summary)

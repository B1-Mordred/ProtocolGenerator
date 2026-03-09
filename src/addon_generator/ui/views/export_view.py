from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QPushButton, QWidget


class ExportView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.destination = QLineEdit(self)
        self.package_name = QLineEdit(self)
        self.overwrite = QCheckBox("Overwrite", self)
        self.export_button = QPushButton("Export", self)
        layout.addRow("Destination Folder", self.destination)
        layout.addRow("Package Name", self.package_name)
        layout.addRow("", self.overwrite)
        layout.addRow("", self.export_button)

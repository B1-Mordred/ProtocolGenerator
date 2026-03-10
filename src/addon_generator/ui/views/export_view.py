from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget

from addon_generator.ui.services.export_service import ExportResult


class ExportView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.destination = QLineEdit(self)
        self.choose_destination_button = QPushButton("Choose…", self)
        self.package_name = QLineEdit(self)
        self.overwrite = QCheckBox("Overwrite", self)
        self.validate_button = QPushButton("Validate Before Export", self)
        self.export_button = QPushButton("Export", self)

        destination_container = QWidget(self)
        destination_layout = QVBoxLayout(destination_container)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.addWidget(self.destination)
        destination_layout.addWidget(self.choose_destination_button)

        self.result_status = QLabel("No export attempted.", self)
        self.result_destination = QLabel("", self)
        self.result_written_paths = QListWidget(self)
        self.result_cleanup_note = QLabel("", self)

        layout.addRow("Destination Folder", destination_container)
        layout.addRow("Package Name", self.package_name)
        layout.addRow("", self.overwrite)
        layout.addRow("", self.validate_button)
        layout.addRow("", self.export_button)
        layout.addRow("Result", self.result_status)
        layout.addRow("Destination", self.result_destination)
        layout.addRow("Written Files", self.result_written_paths)
        layout.addRow("Notes", self.result_cleanup_note)

    def set_export_result(self, result: ExportResult) -> None:
        if result.success:
            self.result_status.setText("Export succeeded")
        else:
            reason = result.failure_reason or "Unknown failure"
            self.result_status.setText(f"Export failed: {reason}")

        self.result_destination.setText(result.destination)
        self.result_cleanup_note.setText(result.cleanup_note or "")
        self.result_written_paths.clear()
        self.result_written_paths.addItems(result.written_paths)

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from addon_generator.ui.widgets.preview_tabs import PreviewTabs


class PreviewView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.stale_banner = QLabel("Preview status: stale", self)
        self.validation_readiness = QLabel("Validation: unknown", self)
        self.export_readiness = QLabel("Export readiness: unknown", self)
        self.error_message = QLabel("", self)
        self.regenerate_button = QPushButton("Regenerate", self)
        self.tabs = PreviewTabs(self)
        layout.addWidget(self.stale_banner)
        layout.addWidget(self.validation_readiness)
        layout.addWidget(self.export_readiness)
        layout.addWidget(self.error_message)
        layout.addWidget(self.regenerate_button)
        layout.addWidget(self.tabs)

    def set_preview_meta(
        self,
        *,
        stale: bool,
        validation_state: str,
        export_ready: bool,
        generation_error: str | None,
    ) -> None:
        self.stale_banner.setText("Preview status: stale" if stale else "Preview status: current")
        self.validation_readiness.setText(f"Validation: {validation_state}")
        self.export_readiness.setText(f"Export readiness: {'ready' if export_ready else 'blocked'}")
        self.error_message.setText(generation_error or "")

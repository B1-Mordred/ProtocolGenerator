from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusBanner(QLabel):
    def set_status(self, *, preview_stale: bool, has_errors: bool) -> None:
        if has_errors:
            self.setText("Validation errors present")
        elif preview_stale:
            self.setText("Preview is stale")
        else:
            self.setText("Ready")

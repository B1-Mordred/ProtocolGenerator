from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusBanner(QLabel):
    def set_status(
        self,
        *,
        validation_stale: bool,
        preview_stale: bool,
        export_ready: bool,
        draft_dirty: bool,
    ) -> None:
        validation_status = "stale" if validation_stale else "current"
        preview_status = "stale" if preview_stale else "current"
        export_status = "ready" if export_ready else "blocked"
        draft_status = "dirty" if draft_dirty else "saved"
        self.setText(
            " | ".join(
                [
                    f"Validation: {validation_status}",
                    f"Preview: {preview_status}",
                    f"Export: {export_status}",
                    f"Draft: {draft_status}",
                ]
            )
        )

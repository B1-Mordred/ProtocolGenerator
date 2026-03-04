from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DraftPersistence:
    def __init__(self, temp_draft_path: Path | None = None):
        self.temp_draft_path = temp_draft_path

    @staticmethod
    def now_stamp() -> str:
        return datetime.now().strftime("%H:%M")

    @staticmethod
    def write_json_atomic(target: Path, payload: Dict[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target.parent, suffix=".tmp") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            temp_name = handle.name
        Path(temp_name).replace(target)

    def save_temp_draft(self, payload: Dict[str, Any]) -> Path | None:
        if self.temp_draft_path is None:
            return None
        self.write_json_atomic(self.temp_draft_path, payload)
        return self.temp_draft_path

    def load_temp_draft(self) -> Dict[str, Any] | None:
        if self.temp_draft_path is None or not self.temp_draft_path.exists():
            return None
        return json.loads(self.temp_draft_path.read_text(encoding="utf-8"))

    def log_save_failure(self, destination: str, exc: Exception) -> None:
        logger.error(
            "save_operation_failed",
            extra={
                "event": "save_operation_failed",
                "destination": destination,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            exc_info=True,
        )


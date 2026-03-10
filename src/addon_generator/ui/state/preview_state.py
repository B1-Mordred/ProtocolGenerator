from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass


@dataclass(slots=True)
class PreviewState:
    stale: bool = True
    protocol_json: str = ""
    analytes_xml: str = ""
    summary: dict[str, str | int | bool] | None = None
    validation_state_snapshot: str = "unknown"
    export_readiness_snapshot: bool = False
    last_generated_at: datetime | None = None
    generation_error: str | None = None

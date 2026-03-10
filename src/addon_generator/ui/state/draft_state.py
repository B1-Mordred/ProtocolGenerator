from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DraftState:
    path: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    dirty: bool = False
    last_saved_at: datetime | None = None
    restore_metadata: dict[str, Any] = field(default_factory=dict)

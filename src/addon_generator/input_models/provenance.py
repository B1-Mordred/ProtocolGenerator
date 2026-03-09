from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceType = Literal["excel", "xml", "gui", "default"]


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    source_type: SourceType
    source_file: str | None = None
    source_sheet: str | None = None
    row: int | None = None
    column: str | None = None
    field_key: str | None = None
    is_override: bool = False

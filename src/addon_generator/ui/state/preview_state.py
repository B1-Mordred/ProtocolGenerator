from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreviewState:
    stale: bool = True
    protocol_json: str = ""
    analytes_xml: str = ""
    summary: dict[str, str | int | bool] | None = None

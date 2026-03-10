from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(resource_name: str, *, anchor_file: str | Path | None = None) -> Path:
    """Resolve a resource path for both source and PyInstaller-bundled execution."""

    search_roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_roots.append(Path(meipass))

    if anchor_file is not None:
        anchor_path = Path(anchor_file).resolve()
        search_roots.extend(
            [
                Path.cwd(),
                anchor_path.parent,
                *anchor_path.parents,
            ]
        )
    else:
        search_roots.append(Path.cwd())

    seen: set[Path] = set()
    for root in search_roots:
        if root in seen:
            continue
        seen.add(root)
        candidate = root / resource_name
        if candidate.exists():
            return candidate

    return search_roots[0] / resource_name


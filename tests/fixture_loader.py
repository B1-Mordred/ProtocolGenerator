from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
INDEX_PATH = FIXTURE_ROOT / "index.json"


def load_fixture_index() -> dict[str, Any]:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def fixture_metadata(name: str) -> dict[str, Any]:
    index = load_fixture_index()["workbook_fixtures"]
    if name not in index:
        raise KeyError(f"Unknown fixture scenario: {name}")
    return index[name]


def materialize_workbook_fixture(name: str, tmp_path: Path) -> Path:
    meta = fixture_metadata(name)
    source_path = Path(meta["workbook"])

    if source_path.suffix.lower() == ".xlsx":
        destination = tmp_path / f"{name}.xlsx"
        shutil.copyfile(source_path, destination)
        return destination

    spec = json.loads(source_path.read_text(encoding="utf-8"))
    if spec.get("layout") not in {"v1-flat", "v2-sheeted"}:
        raise ValueError(f"Unsupported fixture layout for scenario '{name}'")

    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    first_sheet = True
    for sheet_name, sheet_spec in spec["sheets"].items():
        sheet = workbook.active if first_sheet else workbook.create_sheet(sheet_name)
        sheet.title = sheet_name
        first_sheet = False
        sheet.append(sheet_spec["columns"])
        for row in sheet_spec.get("rows", []):
            sheet.append(row)

    output_path = tmp_path / f"{name}.xlsx"
    workbook.save(output_path)
    return output_path

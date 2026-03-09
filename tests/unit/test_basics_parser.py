from __future__ import annotations

from dataclasses import dataclass

from addon_generator.importers.excel.basics_parser import parse_basics_sheet


@dataclass
class _Cell:
    value: object


class _Sheet:
    title = "Basics"

    def __init__(self, rows: list[list[object]]):
        self._rows = rows

    def iter_rows(self):
        for row in self._rows:
            yield tuple(_Cell(value=v) for v in row)


def test_parse_basics_sheet_preserves_identity_mapping_after_duplicate_checks() -> None:
    diagnostics = []
    sheet = _Sheet(
        [
            ["Method Id", "M-100"],
            ["Method Version", "1.0"],
            ["Method Display Name", "Panel A"],
            [],
            ["Assay Key", "Protocol Type", "Protocol Display Name", "Xml Assay Name"],
            ["assay:chem", "CHEM", "Chemistry", "Chemistry"],
            ["assay:chem", "CHEM", "Chemistry", "Chemistry"],
        ]
    )

    parsed = parse_basics_sheet(sheet, diagnostics=diagnostics)

    assert parsed.method.display_name == "Panel A"
    assert [assay.key for assay in parsed.assays] == ["assay:chem"]
    assert any(d.rule_id == "duplicate-row" for d in diagnostics)

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


def test_parse_basics_sheet_maps_kit_component_table_columns() -> None:
    diagnostics = []
    sheet = _Sheet(
        [
            ["Method Id", "M-100"],
            ["Method Version", "1.0"],
            [],
            [
                "Product Number",
                "Component Name",
                "Parameter Set Number",
                "Assay Abbreviation",
                'Parameter Set Name (or "BASIC Kit")',
                "Type",
                "Container Type (if liquid)",
            ],
            ["PN-1", "Component A", "PS-1", "ABB", "Basic Kit", "CHEM", "Tube"],
        ]
    )

    parsed = parse_basics_sheet(sheet, diagnostics=diagnostics)

    assert [assay.key for assay in parsed.assays] == ["PS-1"]
    assert parsed.assays[0].protocol_type == "CHEM"
    assert parsed.assays[0].metadata["product_number"] == "PN-1"
    assert parsed.assays[0].metadata["container_type"] == "Tube"
    assert not diagnostics


def test_parse_basics_sheet_reads_identity_pairs_across_columns() -> None:
    diagnostics = []
    sheet = _Sheet(
        [
            [
                "Method Id",
                "M-100",
                "Method Version",
                "1.0",
                "Method Display Name",
                "Legacy Name",
                "AddOn Series",
                "Series X",
            ],
            [
                "ignored",
                "value",
                "AddOn Product Name",
                "Product Y",
                "AddOn Product Number",
                "PN-900",
                "trailing",
                "data",
            ],
            [],
            ["Assay Key", "Protocol Type", "Protocol Display Name", "Xml Assay Name"],
            ["assay:chem", "CHEM", "Chemistry", "Chemistry"],
        ]
    )

    parsed = parse_basics_sheet(sheet, diagnostics=diagnostics)

    assert parsed.method.main_title == "Series X"
    assert parsed.method.sub_title == "Product Y"
    assert parsed.method.product_number == "PN-900"
    assert parsed.method.display_name == "Legacy Name"
    assert not diagnostics


def test_parse_basics_sheet_prefers_latest_identity_match_when_label_repeats() -> None:
    diagnostics = []
    sheet = _Sheet(
        [
            ["Method Id", "M-100", "Method Version", "1.0", "AddOn Series", "Old Series", "AddOn Series", "New Series"],
            ["AddOn Product Name", "Old Product", "AddOn Product Name", "New Product", "AddOn Product Number", "P-001", "AddOn Product Number", "P-002"],
            [],
            ["Assay Key", "Protocol Type", "Protocol Display Name", "Xml Assay Name"],
            ["assay:chem", "CHEM", "Chemistry", "Chemistry"],
        ]
    )

    parsed = parse_basics_sheet(sheet, diagnostics=diagnostics)

    assert parsed.method.main_title == "New Series"
    assert parsed.method.sub_title == "New Product"
    assert parsed.method.product_number == "P-002"
    assert not diagnostics


def test_parse_basics_sheet_fills_down_sparse_kit_component_cells() -> None:
    diagnostics = []
    sheet = _Sheet(
        [
            ["Method Id", "M-100"],
            ["Method Version", "1.0"],
            [],
            [
                "Product Number",
                "Component Name",
                "Parameter Set Number",
                "Assay Abbreviation",
                'Parameter Set Name (or "BASIC Kit")',
                "Type",
                "Container Type (if liquid)",
            ],
            ["92046/N2/XT2", "Internal Standard Mix", "92714-XT2", "NL2-XT2", "Neuroleptics 2/EXTENDED 2", "Internal Standard", "BG 50mL"],
            ["", "", "92913-XT", "AD1-XT", "Antidepressants 1/EXTENDED", "", ""],
        ]
    )

    parsed = parse_basics_sheet(sheet, diagnostics=diagnostics)

    assert [assay.key for assay in parsed.assays] == ["92714-XT2", "92913-XT"]
    assert parsed.assays[1].metadata["product_number"] == "92046/N2/XT2"
    assert parsed.assays[1].metadata["type"] == "Internal Standard"
    assert parsed.assays[1].metadata["container_type"] == "BG 50mL"
    assert not diagnostics

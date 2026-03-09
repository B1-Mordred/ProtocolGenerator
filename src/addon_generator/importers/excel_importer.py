from __future__ import annotations

from pathlib import Path
from typing import Any

from addon_generator.domain.models import ProtocolContextModel
from addon_generator.importers.gui_mapper import map_gui_payload_to_context


class ExcelImporter:
    """Workbook importer compatible with the legacy row-oriented baseline behavior."""

    def import_workbook(self, excel_path: str | Path) -> ProtocolContextModel:
        workbook_path = Path(excel_path)
        try:
            from openpyxl import load_workbook  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("openpyxl is required for ExcelImporter") from exc

        workbook = load_workbook(workbook_path, data_only=True)
        row_payloads: list[dict[str, Any]] = []

        for sheet in workbook.worksheets:
            header_row = next(sheet.iter_rows(min_row=1, max_row=1), None)
            if header_row is None:
                continue

            headers = [str(cell.value or "").strip() for cell in header_row]
            for row in sheet.iter_rows(min_row=2):
                values = [cell.value for cell in row]
                if not any(value is not None and str(value).strip() for value in values):
                    continue
                row_payloads.append({headers[i]: values[i] for i in range(min(len(headers), len(values))) if headers[i]})

        return map_gui_payload_to_context({"rows": row_payloads})

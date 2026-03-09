from __future__ import annotations

from pathlib import Path
from typing import Any

from addon_generator.domain.models import AddonModel
from addon_generator.importers.gui_mapper import map_gui_payload_to_addon


class ExcelImporter:
    def read_workbook_rows(self, excel_path: str | Path) -> list[dict[str, Any]]:
        from openpyxl import load_workbook  # type: ignore

        rows: list[dict[str, Any]] = []
        wb = load_workbook(Path(excel_path), data_only=True)
        for sheet in wb.worksheets:
            header_row = next(sheet.iter_rows(min_row=1, max_row=1), None)
            if not header_row:
                continue
            headers = [str(c.value or "").strip() for c in header_row]
            for row in sheet.iter_rows(min_row=2):
                values = [c.value for c in row]
                if not any(v is not None and str(v).strip() for v in values):
                    continue
                rows.append({headers[i]: values[i] for i in range(min(len(headers), len(values))) if headers[i]})
        return rows

    def normalize_workbook_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"method_id": "", "method_version": "", "assays": [], "analytes": [], "units": []}

        first = rows[0]
        payload: dict[str, Any] = {
            "method_id": str(first.get("MethodId") or ""),
            "method_version": str(first.get("MethodVersion") or ""),
            "MethodInformation": {"DisplayName": str(first.get("MethodDisplayName") or "")},
            "assays": [],
            "analytes": [],
            "units": [],
        }
        for row in rows:
            assay_key = str(row.get("AssayKey") or row.get("AssayDisplayName") or "").strip()
            analyte_key = str(row.get("AnalyteKey") or row.get("AnalyteName") or "").strip()
            unit_key = str(row.get("UnitKey") or row.get("UnitName") or "").strip()
            if assay_key:
                payload["assays"].append(
                    {
                        "key": assay_key,
                        "protocol_type": str(row.get("ProtocolType") or row.get("AssayDisplayName") or ""),
                        "protocol_display_name": row.get("AssayDisplayName"),
                        "xml_name": str(row.get("XmlAssayName") or row.get("ProtocolType") or row.get("AssayDisplayName") or ""),
                    }
                )
            if analyte_key:
                payload["analytes"].append(
                    {
                        "key": analyte_key,
                        "name": str(row.get("AnalyteName") or ""),
                        "assay_key": assay_key,
                        "assay_information_type": row.get("AssayInformationType"),
                    }
                )
            if unit_key:
                payload["units"].append(
                    {
                        "key": unit_key,
                        "name": str(row.get("UnitName") or ""),
                        "analyte_key": analyte_key,
                    }
                )
        return payload

    def map_workbook_rows_to_canonical_model(self, rows: list[dict[str, Any]]) -> AddonModel:
        return map_gui_payload_to_addon(self.normalize_workbook_rows(rows))

    def import_workbook(self, excel_path: str | Path) -> AddonModel:
        return self.map_workbook_rows_to_canonical_model(self.read_workbook_rows(excel_path))

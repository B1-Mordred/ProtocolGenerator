from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from addon_generator.domain.models import ProtocolContextModel
from addon_generator.importers.gui_mapper import extract_context_fragments, map_gui_payload_to_context


class XmlImporter:
    """Architecture-ready XML importer that maps AddOn XML into canonical domain context."""

    def import_xml(self, xml_path: str | Path) -> ProtocolContextModel:
        xml_file = Path(xml_path)
        root = ElementTree.parse(xml_file).getroot()

        payload = self._build_payload(root)
        context = map_gui_payload_to_context(payload)
        context.context_fragments.update(extract_context_fragments(payload, origin="xml"))
        return context

    def _build_payload(self, root: ElementTree.Element) -> dict[str, Any]:
        method_name = root.attrib.get("Name") or root.findtext("Name") or "Imported Addon"
        method_id = root.attrib.get("Id") or root.findtext("Id") or 0

        rows: list[dict[str, Any]] = []
        for assay_el in root.findall(".//Assay"):
            assay_name = assay_el.attrib.get("Name") or assay_el.findtext("Name") or "Assay"
            analyte_elements = assay_el.findall(".//Analyte")
            if not analyte_elements:
                rows.append({"MethodDisplayName": method_name, "AssayDisplayName": assay_name})
                continue

            for analyte_el in analyte_elements:
                analyte_name = analyte_el.attrib.get("Name") or analyte_el.findtext("Name") or "Analyte"
                units = analyte_el.findall(".//AnalyteUnit")
                if not units:
                    rows.append(
                        {
                            "MethodDisplayName": method_name,
                            "AssayDisplayName": assay_name,
                            "AnalyteName": analyte_name,
                            "UnitName": "Unit",
                        }
                    )
                    continue

                for unit_el in units:
                    unit_name = unit_el.attrib.get("Name") or unit_el.findtext("Name") or "Unit"
                    rows.append(
                        {
                            "MethodDisplayName": method_name,
                            "AssayDisplayName": assay_name,
                            "AnalyteName": analyte_name,
                            "UnitName": unit_name,
                        }
                    )

        payload: dict[str, Any] = {
            "addon_id": method_id,
            "addon_name": method_name,
            "MethodInformation": {"DisplayName": method_name, "Id": method_id},
            "rows": rows or [{"MethodDisplayName": method_name}],
        }

        for key in (
            "LoadingWorkflowSteps",
            "ProcessingWorkflowSteps",
            "DilutionWorkflowSteps",
            "ReagentWorkflowSteps",
            "CalibratorWorkflowSteps",
            "ControlWorkflowSteps",
        ):
            section = root.find(f".//{key}")
            if section is not None:
                payload[key] = [{"tag": child.tag, "text": (child.text or "").strip()} for child in section]

        return payload

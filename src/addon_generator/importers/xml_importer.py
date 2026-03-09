from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from addon_generator.domain.models import AddonModel
from addon_generator.importers.gui_mapper import map_gui_payload_to_addon


class XmlImporter:
    def import_xml(self, xml_path: str | Path) -> AddonModel:
        root = ET.parse(Path(xml_path)).getroot()
        payload: dict[str, object] = {
            "method_id": root.findtext("MethodId") or "",
            "method_version": root.findtext("MethodVersion") or "",
            "assays": [],
            "analytes": [],
            "units": [],
        }

        for assay_el in root.findall("./Assays/Assay"):
            assay_id = assay_el.findtext("Id") or ""
            assay_name = assay_el.findtext("Name") or ""
            assay_key = f"assay:{assay_id or assay_name}"
            payload["assays"].append(
                {
                    "key": assay_key,
                    "protocol_type": assay_name,
                    "protocol_display_name": assay_name,
                    "xml_name": assay_name,
                }
            )
            for analyte_el in assay_el.findall("./Analytes/Analyte"):
                analyte_id = analyte_el.findtext("Id") or ""
                analyte_name = analyte_el.findtext("Name") or ""
                analyte_key = f"analyte:{analyte_id or analyte_name}"
                payload["analytes"].append(
                    {
                        "key": analyte_key,
                        "name": analyte_name,
                        "assay_key": assay_key,
                        "assay_information_type": analyte_el.findtext("AssayInformationType") or "",
                    }
                )
                for unit_el in analyte_el.findall("./AnalyteUnits/AnalyteUnit"):
                    unit_id = unit_el.findtext("Id") or ""
                    unit_name = unit_el.findtext("Name") or ""
                    payload["units"].append(
                        {
                            "key": f"unit:{unit_id or unit_name}",
                            "name": unit_name,
                            "analyte_key": analyte_key,
                        }
                    )
        return map_gui_payload_to_addon(payload)

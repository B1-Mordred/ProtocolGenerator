from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from addon_generator.domain.issues import ValidationIssueCollection
from addon_generator.domain.models import AddonModel
from addon_generator.serialization.xml_writer import serialize_xml_document, write_xml_document
from addon_generator.validation.xsd_validator import validate_xml_against_xsd


@dataclass(slots=True)
class AddonXmlGenerationResult:
    xml_content: str
    issues: ValidationIssueCollection
    output_path: Path | None = None


def generate_analytes_addon_xml(addon: AddonModel, xsd_path: Path | str, output_path: Path | str | None = None) -> AddonXmlGenerationResult:
    if addon.method is None:
        raise ValueError("AddonModel.method is required")

    root = ET.Element("AddOn")
    ET.SubElement(root, "Id").text = str(addon.addon_id)
    ET.SubElement(root, "MethodId").text = addon.method.product_number or ""
    ET.SubElement(root, "MethodVersion").text = ""

    assays_el = ET.SubElement(root, "Assays")
    analytes_by_assay: dict[str, list] = {}
    for analyte in addon.analytes:
        analytes_by_assay.setdefault(analyte.assay_key, []).append(analyte)

    units_by_analyte: dict[str, list] = {}
    for unit in addon.units:
        units_by_analyte.setdefault(unit.analyte_key, []).append(unit)

    for assay in sorted(addon.assays, key=lambda a: (a.xml_id if a.xml_id is not None else -1, a.key)):
        assay_abbreviation = str((assay.metadata or {}).get("assay_abbreviation") or "").strip()
        if not assay_abbreviation:
            continue

        assay_el = ET.SubElement(assays_el, "Assay")
        ET.SubElement(assay_el, "Id").text = str(assay.xml_id if assay.xml_id is not None else 0)
        ET.SubElement(assay_el, "Name").text = assay.xml_name or assay.protocol_type or ""
        ET.SubElement(assay_el, "AddOnRef").text = str(assay.addon_ref if assay.addon_ref is not None else addon.addon_id)

        analytes_el = ET.SubElement(assay_el, "Analytes")
        for analyte in sorted(analytes_by_assay.get(assay.key, []), key=lambda a: (a.xml_id if a.xml_id is not None else -1, a.key)):
            analyte_el = ET.SubElement(analytes_el, "Analyte")
            ET.SubElement(analyte_el, "Id").text = str(analyte.xml_id if analyte.xml_id is not None else 0)
            ET.SubElement(analyte_el, "Name").text = analyte.name
            ET.SubElement(analyte_el, "AssayRef").text = str(analyte.assay_ref if analyte.assay_ref is not None else 0)

            unit_parent = ET.SubElement(analyte_el, "AnalyteUnits")
            for unit in sorted(units_by_analyte.get(analyte.key, []), key=lambda u: (u.xml_id if u.xml_id is not None else -1, u.key)):
                unit_el = ET.SubElement(unit_parent, "AnalyteUnit")
                ET.SubElement(unit_el, "Id").text = str(unit.xml_id if unit.xml_id is not None else 0)
                ET.SubElement(unit_el, "Name").text = unit.name
                ET.SubElement(unit_el, "AnalyteRef").text = str(unit.analyte_ref if unit.analyte_ref is not None else 0)

            if analyte.assay_information_type:
                ET.SubElement(analyte_el, "AssayInformationType").text = analyte.assay_information_type

    xml_content = serialize_xml_document(root)
    validation = validate_xml_against_xsd(xml_content, xsd_path)
    written = None
    if output_path is not None and not validation.issues.has_errors():
        written = write_xml_document(xml_content, output_path)
    return AddonXmlGenerationResult(xml_content=xml_content, issues=validation.issues, output_path=written)

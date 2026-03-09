from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from addon_generator.domain.issues import ValidationIssueCollection
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel
from addon_generator.serialization.xml_writer import serialize_xml_document, write_xml_document
from addon_generator.validation.xsd_validator import validate_xml_against_xsd


@dataclass(slots=True)
class AddonXmlGenerationResult:
    xml_content: str
    issues: ValidationIssueCollection
    output_path: Path | None = None


def generate_analytes_addon_xml(
    addon: AddonModel,
    xsd_path: Path | str,
    output_path: Path | str | None = None,
) -> AddonXmlGenerationResult:
    """Generate deterministic AddOn analytes XML and optionally write it after XSD validation."""

    root = ET.Element("AddOn")
    ET.SubElement(root, "AddOnRef").text = str(addon.addon_id)

    assays_el = ET.SubElement(root, "Assays")
    for assay in _sorted_assays(addon.assays):
        assays_el.append(_build_assay_element(addon.addon_id, assay))

    xml_content = serialize_xml_document(root)
    validation = validate_xml_against_xsd(xml_content, xsd_path)

    written_path: Path | None = None
    if output_path is not None and not validation.issues.has_errors():
        written_path = write_xml_document(xml_content, output_path)

    return AddonXmlGenerationResult(xml_content=xml_content, issues=validation.issues, output_path=written_path)


def _sorted_assays(assays: list[AssayModel]) -> list[AssayModel]:
    return sorted(assays, key=lambda item: (item.assay_id, item.key, item.name))


def _sorted_analytes(analytes: list[AnalyteModel]) -> list[AnalyteModel]:
    return sorted(analytes, key=lambda item: (item.analyte_id, item.key, item.name))


def _sorted_units(units: list[AnalyteUnitModel]) -> list[AnalyteUnitModel]:
    return sorted(units, key=lambda item: (item.unit_id, item.key, item.symbol, item.name))


def _build_assay_element(addon_id: int, assay: AssayModel) -> ET.Element:
    assay_el = ET.Element("Assay")
    ET.SubElement(assay_el, "AddOnRef").text = str(addon_id)
    ET.SubElement(assay_el, "AssayRef").text = str(assay.assay_id)

    analytes_el = ET.SubElement(assay_el, "Analytes")
    for analyte in _sorted_analytes(assay.analytes):
        analytes_el.append(_build_analyte_element(addon_id, assay.assay_id, analyte))

    return assay_el


def _build_analyte_element(addon_id: int, assay_id: int, analyte: AnalyteModel) -> ET.Element:
    analyte_el = ET.Element("Analyte")
    ET.SubElement(analyte_el, "AddOnRef").text = str(addon_id)
    ET.SubElement(analyte_el, "AssayRef").text = str(assay_id)
    ET.SubElement(analyte_el, "AnalyteRef").text = str(analyte.analyte_id)

    units_el = ET.SubElement(analyte_el, "AnalyteUnits")
    for unit in _sorted_units(analyte.units):
        unit_el = ET.SubElement(units_el, "AnalyteUnit")
        ET.SubElement(unit_el, "AddOnRef").text = str(addon_id)
        ET.SubElement(unit_el, "AssayRef").text = str(assay_id)
        ET.SubElement(unit_el, "AnalyteRef").text = str(analyte.analyte_id)
        ET.SubElement(unit_el, "UnitRef").text = str(unit.unit_id)

    return analyte_el

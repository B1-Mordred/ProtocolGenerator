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


def _normalized_text(value: str | None) -> str:
    return str(value or "").strip()


def _assay_name(assay) -> str:
    metadata = assay.metadata if isinstance(getattr(assay, "metadata", None), dict) else {}
    abbreviation = _normalized_text(metadata.get("assay_abbreviation"))
    return abbreviation or _normalized_text(assay.xml_name) or _normalized_text(assay.protocol_type) or _normalized_text(assay.key)


def _dedupe_analytes_by_name(analytes: list) -> list:
    deduped: list = []
    seen: set[str] = set()
    for analyte in analytes:
        normalized = _normalized_text(getattr(analyte, "name", "")).casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(analyte)
    return deduped


def _dedupe_units_by_name(units: list) -> list:
    deduped: list = []
    seen: set[str] = set()
    for unit in units:
        normalized = _normalized_text(getattr(unit, "name", "")).casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(unit)
    return deduped


def generate_analytes_addon_xml(addon: AddonModel, xsd_path: Path | str, output_path: Path | str | None = None) -> AddonXmlGenerationResult:
    if addon.method is None:
        raise ValueError("AddonModel.method is required")

    method_version = str(addon.method.method_version or "").strip() or "0.0.0.0"

    root = ET.Element("AddOn")
    ET.SubElement(root, "Id").text = "0"
    ET.SubElement(root, "MethodId").text = addon.method.product_number or addon.method.method_id or ""
    ET.SubElement(root, "MethodVersion").text = method_version

    assays_el = ET.SubElement(root, "Assays")
    analytes_by_assay: dict[str, list] = {}
    for analyte in addon.analytes:
        analytes_by_assay.setdefault(analyte.assay_key, []).append(analyte)

    units_by_analyte: dict[str, list] = {}
    for unit in addon.units:
        units_by_analyte.setdefault(unit.analyte_key, []).append(unit)

    unique_assays: list = []
    seen_assay_names: set[str] = set()
    for assay in addon.assays:
        assay_name = _assay_name(assay)
        normalized_assay_name = assay_name.casefold()
        if not normalized_assay_name or normalized_assay_name in seen_assay_names:
            continue
        seen_assay_names.add(normalized_assay_name)
        unique_assays.append(assay)

    for assay in unique_assays:
        assay_el = ET.SubElement(assays_el, "Assay")
        ET.SubElement(assay_el, "Id").text = "0"
        ET.SubElement(assay_el, "Name").text = _assay_name(assay)
        ET.SubElement(assay_el, "AddOnRef").text = "0"

        analytes_el = ET.SubElement(assay_el, "Analytes")
        assay_analytes = _dedupe_analytes_by_name(analytes_by_assay.get(assay.key, []))
        for analyte in assay_analytes:
            analyte_el = ET.SubElement(analytes_el, "Analyte")
            ET.SubElement(analyte_el, "Id").text = "0"
            ET.SubElement(analyte_el, "Name").text = analyte.name
            ET.SubElement(analyte_el, "AssayRef").text = "0"

            unit_parent = ET.SubElement(analyte_el, "AnalyteUnits")
            analyte_units = _dedupe_units_by_name(units_by_analyte.get(analyte.key, []))
            for unit in analyte_units:
                unit_el = ET.SubElement(unit_parent, "AnalyteUnit")
                ET.SubElement(unit_el, "Id").text = "0"
                ET.SubElement(unit_el, "Name").text = unit.name
                ET.SubElement(unit_el, "AnalyteRef").text = "0"


    xml_content = serialize_xml_document(root)
    validation = validate_xml_against_xsd(xml_content, xsd_path)
    written = None
    if output_path is not None and not validation.issues.has_errors():
        written = write_xml_document(xml_content, output_path)
    return AddonXmlGenerationResult(xml_content=xml_content, issues=validation.issues, output_path=written)

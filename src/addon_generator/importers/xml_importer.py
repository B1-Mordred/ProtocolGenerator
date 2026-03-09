from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from addon_generator.domain.models import AddonModel, normalize_assay_identity_fields
from addon_generator.importers.gui_mapper import map_gui_payload_to_bundle
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder


class XmlImportValidationError(ValueError):
    """Raised when XML import cannot proceed due to schema or parsing errors."""


class XmlImporter:
    XSD_NS = {"xs": "http://www.w3.org/2001/XMLSchema"}

    def __init__(self, xsd_path: str | Path = "AddOn.xsd"):
        self.xsd_path = Path(xsd_path)

    def import_xml_bundle(self, xml_path: str | Path) -> InputDTOBundle:
        xml_file = Path(xml_path)
        xml_content = xml_file.read_text(encoding="utf-8")
        root = self._validate_against_schema(xml_content)

        payload: dict[str, object] = {"method_id": root.findtext("MethodId") or "", "method_version": root.findtext("MethodVersion") or "", "assays": [], "analytes": [], "units": []}

        for assay_el in root.findall("./Assays/Assay"):
            assay_id = assay_el.findtext("Id") or ""
            assay_name = assay_el.findtext("Name") or ""
            assay_key = f"assay:{assay_id or assay_name}"
            protocol_type, protocol_display_name, xml_name = normalize_assay_identity_fields(
                protocol_type=None,
                protocol_display_name=None,
                xml_name=assay_name,
                fallback_order={
                    "protocol_type": ("xml_name",),
                    "protocol_display_name": ("xml_name",),
                },
            )
            payload["assays"].append(
                {
                    "key": assay_key,
                    "protocol_type": protocol_type,
                    "protocol_display_name": protocol_display_name,
                    "xml_name": xml_name,
                }
            )
            for analyte_el in assay_el.findall("./Analytes/Analyte"):
                analyte_id = analyte_el.findtext("Id") or ""
                analyte_name = analyte_el.findtext("Name") or ""
                analyte_key = f"analyte:{analyte_id or analyte_name}"
                payload["analytes"].append({"key": analyte_key, "name": analyte_name, "assay_key": assay_key, "assay_information_type": analyte_el.findtext("AssayInformationType") or ""})
                for unit_el in analyte_el.findall("./AnalyteUnits/AnalyteUnit"):
                    unit_id = unit_el.findtext("Id") or ""
                    unit_name = unit_el.findtext("Name") or ""
                    payload["units"].append({"key": f"unit:{unit_id or unit_name}", "name": unit_name, "analyte_key": analyte_key})
        bundle = map_gui_payload_to_bundle(payload)
        bundle.source_type = "xml"
        bundle.source_name = str(xml_file)
        bundle.provenance.setdefault("method.method_id", []).append(FieldProvenance(source_type="xml", source_file=str(xml_file), field_key="MethodId"))
        return bundle

    def import_xml(self, xml_path: str | Path) -> AddonModel:
        return CanonicalModelBuilder().build(self.import_xml_bundle(xml_path))

    def _validate_against_schema(self, xml_content: str) -> ET.Element:
        if not self.xsd_path.exists():
            raise XmlImportValidationError(f"Schema file not found: {self.xsd_path}")

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise XmlImportValidationError(f"Unable to parse XML input: {exc}") from exc

        if root.tag != "AddOn":
            raise XmlImportValidationError("XML does not conform to schema AddOn.xsd: root element must be AddOn")

        xsd_root = ET.parse(self.xsd_path).getroot()
        self._validate_required_children(root, xsd_root, "AddOn", "AddOn")

        for assay in root.findall("./Assays/Assay"):
            self._validate_required_children(assay, xsd_root, "Assay", "AddOn/Assays/Assay")
        for analyte in root.findall("./Assays/Assay/Analytes/Analyte"):
            self._validate_required_children(analyte, xsd_root, "Analyte", "AddOn/Assays/Assay/Analytes/Analyte")
        for unit in root.findall("./Assays/Assay/Analytes/Analyte/AnalyteUnits/AnalyteUnit"):
            self._validate_required_children(unit, xsd_root, "AnalyteUnit", "AddOn/.../AnalyteUnit")

        return root

    def _validate_required_children(self, xml_element: ET.Element, xsd_root: ET.Element, complex_type_name: str, path: str) -> None:
        required = self._required_children_from_xsd(xsd_root, complex_type_name)
        missing = [name for name in required if xml_element.find(name) is None]
        if missing:
            raise XmlImportValidationError(
                f"XML does not conform to schema {self.xsd_path}: {path} is missing required element(s): {', '.join(missing)}"
            )

    def _required_children_from_xsd(self, xsd_root: ET.Element, complex_type_name: str) -> list[str]:
        complex_type = xsd_root.find(f"./xs:complexType[@name='{complex_type_name}']", self.XSD_NS)
        if complex_type is None:
            return []
        sequence = complex_type.find("./xs:sequence", self.XSD_NS)
        if sequence is None:
            extension = complex_type.find("./xs:complexContent/xs:extension", self.XSD_NS)
            sequence = extension.find("./xs:sequence", self.XSD_NS) if extension is not None else None
        if sequence is None:
            return []

        required: list[str] = []
        extension = complex_type.find("./xs:complexContent/xs:extension", self.XSD_NS)
        if extension is not None:
            base = extension.get("base")
            if base:
                required.extend(self._required_children_from_xsd(xsd_root, base))

        for element in sequence.findall("./xs:element", self.XSD_NS):
            if element.get("minOccurs", "1") == "0":
                continue
            name = element.get("name")
            if name:
                required.append(name)
        return required

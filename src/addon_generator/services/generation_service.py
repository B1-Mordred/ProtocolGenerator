from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from addon_generator.domain.issues import ValidationIssue
from addon_generator.domain.models import AddonModel
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.generators.protocol_json_generator import generate_protocol_json
from addon_generator.importers import ExcelImporter, XmlImporter, map_gui_payload_to_addon
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain
from addon_generator.validation.protocol_schema_validator import validate_protocol_schema


@dataclass(slots=True)
class GenerationResult:
    addon_model: AddonModel
    protocol_json: dict[str, Any]
    analytes_xml_string: str
    issues: list[ValidationIssue]
    warnings: list[ValidationIssue]
    resolved_mapping_snapshot: dict[str, Any]
    merge_report: dict[str, Any]
    unresolved_required_fields: list[str]
    conflicting_required_fields: list[str]


class GenerationService:
    def __init__(self, mapping_path: str | Path = "config/mapping.v1.yaml"):
        self.mapping = load_mapping_config(mapping_path)
        self.resolver = LinkResolver(self.mapping)

    def import_from_excel(self, path: str) -> AddonModel:
        return ExcelImporter().import_workbook(path)

    def import_from_gui_payload(self, payload: dict[str, Any]) -> AddonModel:
        return map_gui_payload_to_addon(payload)

    def import_from_xml(self, path: str) -> AddonModel:
        return XmlImporter().import_xml(path)

    def validate_domain(self, addon: AddonModel):
        return validate_domain(addon).issues

    def generate_analytes_xml(self, addon: AddonModel, xsd_path: str | Path = "AddOn.xsd") -> str:
        self.resolver.assign_ids(addon)
        return generate_analytes_addon_xml(addon, xsd_path=xsd_path).xml_content

    def generate_protocol_json(self, addon: AddonModel, protocol_fragments: dict[str, Any] | None = None):
        self.resolver.assign_ids(addon)
        return generate_protocol_json(addon, self.resolver, protocol_fragments)

    def generate_all(self, addon: AddonModel, *, xsd_path: str | Path = "AddOn.xsd", protocol_schema_path: str | Path = "protocol.schema.json") -> GenerationResult:
        self.resolver.assign_ids(addon)
        issues = list(validate_domain(addon).issues.issues)
        issues.extend(self.resolver.validate_cross_file_linkage(addon))

        xml_result = generate_analytes_addon_xml(addon, xsd_path=xsd_path)
        issues.extend(xml_result.issues.issues)

        protocol_result = self.generate_protocol_json(addon)
        protocol_json = protocol_result.payload
        protocol_schema_result = validate_protocol_schema(protocol_json, schema_path=protocol_schema_path)
        issues.extend(protocol_schema_result.issues.issues)

        cross_file = validate_cross_file_consistency(protocol_json, ET.fromstring(xml_result.xml_content))
        issues.extend(cross_file.issues.issues)

        warnings = [i for i in issues if i.severity.value == "warning"]
        errors = [i for i in issues if i.severity.value == "error"]
        return GenerationResult(
            addon_model=addon,
            protocol_json=protocol_json,
            analytes_xml_string=xml_result.xml_content,
            issues=errors,
            warnings=warnings,
            resolved_mapping_snapshot=self.mapping.raw,
            merge_report=protocol_result.merge_report,
            unresolved_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("unresolved", [])),
            conflicting_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("conflicting", [])),
        )


def fragments_from_protocol_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return payload

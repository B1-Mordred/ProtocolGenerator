from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from addon_generator.domain.fragments import FragmentCollection, ProtocolFragment
from addon_generator.domain.issues import IssueSource, IssueSeverity, ValidationIssue, ValidationIssueCollection
from addon_generator.domain.models import ProtocolContextModel
from addon_generator.generators.analytes_xml_generator import AddonXmlGenerationResult, generate_analytes_addon_xml
from addon_generator.importers import ExcelImporter, map_gui_payload_to_context
from addon_generator.generators.protocol_generator import ProtocolJsonGenerationResult, generate_protocol_json as materialize_protocol_json


@dataclass(slots=True)
class GenerationArtifacts:
    domain_issues: ValidationIssueCollection
    analytes_xml: AddonXmlGenerationResult
    protocol_json: ProtocolJsonGenerationResult


class GenerationService:
    def import_from_excel(self, excel_path: str | Path) -> ProtocolContextModel:
        return ExcelImporter().import_workbook(excel_path)

    def import_from_gui_payload(self, payload: dict[str, Any]) -> ProtocolContextModel:
        return map_gui_payload_to_context(payload)

    def validate_domain(self, context: ProtocolContextModel) -> ValidationIssueCollection:
        issues = ValidationIssueCollection()
        if not context.addon.addon_name:
            issues.add(
                ValidationIssue(
                    code="missing-addon-name",
                    message="Addon name is required",
                    path="addon.addon_name",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.DOMAIN,
                )
            )
        if not context.addon.assays:
            issues.add(
                ValidationIssue(
                    code="missing-assays",
                    message="At least one assay is required",
                    path="addon.assays",
                    severity=IssueSeverity.ERROR,
                    source=IssueSource.DOMAIN,
                )
            )
        return issues

    def generate_analytes_xml(
        self, context: ProtocolContextModel, xsd_path: str | Path, output_path: str | Path | None = None
    ) -> AddonXmlGenerationResult:
        return generate_analytes_addon_xml(context.addon, xsd_path=xsd_path, output_path=output_path)

    def generate_protocol_json(self, context: ProtocolContextModel, protocol_fragments: FragmentCollection) -> ProtocolJsonGenerationResult:
        return materialize_protocol_json(context, protocol_fragments)

    def generate_all(
        self,
        context: ProtocolContextModel,
        protocol_fragments: FragmentCollection,
        xsd_path: str | Path,
        xml_output_path: str | Path | None = None,
    ) -> GenerationArtifacts:
        domain_issues = self.validate_domain(context)
        xml_result = self.generate_analytes_xml(context=context, xsd_path=xsd_path, output_path=xml_output_path)
        protocol_result = self.generate_protocol_json(context=context, protocol_fragments=protocol_fragments)
        return GenerationArtifacts(domain_issues=domain_issues, analytes_xml=xml_result, protocol_json=protocol_result)


def fragments_from_protocol_payload(payload: dict[str, Any]) -> FragmentCollection:
    fragments = FragmentCollection()
    for key in ("MethodInformation", "AssayInformation", "LoadingWorkflowSteps", "ProcessingWorkflowSteps"):
        if key in payload:
            fragments.add(ProtocolFragment(path=(key,), value=payload[key], origin="ui"))
    return fragments

from __future__ import annotations

from dataclasses import dataclass

from addon_generator.domain.ids import assign_deterministic_ids
from addon_generator.domain.issues import IssueSeverity, IssueSource, ValidationIssue
from addon_generator.domain.models import AddonModel, AnalyteModel, AssayModel, normalize_assay_identity_fields
from addon_generator.mapping.config_loader import MappingConfig
from addon_generator.mapping.normalizers import normalize_for_matching


@dataclass(slots=True)
class ResolvedMethodProjection:
    protocol_id: str
    protocol_version: str
    xml_method_id: str
    xml_method_version: str


@dataclass(slots=True)
class ResolvedAssayProjection:
    protocol_type: str
    protocol_display_name: str | None
    xml_name: str
    xml_id: int
    addon_ref: int


@dataclass(slots=True)
class ResolvedAnalyteProjection:
    xml_id: int
    xml_name: str
    assay_ref: int
    assay_information_type: str | None


class LinkResolver:
    def __init__(self, config: MappingConfig):
        self.config = config

    def assign_ids(self, addon: AddonModel) -> AddonModel:
        ids = self.config.raw["ids"]
        return assign_deterministic_ids(
            addon,
            assay_start=int(ids["assay"]["start"]),
            analyte_start=int(ids["analyte"]["start"]),
            unit_start=int(ids["analyte_unit"]["start"]),
        )

    def resolve_method_projection(self, addon: AddonModel) -> ResolvedMethodProjection:
        method = addon.method
        if method is None:
            raise ValueError("AddonModel.method is required")
        return ResolvedMethodProjection(
            protocol_id=method.method_id,
            protocol_version=method.method_version,
            xml_method_id=method.method_id,
            xml_method_version=method.method_version,
        )

    def resolve_assay_projection(self, assay: AssayModel) -> ResolvedAssayProjection:
        fallbacks = self.config.raw.get("assay_mapping", {}).get("projection_fallbacks", {})
        protocol_type, protocol_display_name, xml_name = normalize_assay_identity_fields(
            protocol_type=assay.protocol_type,
            protocol_display_name=assay.protocol_display_name,
            xml_name=assay.xml_name,
            fallback_order=fallbacks if isinstance(fallbacks, dict) else None,
        )
        return ResolvedAssayProjection(
            protocol_type=protocol_type or "",
            protocol_display_name=protocol_display_name,
            xml_name=xml_name or "",
            xml_id=assay.xml_id if assay.xml_id is not None else 0,
            addon_ref=assay.addon_ref if assay.addon_ref is not None else 0,
        )

    def resolve_analyte_projection(self, analyte: AnalyteModel) -> ResolvedAnalyteProjection:
        return ResolvedAnalyteProjection(
            xml_id=analyte.xml_id if analyte.xml_id is not None else 0,
            xml_name=analyte.name,
            assay_ref=analyte.assay_ref if analyte.assay_ref is not None else 0,
            assay_information_type=analyte.assay_information_type,
        )

    def validate_cross_file_linkage(self, addon: AddonModel) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        mode = self.config.raw["assay_mapping"]["cross_file_match"].get("mode", "exact")

        protocol_types = [assay.protocol_type or "" for assay in addon.assays]
        xml_names = [assay.xml_name or "" for assay in addon.assays]
        for p, x in zip(protocol_types, xml_names):
            if mode == "exact" and p != x:
                issues.append(
                    ValidationIssue(
                        code="assay-cross-file-mismatch",
                        message=f"Protocol assay type '{p}' does not match XML assay name '{x}'",
                        path="assays",
                        severity=IssueSeverity.ERROR,
                        source=IssueSource.PROJECTION,
                    )
                )
            if mode == "normalized" and normalize_for_matching(p) != normalize_for_matching(x):
                issues.append(
                    ValidationIssue(
                        code="assay-cross-file-mismatch",
                        message=f"Protocol assay type '{p}' does not match XML assay name '{x}'",
                        path="assays",
                        severity=IssueSeverity.ERROR,
                        source=IssueSource.PROJECTION,
                    )
                )
        return issues

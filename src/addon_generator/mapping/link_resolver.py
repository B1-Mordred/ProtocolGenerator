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
        method_product_number = str(method.product_number or "").strip()
        method_version = str(method.method_version or "").strip() or "0.0.0.0"
        protocol_id = method_product_number or method.method_id

        return ResolvedMethodProjection(
            protocol_id=protocol_id,
            protocol_version=method_version,
            xml_method_id=protocol_id,
            xml_method_version=method_version,
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
        cross_file_match = self.config.raw["assay_mapping"]["cross_file_match"]
        mode = cross_file_match.get("mode", "exact")
        alias_map = cross_file_match.get("alias_map", {}) if isinstance(cross_file_match, dict) else {}

        protocol_types = [assay.protocol_type or "" for assay in addon.assays]
        xml_names = [assay.xml_name or "" for assay in addon.assays]
        for p, x in zip(protocol_types, xml_names):
            if not self._assay_names_match(p, x, mode=mode, alias_map=alias_map):
                issues.append(
                    self._build_assay_mismatch_issue(protocol_type=p, xml_name=x, mode=mode)
                )
        return issues

    def _assay_names_match(self, protocol_type: str, xml_name: str, *, mode: str, alias_map: dict[str, str]) -> bool:
        if mode == "normalized":
            return normalize_for_matching(protocol_type) == normalize_for_matching(xml_name)
        if mode == "alias_map":
            mapped_protocol = self._apply_alias_map(protocol_type, alias_map)
            mapped_xml = self._apply_alias_map(xml_name, alias_map)
            return mapped_protocol == mapped_xml
        return protocol_type == xml_name

    def _apply_alias_map(self, value: str, alias_map: dict[str, str]) -> str:
        if not alias_map:
            return value
        canonical_map = {k.strip(): v.strip() for k, v in alias_map.items() if isinstance(k, str) and isinstance(v, str)}
        if value in canonical_map:
            return canonical_map[value]
        reverse_lookup = {target: target for target in canonical_map.values()}
        return reverse_lookup.get(value, value)

    def _build_assay_mismatch_issue(self, *, protocol_type: str, xml_name: str, mode: str) -> ValidationIssue:
        recommended_action = "Set XML assay name equal to Type or change matching mode to alias_map/normalized."
        if mode == "normalized":
            recommended_action = "Normalize Type and XML assay name to the same value or switch to alias_map mode."
        if mode == "alias_map":
            recommended_action = "Add/adjust assay_mapping.cross_file_match.alias_map so Type and XML assay name resolve to the same canonical value."
        return ValidationIssue(
            code="assay-cross-file-mismatch",
            message=f"Protocol assay type '{protocol_type}' does not match XML assay name '{xml_name}' under mode '{mode}'.",
            path="assays",
            severity=IssueSeverity.ERROR,
            source=IssueSource.PROJECTION,
            details={"recommended_action": recommended_action},
        )

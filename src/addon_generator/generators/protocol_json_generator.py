from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.models import AddonModel
from addon_generator.mapping.link_resolver import LinkResolver


@dataclass(slots=True)
class ProtocolJsonGenerationResult:
    payload: dict[str, Any]


class ProtocolJsonGenerator:
    def __init__(self, resolver: LinkResolver):
        self.resolver = resolver

    def generate(self, addon: AddonModel, protocol_fragments: dict[str, Any] | None = None) -> ProtocolJsonGenerationResult:
        defaults = self.resolver.config.raw.get("protocol_defaults", {})
        payload = {
            "MethodInformation": self._build_method_information(addon, defaults.get("method_information", {})),
            "AssayInformation": self._build_assay_information(addon, defaults.get("assay_information", {})),
            "LoadingWorkflowSteps": self._build_loading_workflow_steps(addon, defaults.get("loading_workflow_steps", [])),
            "ProcessingWorkflowSteps": self._build_processing_workflow_steps(addon, defaults.get("processing_workflow_steps", [])),
        }

        context = addon.protocol_context
        if context:
            payload["MethodInformation"].update(context.method_information_overrides)
            if context.assay_fragments:
                payload["AssayInformation"] = context.assay_fragments
            if context.loading_fragments:
                payload["LoadingWorkflowSteps"] = context.loading_fragments
            if context.processing_fragments:
                payload["ProcessingWorkflowSteps"] = context.processing_fragments

        if protocol_fragments:
            for key in ("MethodInformation", "AssayInformation", "LoadingWorkflowSteps", "ProcessingWorkflowSteps"):
                if key in protocol_fragments and protocol_fragments[key]:
                    payload[key] = protocol_fragments[key]

        return ProtocolJsonGenerationResult(payload=payload)

    def _build_method_information(self, addon: AddonModel, defaults: dict[str, Any]) -> dict[str, Any]:
        projection = self.resolver.resolve_method_projection(addon)
        method = addon.method
        return {
            "Id": projection.protocol_id,
            "DisplayName": self._resolve_required_default(method.display_name if method else None, defaults.get("DisplayName"), "Method"),
            "Version": projection.protocol_version,
            "MainTitle": self._resolve_required_default(method.main_title if method else None, defaults.get("MainTitle"), "Main"),
            "SubTitle": self._resolve_required_default(method.sub_title if method else None, defaults.get("SubTitle"), "Sub"),
            "OrderNumber": self._resolve_required_default(method.order_number if method else None, defaults.get("OrderNumber"), "O-1"),
            "MaximumNumberOfSamples": int(defaults.get("MaximumNumberOfSamples", 1)),
            "MaximumNumberOfProcessingCycles": int(defaults.get("MaximumNumberOfProcessingCycles", 1)),
            "MaximumNumberOfAssays": max(1, int(defaults.get("MaximumNumberOfAssays", len(addon.assays) if addon.assays else 1))),
            "SamplesLayoutType": defaults.get("SamplesLayoutType", "SAMPLES_LAYOUT_COMBINED"),
            "MethodInformationType": defaults.get("MethodInformationType", "REGULAR"),
        }

    def _build_assay_information(self, addon: AddonModel, defaults: dict[str, Any]) -> list[dict[str, Any]]:
        assays: list[dict[str, Any]] = []
        for assay in sorted(addon.assays, key=lambda a: a.key):
            projection = self.resolver.resolve_assay_projection(assay)
            assay_record = dict(defaults)
            assay_record.update({
                "Type": projection.protocol_type or projection.xml_name,
                "DisplayName": projection.protocol_display_name or projection.xml_name or defaults.get("DisplayName", "Assay"),
            })
            assays.append(assay_record)
        if not assays:
            assay_record = dict(defaults)
            assay_record.update({"Type": "A", "DisplayName": defaults.get("DisplayName", "Assay")})
            assays.append(assay_record)
        return assays

    def _build_loading_workflow_steps(self, addon: AddonModel, defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return defaults if defaults else []

    def _build_processing_workflow_steps(self, addon: AddonModel, defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return defaults if defaults else []

    @staticmethod
    def _resolve_required_default(primary: Any, fallback: Any, hard_default: Any) -> Any:
        if primary is not None and str(primary).strip() != "":
            return primary
        if fallback is not None and str(fallback).strip() != "":
            return fallback
        return hard_default


def generate_protocol_json(addon: AddonModel, resolver: LinkResolver, protocol_fragments: dict[str, Any] | None = None) -> ProtocolJsonGenerationResult:
    return ProtocolJsonGenerator(resolver).generate(addon, protocol_fragments)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.models import AddonModel
from addon_generator.mapping.link_resolver import LinkResolver


@dataclass(slots=True)
class ProtocolJsonGenerationResult:
    payload: dict[str, Any]


def generate_protocol_json(addon: AddonModel, resolver: LinkResolver) -> ProtocolJsonGenerationResult:
    method_projection = resolver.resolve_method_projection(addon)
    assay_info: list[dict[str, Any]] = []
    for assay in sorted(addon.assays, key=lambda a: a.key):
        projection = resolver.resolve_assay_projection(assay)
        record: dict[str, Any] = {"Type": projection.protocol_type}
        if projection.protocol_display_name:
            record["DisplayName"] = projection.protocol_display_name
        assay_info.append(record)

    payload: dict[str, Any] = {
        "MethodInformation": {
            "Id": method_projection.protocol_id,
            "Version": method_projection.protocol_version,
        },
        "AssayInformation": assay_info,
        "LoadingWorkflowSteps": [],
        "ProcessingWorkflowSteps": [],
    }

    if addon.protocol_context:
        payload["MethodInformation"].update(addon.protocol_context.method_information_overrides)
        if addon.protocol_context.assay_fragments:
            payload["AssayInformation"] = addon.protocol_context.assay_fragments
        if addon.protocol_context.loading_fragments:
            payload["LoadingWorkflowSteps"] = addon.protocol_context.loading_fragments
        if addon.protocol_context.processing_fragments:
            payload["ProcessingWorkflowSteps"] = addon.protocol_context.processing_fragments

    return ProtocolJsonGenerationResult(payload=payload)

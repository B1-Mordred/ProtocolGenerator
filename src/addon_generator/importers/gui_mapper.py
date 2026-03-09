from __future__ import annotations

from typing import Any

from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel, ProtocolContextModel


def map_gui_payload_to_addon(payload: dict[str, Any]) -> AddonModel:
    method_info = payload.get("MethodInformation", {}) if isinstance(payload.get("MethodInformation"), dict) else {}
    method_id = str(payload.get("method_id") or method_info.get("Id") or "")
    method_version = str(payload.get("method_version") or method_info.get("Version") or "")
    method_key = str(payload.get("method_key") or f"method:{method_id or 'default'}")
    method = MethodModel(
        key=method_key,
        method_id=method_id,
        method_version=method_version,
        display_name=method_info.get("DisplayName"),
    )

    assay_rows = payload.get("assays") if isinstance(payload.get("assays"), list) else []

    if not assay_rows and isinstance(payload.get("AssayInformation"), list):
        for idx, assay in enumerate(payload.get("AssayInformation", [])):
            if isinstance(assay, dict):
                assay_rows.append({
                    "key": assay.get("Type") or f"assay:{idx}",
                    "protocol_type": assay.get("Type") or "",
                    "protocol_display_name": assay.get("DisplayName"),
                    "xml_name": assay.get("Type") or "",
                })

    analyte_rows = payload.get("analytes") if isinstance(payload.get("analytes"), list) else []
    unit_rows = payload.get("units") if isinstance(payload.get("units"), list) else []

    assays: list[AssayModel] = [
        AssayModel(
            key=str(row["key"]),
            protocol_type=str(row.get("protocol_type") or ""),
            protocol_display_name=row.get("protocol_display_name"),
            xml_name=str(row.get("xml_name") or row.get("protocol_type") or ""),
        )
        for row in assay_rows
    ]

    analytes: list[AnalyteModel] = [
        AnalyteModel(
            key=str(row["key"]),
            name=str(row.get("name") or ""),
            assay_key=str(row.get("assay_key") or ""),
            assay_information_type=row.get("assay_information_type"),
        )
        for row in analyte_rows
    ]

    units: list[AnalyteUnitModel] = [
        AnalyteUnitModel(
            key=str(row["key"]),
            name=str(row.get("name") or ""),
            analyte_key=str(row.get("analyte_key") or ""),
        )
        for row in unit_rows
    ]

    method_overrides = dict(payload.get("method_information_overrides", {}))
    if isinstance(method_info, dict):
        method_overrides = {**method_info, **method_overrides}
    protocol_context = ProtocolContextModel(
        method_information_overrides=method_overrides,
        assay_fragments=payload.get("AssayInformation", []),
        loading_fragments=payload.get("LoadingWorkflowSteps", []),
        processing_fragments=payload.get("ProcessingWorkflowSteps", []),
    )

    return AddonModel(
        addon_id=0,
        method=method,
        assays=assays,
        analytes=analytes,
        units=units,
        protocol_context=protocol_context,
        source_metadata={"source": "gui"},
    )

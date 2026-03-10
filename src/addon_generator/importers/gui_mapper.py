from __future__ import annotations

from typing import Any

from addon_generator.domain.models import AddonModel, normalize_assay_identity_fields
from addon_generator.input_models.dtos import AnalyteInputDTO, AssayInputDTO, InputDTOBundle, MethodInputDTO, UnitInputDTO
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder


def _split_multi_value(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(v).strip() for v in raw if str(v).strip()]
    text = str(raw).strip()
    if not text:
        return []
    normalized = text.replace("|", ";").replace(",", ";")
    return [part.strip() for part in normalized.split(";") if part.strip()]


def map_gui_payload_to_bundle(payload: dict[str, Any]) -> InputDTOBundle:
    method_info = payload.get("MethodInformation", {}) if isinstance(payload.get("MethodInformation"), dict) else {}
    method_id = str(payload.get("method_id") or method_info.get("Id") or "")
    method_version = str(payload.get("method_version") or method_info.get("Version") or "")
    method_key = str(payload.get("method_key") or f"method:{method_id or 'default'}")

    method = MethodInputDTO(
        key=method_key,
        method_id=method_id,
        method_version=method_version,
        display_name=method_info.get("DisplayName"),
        main_title=method_info.get("MainTitle"),
        sub_title=method_info.get("SubTitle"),
        order_number=method_info.get("OrderNumber"),
        series_name=method_info.get("SeriesName"),
        product_name=method_info.get("ProductName"),
        product_number=method_info.get("ProductNumber"),
    )

    assay_rows = payload.get("assays") if isinstance(payload.get("assays"), list) else []
    analyte_rows = payload.get("analytes") if isinstance(payload.get("analytes"), list) else []
    unit_rows = payload.get("units") if isinstance(payload.get("units"), list) else []

    assays: list[AssayInputDTO] = []
    for idx, row in enumerate(assay_rows):
        parameter_set_number = str(row.get("parameter_set_number") or "").strip()
        component_name = str(row.get("component_name") or "").strip()
        assay_abbreviation = str(row.get("assay_abbreviation") or "").strip()
        assay_type = str(row.get("type") or "").strip()

        assay_key = str(row.get("key") or parameter_set_number or component_name or f"assay:{idx + 1}").strip()
        protocol_type, protocol_display_name, xml_name = normalize_assay_identity_fields(
            protocol_type=row.get("protocol_type") or assay_type,
            protocol_display_name=row.get("protocol_display_name") or component_name,
            xml_name=row.get("xml_name") or row.get("parameter_set_name") or component_name,
        )
        metadata = {
            "product_number": str(row.get("product_number") or "").strip(),
            "component_name": component_name,
            "parameter_set_number": parameter_set_number,
            "assay_abbreviation": assay_abbreviation,
            "parameter_set_name": str(row.get("parameter_set_name") or "").strip(),
            "type": assay_type,
            "container_type": str(row.get("container_type") or "").strip(),
        }
        assays.append(
            AssayInputDTO(
                key=assay_key,
                protocol_type=protocol_type,
                protocol_display_name=protocol_display_name,
                xml_name=xml_name,
                metadata=metadata,
            )
        )
    analytes: list[AnalyteInputDTO] = []
    for idx, row in enumerate(analyte_rows):
        key = str(row.get("key") or row.get("analyte_key") or f"analyte:{idx + 1}").strip()
        name = str(row.get("name") or row.get("analyte_name") or "").strip()
        assay_key = str(row.get("assay_key") or row.get("assay") or "").strip()
        analytes.append(
            AnalyteInputDTO(
                key=key,
                name=name,
                assay_key=assay_key,
                assay_information_type=row.get("assay_information_type"),
            )
        )

    normalized_unit_rows = list(unit_rows)
    for analyte_idx, analyte_row in enumerate(analyte_rows):
        analyte_key = str(analyte_row.get("key") or analyte_row.get("analyte_key") or f"analyte:{analyte_idx + 1}").strip()
        unit_names = _split_multi_value(analyte_row.get("unit_names") or analyte_row.get("units"))
        for idx, unit_name in enumerate(unit_names):
            normalized_unit_rows.append({"key": f"{analyte_key}:unit:{idx}:{unit_name}", "name": unit_name, "analyte_key": analyte_key})

    units = [UnitInputDTO(key=str(row["key"]), name=str(row.get("name") or ""), analyte_key=str(row.get("analyte_key") or "")) for row in normalized_unit_rows]

    provenance = {
        "method.method_id": [FieldProvenance(source_type="gui", field_key="method_id", is_override=True)],
        "method.method_version": [FieldProvenance(source_type="gui", field_key="method_version", is_override=True)],
    }

    return InputDTOBundle(
        source_type="gui",
        source_name="gui",
        method=method,
        assays=assays,
        analytes=analytes,
        units=units,
        method_information_overrides={**method_info, **dict(payload.get("method_information_overrides", {}))},
        assay_fragments=payload.get("AssayInformation", []),
        loading_fragments=payload.get("LoadingWorkflowSteps", []),
        processing_fragments=payload.get("ProcessingWorkflowSteps", []),
        provenance=provenance,
    )


def map_gui_payload_to_addon(payload: dict[str, Any]) -> AddonModel:
    return CanonicalModelBuilder().build(map_gui_payload_to_bundle(payload))

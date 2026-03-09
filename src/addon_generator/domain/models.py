from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_assay_identity_fields(
    *,
    protocol_type: str | None,
    protocol_display_name: str | None,
    xml_name: str | None,
    fallback_order: dict[str, tuple[str, ...]] | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Normalize assay identity fields with optional, explicit fallback rules."""

    values: dict[str, str | None] = {
        "protocol_type": _clean_optional_text(protocol_type),
        "protocol_display_name": _clean_optional_text(protocol_display_name),
        "xml_name": _clean_optional_text(xml_name),
    }
    if fallback_order:
        for target, sources in fallback_order.items():
            if values.get(target):
                continue
            for source in sources:
                candidate = values.get(source)
                if candidate:
                    values[target] = candidate
                    break

    return values["protocol_type"], values["protocol_display_name"], values["xml_name"]


@dataclass(slots=True)
class MethodModel:
    key: str
    method_id: str
    method_version: str
    display_name: str | None = None
    main_title: str | None = None
    sub_title: str | None = None
    order_number: str | None = None
    series_name: str | None = None
    product_name: str | None = None
    product_number: str | None = None
    legacy_protocol_id: str | None = None


@dataclass(slots=True)
class AssayModel:
    key: str
    xml_id: int | None = None
    source_row_id: str | None = None
    display_name: str | None = None
    protocol_type: str | None = None
    protocol_display_name: str | None = None
    xml_name: str | None = None
    addon_ref: int | None = None
    aliases: list[str] = field(default_factory=list)
    analyte_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnalyteModel:
    key: str
    name: str
    assay_key: str
    xml_id: int | None = None
    assay_ref: int | None = None
    assay_information_type: str | None = None
    unit_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnalyteUnitModel:
    key: str
    name: str
    analyte_key: str
    xml_id: int | None = None
    analyte_ref: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProtocolContextModel:
    method_information_overrides: dict[str, Any] = field(default_factory=dict)
    assay_fragments: list[dict[str, Any]] = field(default_factory=list)
    loading_fragments: list[dict[str, Any]] = field(default_factory=list)
    processing_fragments: list[dict[str, Any]] = field(default_factory=list)
    dilution_fragments: list[dict[str, Any]] = field(default_factory=list)
    reagent_fragments: list[dict[str, Any]] = field(default_factory=list)
    calibrator_fragments: list[dict[str, Any]] = field(default_factory=list)
    control_fragments: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class AddonModel:
    addon_id: int = 0
    method: MethodModel | None = None
    assays: list[AssayModel] = field(default_factory=list)
    analytes: list[AnalyteModel] = field(default_factory=list)
    units: list[AnalyteUnitModel] = field(default_factory=list)
    sample_tube_types: list[dict[str, Any]] = field(default_factory=list)
    measurement_sample_lists: list[dict[str, Any]] = field(default_factory=list)
    run_results_export_path: str | None = None
    protocol_context: ProtocolContextModel | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)

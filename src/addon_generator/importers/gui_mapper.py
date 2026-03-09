from __future__ import annotations

from typing import Any

from addon_generator.domain.fragments import FragmentCollection, ProtocolFragment
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel, ProtocolContextModel

_FRAGMENT_SOURCE_KEYS: dict[str, tuple[str, ...]] = {
    "loading": ("LoadingWorkflowSteps",),
    "processing": ("ProcessingWorkflowSteps",),
    "dilution": ("DilutionWorkflowSteps", "DilutionSettings", "Dilution"),
    "reagent": ("ReagentWorkflowSteps", "ReagentSettings", "Reagent"),
    "calibrator": ("CalibratorWorkflowSteps", "CalibratorSettings", "Calibrator"),
    "control": ("ControlWorkflowSteps", "ControlSettings", "Control"),
}


def _build_fragment_collection(key: str, value: Any, origin: str) -> FragmentCollection:
    fragments = FragmentCollection()
    fragments.add(ProtocolFragment(path=(key,), value=value, origin=origin))
    return fragments


def extract_context_fragments(payload: dict[str, Any], origin: str = "gui") -> dict[str, FragmentCollection]:
    """Extract optional protocol context fragments from payload sections."""

    context_fragments: dict[str, FragmentCollection] = {}
    for fragment_name, aliases in _FRAGMENT_SOURCE_KEYS.items():
        for alias in aliases:
            if alias in payload:
                context_fragments[fragment_name] = _build_fragment_collection(alias, payload[alias], origin)
                break
    return context_fragments


def map_gui_payload_to_context(payload: dict[str, Any]) -> ProtocolContextModel:
    """Map UI payload rows into the canonical addon domain model."""

    rows = payload["rows"] if "rows" in payload else [payload]

    methods: dict[str, MethodModel] = {}
    assays: dict[str, AssayModel] = {}
    analytes: dict[str, AnalyteModel] = {}
    units: dict[str, AnalyteUnitModel] = {}

    for row in rows:
        method_info = row.get("MethodInformation", {}) if isinstance(row.get("MethodInformation"), dict) else {}
        assay_info = row.get("AssayInformation", [])
        first_assay = assay_info[0] if isinstance(assay_info, list) and assay_info else {}

        method_name = str(row.get("MethodDisplayName") or method_info.get("DisplayName") or "Method").strip()
        assay_name = str(row.get("AssayDisplayName") or first_assay.get("DisplayName") or "Assay").strip()
        analyte_name = str(row.get("AnalyteName") or "Analyte").strip()
        unit_name = str(row.get("UnitName") or "Unit").strip()

        method_key = f"method:{method_name.casefold()}"
        assay_key = f"assay:{assay_name.casefold()}"
        analyte_key = f"analyte:{assay_key}:{analyte_name.casefold()}"
        unit_key = f"unit:{analyte_key}:{unit_name.casefold()}"

        methods.setdefault(method_key, MethodModel(key=method_key, method_id=len(methods) + 1, display_name=method_name))
        assay_model = assays.setdefault(assay_key, AssayModel(key=assay_key, assay_id=len(assays) + 1, name=assay_name))
        analyte_model = analytes.setdefault(
            analyte_key,
            AnalyteModel(key=analyte_key, analyte_id=len(analytes) + 1, name=analyte_name),
        )
        units.setdefault(unit_key, AnalyteUnitModel(key=unit_key, unit_id=len(units) + 1, name=unit_name, symbol=unit_name))

        if analyte_model not in assay_model.analytes:
            assay_model.analytes.append(analyte_model)
        unit_model = units[unit_key]
        if unit_model not in analyte_model.units:
            analyte_model.units.append(unit_model)

    method_information = payload.get("MethodInformation", {})
    addon_name = str(method_information.get("DisplayName") or payload.get("addon_name") or "Generated Addon")
    addon_id_raw = method_information.get("Id") or payload.get("addon_id") or 0
    try:
        addon_id = int(addon_id_raw)
    except (TypeError, ValueError):
        addon_id = 0

    addon = AddonModel(addon_id=addon_id, addon_name=addon_name, methods=list(methods.values()), assays=list(assays.values()))
    return ProtocolContextModel(
        addon=addon,
        method_index=methods,
        assay_index=assays,
        analyte_index=analytes,
        unit_index=units,
        context_fragments=extract_context_fragments(payload),
    )

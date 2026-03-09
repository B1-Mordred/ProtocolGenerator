from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MethodModel:
    """Internal method representation with a stable internal identity key."""

    key: str
    method_id: int = 0
    display_name: str = ""


@dataclass(slots=True)
class AnalyteUnitModel:
    """Internal analyte unit representation with stable key."""

    key: str
    unit_id: int = 0
    symbol: str = ""
    name: str = ""


@dataclass(slots=True)
class AnalyteModel:
    """Internal analyte representation with stable key and unit references."""

    key: str
    analyte_id: int = 0
    name: str = ""
    units: list[AnalyteUnitModel] = field(default_factory=list)


@dataclass(slots=True)
class AssayModel:
    """Internal assay representation with stable key and analytes."""

    key: str
    assay_id: int = 0
    name: str = ""
    analytes: list[AnalyteModel] = field(default_factory=list)


@dataclass(slots=True)
class AddonModel:
    """Top-level addon projection model."""

    addon_id: int = 0
    addon_name: str = ""
    methods: list[MethodModel] = field(default_factory=list)
    assays: list[AssayModel] = field(default_factory=list)


@dataclass(slots=True)
class ProtocolContextModel:
    """Materialized context that keeps addon and generation metadata together."""

    addon: AddonModel = field(default_factory=AddonModel)
    method_index: dict[str, MethodModel] = field(default_factory=dict)
    assay_index: dict[str, AssayModel] = field(default_factory=dict)
    analyte_index: dict[str, AnalyteModel] = field(default_factory=dict)
    unit_index: dict[str, AnalyteUnitModel] = field(default_factory=dict)

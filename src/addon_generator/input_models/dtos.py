from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from addon_generator.input_models.provenance import FieldProvenance, SourceType


@dataclass(slots=True)
class MethodInputDTO:
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
class AssayInputDTO:
    key: str
    protocol_type: str | None = None
    protocol_display_name: str | None = None
    xml_name: str | None = None
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnalyteInputDTO:
    key: str
    name: str
    assay_key: str
    assay_information_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UnitInputDTO:
    key: str
    name: str
    analyte_key: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SamplePrepStepInputDTO:
    key: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DilutionSchemeInputDTO:
    key: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InputDTOBundle:
    source_type: SourceType
    source_name: str | None = None
    method: MethodInputDTO | None = None
    assays: list[AssayInputDTO] = field(default_factory=list)
    analytes: list[AnalyteInputDTO] = field(default_factory=list)
    units: list[UnitInputDTO] = field(default_factory=list)
    sample_prep_steps: list[SamplePrepStepInputDTO] = field(default_factory=list)
    dilution_schemes: list[DilutionSchemeInputDTO] = field(default_factory=list)
    method_information_overrides: dict[str, Any] = field(default_factory=dict)
    assay_fragments: list[dict[str, Any]] = field(default_factory=list)
    loading_fragments: list[dict[str, Any]] = field(default_factory=list)
    processing_fragments: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, list[FieldProvenance]] = field(default_factory=dict)

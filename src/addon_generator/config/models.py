from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MatchMode = Literal["exact", "normalized", "alias_map", "explicit_key"]


@dataclass(slots=True)
class SequentialIdConfig:
    strategy: Literal["sequential"]
    start: int


@dataclass(slots=True)
class AddonIdConfig:
    fixed: int = 0


@dataclass(slots=True)
class IdGenerationConfig:
    addon: AddonIdConfig = field(default_factory=AddonIdConfig)
    assay: SequentialIdConfig | None = None
    analyte: SequentialIdConfig | None = None
    analyte_unit: SequentialIdConfig | None = None


@dataclass(slots=True)
class MethodProtocolMapping:
    id: str
    version: str


@dataclass(slots=True)
class MethodAnalytesXmlMapping:
    method_id: str
    method_version: str


@dataclass(slots=True)
class MethodMappingConfig:
    protocol: MethodProtocolMapping
    analytes_xml: MethodAnalytesXmlMapping


@dataclass(slots=True)
class AssayProtocolMapping:
    type: str
    display_name: str | None = None


@dataclass(slots=True)
class AssayAnalytesXmlMapping:
    id: str
    name: str
    addon_ref: str


@dataclass(slots=True)
class CrossFileMatchConfig:
    mode: MatchMode = "exact"
    alias_map: dict[str, str] | None = None
    protocol_field: str | None = None
    analytes_xml_field: str | None = None


@dataclass(slots=True)
class AssayMappingConfig:
    internal_identity: str
    protocol: AssayProtocolMapping
    analytes_xml: AssayAnalytesXmlMapping
    cross_file_match: CrossFileMatchConfig = field(default_factory=CrossFileMatchConfig)


@dataclass(slots=True)
class AnalyteAnalytesXmlMapping:
    id: str
    name: str
    assay_ref: str
    assay_information_type: str | None = None


@dataclass(slots=True)
class AnalyteMappingConfig:
    internal_identity: str
    analytes_xml: AnalyteAnalytesXmlMapping


@dataclass(slots=True)
class UnitAnalytesXmlMapping:
    id: str
    name: str
    analyte_ref: str


@dataclass(slots=True)
class UnitMappingConfig:
    analytes_xml: UnitAnalytesXmlMapping


@dataclass(slots=True)
class FragmentDefaultsConfig:
    method_information: dict[str, Any] = field(default_factory=dict)
    assay_information: dict[str, Any] = field(default_factory=dict)
    loading_workflow_steps: list[Any] = field(default_factory=list)
    processing_workflow_steps: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class ExportPackagingConfig:
    include_protocol_file: bool = True
    include_analytes_xml: bool = True


@dataclass(slots=True)
class AliasMapsConfig:
    assays: dict[str, str] = field(default_factory=dict)
    analytes: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class WorkbookParsingRulesConfig:
    strict_headers: bool = True
    trim_whitespace: bool = True
    normalize_unicode: bool = False


@dataclass(slots=True)
class MappingConfigModel:
    version: Literal[1]
    ids: IdGenerationConfig
    method_mapping: MethodMappingConfig
    assay_mapping: AssayMappingConfig
    analyte_mapping: AnalyteMappingConfig
    unit_mapping: UnitMappingConfig
    protocol_defaults: FragmentDefaultsConfig = field(default_factory=FragmentDefaultsConfig)
    export_packaging: ExportPackagingConfig = field(default_factory=ExportPackagingConfig)
    alias_maps: AliasMapsConfig = field(default_factory=AliasMapsConfig)
    workbook_parsing_rules: WorkbookParsingRulesConfig = field(default_factory=WorkbookParsingRulesConfig)

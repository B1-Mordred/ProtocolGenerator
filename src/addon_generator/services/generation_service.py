from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from addon_generator.domain.issues import ValidationIssue
from addon_generator.domain.models import AddonModel
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.generators.protocol_json_generator import generate_protocol_json
from addon_generator.importers import ExcelImporter, XmlImporter, map_gui_payload_to_bundle
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.input_merge_service import InputMergeService
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain
from addon_generator.validation.dto_validator import validate_dto_bundle
from addon_generator.validation.protocol_schema_validator import validate_protocol_schema


@dataclass(slots=True)
class GenerationResult:
    addon_model: AddonModel
    protocol_json: dict[str, Any]
    analytes_xml_string: str
    issues: list[ValidationIssue]
    warnings: list[ValidationIssue]
    resolved_mapping_snapshot: dict[str, Any]
    merge_report: dict[str, Any]
    unresolved_required_fields: list[str]
    conflicting_required_fields: list[str]


@dataclass(slots=True, frozen=True)
class PackageBuildResult:
    package_root: Path
    package_name: str
    artifacts: dict[str, Path]


class PackageCollisionError(FileExistsError):
    """Raised when a package target exists and collision policy forbids replacement."""


class GenerationService:
    def __init__(self, mapping_path: str | Path = "config/mapping.v1.yaml"):
        self.mapping = load_mapping_config(mapping_path)
        self.resolver = LinkResolver(self.mapping)
        self.merge_service = InputMergeService()
        self.builder = CanonicalModelBuilder()

    def import_from_excel(self, path: str) -> AddonModel:
        bundle = ExcelImporter().import_workbook_bundle(path)
        merged, _ = self.merge_service.merge([bundle])
        return self.builder.build(merged)

    def import_from_gui_payload(self, payload: dict[str, Any]) -> AddonModel:
        bundle = map_gui_payload_to_bundle(payload)
        merged, _ = self.merge_service.merge([bundle])
        return self.builder.build(merged)

    def import_from_xml(self, path: str) -> AddonModel:
        bundle = XmlImporter().import_xml_bundle(path)
        merged, _ = self.merge_service.merge([bundle])
        return self.builder.build(merged)

    def validate_domain(self, addon: AddonModel):
        return validate_domain(addon).issues

    def generate_analytes_xml(self, addon: AddonModel, xsd_path: str | Path = "AddOn.xsd") -> str:
        self.resolver.assign_ids(addon)
        return generate_analytes_addon_xml(addon, xsd_path=xsd_path).xml_content

    def generate_protocol_json(self, addon: AddonModel, protocol_fragments: dict[str, Any] | None = None):
        self.resolver.assign_ids(addon)
        return generate_protocol_json(addon, self.resolver, protocol_fragments)

    def generate_all(self, addon: AddonModel, *, dto_bundle: InputDTOBundle | None = None, xsd_path: str | Path = "AddOn.xsd", protocol_schema_path: str | Path = "protocol.schema.json") -> GenerationResult:
        self.resolver.assign_ids(addon)
        issues = list(validate_domain(addon).issues.issues)
        issues.extend(validate_dto_bundle(dto_bundle or self._dto_bundle_from_addon(addon)).issues.issues)
        issues.extend(self.resolver.validate_cross_file_linkage(addon))

        xml_result = generate_analytes_addon_xml(addon, xsd_path=xsd_path)
        issues.extend(xml_result.issues.issues)

        protocol_result = self.generate_protocol_json(addon)
        protocol_json = protocol_result.payload
        method_info = protocol_json.get("MethodInformation", {}) if isinstance(protocol_json.get("MethodInformation"), dict) else {}
        if not str(method_info.get("Id") or "").strip() or not str(method_info.get("Version") or "").strip():
            issues.append(
                ValidationIssue(
                    code="missing-required-method-identity-after-merge",
                    message="MethodInformation.Id and MethodInformation.Version are required after merge resolution",
                    path="MethodInformation",
                    entity_keys=((addon.method.key,) if addon.method else ()),
                    source_location="ProtocolFile.json/MethodInformation",
                )
            )
        protocol_schema_result = validate_protocol_schema(protocol_json, schema_path=protocol_schema_path)
        issues.extend(protocol_schema_result.issues.issues)

        cross_file = validate_cross_file_consistency(protocol_json, ET.fromstring(xml_result.xml_content))
        issues.extend(cross_file.issues.issues)

        warnings = [i for i in issues if i.severity.value == "warning"]
        errors = [i for i in issues if i.severity.value == "error"]
        return GenerationResult(
            addon_model=addon,
            protocol_json=protocol_json,
            analytes_xml_string=xml_result.xml_content,
            issues=errors,
            warnings=warnings,
            resolved_mapping_snapshot=self.mapping.raw,
            merge_report=protocol_result.merge_report,
            unresolved_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("unresolved", [])),
            conflicting_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("conflicting", [])),
        )

    def _dto_bundle_from_addon(self, addon: AddonModel) -> InputDTOBundle:
        from addon_generator.input_models.dtos import AnalyteInputDTO, AssayInputDTO, DilutionSchemeInputDTO, SamplePrepStepInputDTO

        source_metadata = addon.source_metadata if isinstance(addon.source_metadata, dict) else {}
        sample_prep = [SamplePrepStepInputDTO(**item) for item in source_metadata.get("sample_prep_steps", []) if isinstance(item, dict)]
        dilutions = [DilutionSchemeInputDTO(**item) for item in source_metadata.get("dilution_schemes", []) if isinstance(item, dict)]
        assays = [AssayInputDTO(key=item.key, protocol_type=item.protocol_type, protocol_display_name=item.protocol_display_name, xml_name=item.xml_name, aliases=list(item.aliases), metadata=dict(item.metadata)) for item in addon.assays]
        analytes = [AnalyteInputDTO(key=item.key, name=item.name, assay_key=item.assay_key, assay_information_type=item.assay_information_type, metadata=dict(item.metadata)) for item in addon.analytes]
        return InputDTOBundle(
            source_type="default",
            source_name="addon",
            assays=assays,
            analytes=analytes,
            sample_prep_steps=sample_prep,
            dilution_schemes=dilutions,
            hidden_vocab={k: list(v) for k, v in source_metadata.get("hidden_vocab", {}).items()} if isinstance(source_metadata.get("hidden_vocab", {}), dict) else {},
            provenance=source_metadata.get("provenance", {}) if isinstance(source_metadata.get("provenance", {}), dict) else {},
        )

    def build_package(
        self,
        addon: AddonModel,
        destination_root: str | Path,
        *,
        overwrite: bool = False,
        collision_policy: str = "error",
        include_metadata: bool = True,
        xsd_path: str | Path = "AddOn.xsd",
        protocol_schema_path: str | Path = "protocol.schema.json",
    ) -> PackageBuildResult:
        result = self.generate_all(addon, xsd_path=xsd_path, protocol_schema_path=protocol_schema_path)
        package_name = self._package_name_for(addon)
        destination_root_path = Path(destination_root)
        destination_root_path.mkdir(parents=True, exist_ok=True)
        final_root = self._resolve_package_path(destination_root_path / package_name, overwrite=overwrite, collision_policy=collision_policy)

        temp_dir = Path(tempfile.mkdtemp(prefix=f".{package_name}.", dir=destination_root_path))
        temp_package_root = temp_dir / final_root.name
        temp_package_root.mkdir(parents=True, exist_ok=True)

        artifacts: dict[str, Path] = {}
        protocol_path = temp_package_root / "ProtocolFile.json"
        protocol_path.write_text(json.dumps(result.protocol_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts["ProtocolFile.json"] = protocol_path

        analytes_path = temp_package_root / "Analytes.xml"
        analytes_path.write_text(result.analytes_xml_string, encoding="utf-8")
        artifacts["Analytes.xml"] = analytes_path

        if include_metadata:
            metadata_path = temp_package_root / "package-metadata.json"
            metadata_payload = {
                "package_name": final_root.name,
                "method_id": addon.method.method_id if addon.method else "",
                "method_version": addon.method.method_version if addon.method else "",
                "artifacts": ["Analytes.xml", "ProtocolFile.json", "package-metadata.json"],
            }
            metadata_path.write_text(json.dumps(metadata_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            artifacts["package-metadata.json"] = metadata_path

        if final_root.exists():
            shutil.rmtree(final_root)
        temp_package_root.replace(final_root)
        shutil.rmtree(temp_dir, ignore_errors=True)

        return PackageBuildResult(package_root=final_root, package_name=final_root.name, artifacts={name: final_root / path.name for name, path in artifacts.items()})

    def _package_name_for(self, addon: AddonModel) -> str:
        method_id = addon.method.method_id if addon.method else "unknown-method"
        method_version = addon.method.method_version if addon.method else "0"
        raw_name = f"{method_id}-{method_version}"
        return re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)

    def _resolve_package_path(self, base_path: Path, *, overwrite: bool, collision_policy: str) -> Path:
        if collision_policy not in {"error", "increment"}:
            raise ValueError("collision_policy must be one of: error, increment")
        if not base_path.exists():
            return base_path
        if overwrite:
            return base_path
        if collision_policy == "error":
            raise PackageCollisionError(f"Package destination already exists: {base_path}")

        counter = 2
        while True:
            candidate = base_path.with_name(f"{base_path.name}-{counter}")
            if not candidate.exists():
                return candidate
            counter += 1


def fragments_from_protocol_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return payload

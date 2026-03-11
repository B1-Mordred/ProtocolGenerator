from __future__ import annotations

from contextlib import contextmanager
import copy
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from addon_generator.domain.issues import ValidationIssue
from addon_generator.__about__ import about_payload
from addon_generator.domain.models import AddonModel
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.generators.analytes_xml_generator import generate_analytes_addon_xml
from addon_generator.generators.protocol_json_generator import generate_protocol_json
from addon_generator.importers import ExcelImporter, XmlImporter, map_gui_payload_to_bundle
from addon_generator.mapping.config_loader import load_mapping_config
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.default_derivation_service import DefaultDerivationService
from addon_generator.services.input_merge_service import InputMergeService
from addon_generator.ui.services.field_mapping_execution import apply_field_mappings
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency
from addon_generator.validation.domain_validator import validate_domain
from addon_generator.validation.dto_validator import validate_dto_bundle
from addon_generator.validation.protocol_schema_validator import validate_protocol_schema
from addon_generator.validation.xsd_validator import validate_xml_against_xsd


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
    field_mapping_report: dict[str, Any]


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
        self.derivation_service = DefaultDerivationService()

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
        derived_overrides = self.derivation_service.derive_protocol_defaults(addon)
        with self._temporary_mapping_overrides(derived_overrides):
            self.resolver.assign_ids(addon)
            return generate_protocol_json(addon, self.resolver, protocol_fragments)

    def generate_all(
        self,
        addon: AddonModel,
        *,
        dto_bundle: InputDTOBundle | None = None,
        field_mapping_settings: dict[str, Any] | None = None,
        mapping_overrides: dict[str, Any] | None = None,
        xsd_path: str | Path = "AddOn.xsd",
        protocol_schema_path: str | Path = "protocol.schema.json",
    ) -> GenerationResult:
        derived_overrides = self.derivation_service.derive_protocol_defaults(addon)
        merged_overrides = copy.deepcopy(derived_overrides)
        if mapping_overrides:
            self._deep_merge(merged_overrides, mapping_overrides)

        with self._temporary_mapping_overrides(merged_overrides):
            self.resolver.assign_ids(addon)
            staged_issues: list[tuple[str, ValidationIssue]] = []

            # Phase 1: structural/domain validation.
            staged_issues.extend(("domain", issue) for issue in validate_domain(addon).issues.issues)
            staged_issues.extend(("domain", issue) for issue in validate_dto_bundle(dto_bundle or self._dto_bundle_from_addon(addon)).issues.issues)

            # Phase 2: unit/linkage validation.
            staged_issues.extend(("linkage", issue) for issue in self.resolver.validate_cross_file_linkage(addon))

            xml_result = generate_analytes_addon_xml(addon, xsd_path=xsd_path)
            protocol_result = self.generate_protocol_json(addon)
            mapping_result = apply_field_mappings(
                protocol_json=protocol_result.payload,
                analytes_xml=xml_result.xml_content,
                dto_bundle=dto_bundle,
                field_mapping_settings=field_mapping_settings,
            )
            protocol_json = mapping_result.protocol_json
            analytes_xml = mapping_result.analytes_xml
            # Phase 3: projection/schema/cross-file validation.
            mapped_xml_validation = validate_xml_against_xsd(analytes_xml, xsd_path)
            staged_issues.extend(("projection", issue) for issue in mapped_xml_validation.issues.issues)
            for warning in mapping_result.report.get("warnings", []):
                staged_issues.append(
                    (
                        "projection",
                        ValidationIssue(
                            code="field-mapping-warning",
                            message=str(warning),
                            path="field_mapping",
                            source_location="field_mapping",
                            severity="warning",
                        ),
                    )
                )
            method_info = protocol_json.get("MethodInformation", {}) if isinstance(protocol_json.get("MethodInformation"), dict) else {}
            if not str(method_info.get("Id") or "").strip() or not str(method_info.get("Version") or "").strip():
                staged_issues.append(
                    (
                        "projection",
                        ValidationIssue(
                            code="missing-required-method-identity-after-merge",
                            message="MethodInformation.Id and MethodInformation.Version are required after merge resolution",
                            path="MethodInformation",
                            entity_keys=((addon.method.key,) if addon.method else ()),
                            source_location="ProtocolFile.json/MethodInformation",
                        ),
                    )
                )
            cross_file = validate_cross_file_consistency(protocol_json, ET.fromstring(analytes_xml))
            staged_issues.extend(("projection", issue) for issue in cross_file.issues.issues)

            protocol_schema_result = validate_protocol_schema(protocol_json, schema_path=protocol_schema_path)
            staged_issues.extend(("projection", issue) for issue in protocol_schema_result.issues.issues)

            sorted_issues = self._sort_issues(staged_issues)

            warnings = [i for i in sorted_issues if i.severity.value == "warning"]
            errors = [i for i in sorted_issues if i.severity.value == "error"]
            return GenerationResult(
                addon_model=addon,
                protocol_json=protocol_json,
                analytes_xml_string=analytes_xml,
                issues=errors,
                warnings=warnings,
                resolved_mapping_snapshot=copy.deepcopy(self.mapping.raw),
                merge_report=protocol_result.merge_report,
                unresolved_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("unresolved", [])),
                conflicting_required_fields=list(protocol_result.merge_report.get("required_fields", {}).get("conflicting", [])),
                field_mapping_report=mapping_result.report,
            )

    def _sort_issues(self, staged_issues: list[tuple[str, ValidationIssue]]) -> list[ValidationIssue]:
        severity_priority = {"error": 0, "warning": 1, "info": 2}
        phase_priority = {"domain": 0, "linkage": 1, "projection": 2}

        def _issue_key(item: tuple[int, tuple[str, ValidationIssue]]) -> tuple[Any, ...]:
            index, (phase, issue) = item
            return (
                severity_priority.get(issue.severity.value, 99),
                phase_priority.get(phase, 99),
                index,
            )

        ordered = sorted(enumerate(staged_issues), key=_issue_key)
        return [issue for _, (_, issue) in ordered]

    def _dto_bundle_from_addon(self, addon: AddonModel) -> InputDTOBundle:
        from addon_generator.input_models.dtos import AnalyteInputDTO, AssayInputDTO, DilutionSchemeInputDTO, SamplePrepStepInputDTO

        source_metadata = addon.source_metadata if isinstance(addon.source_metadata, dict) else {}
        sample_prep_payload = source_metadata.get("sample_prep_steps")
        dilution_payload = source_metadata.get("dilution_schemes")
        hidden_vocab_payload = source_metadata.get("hidden_vocab")
        provenance_payload = source_metadata.get("provenance")

        sample_prep = [SamplePrepStepInputDTO(**item) for item in (sample_prep_payload or []) if isinstance(item, dict)]
        dilutions = [DilutionSchemeInputDTO(**item) for item in (dilution_payload or []) if isinstance(item, dict)]
        hidden_vocab = {k: list(v) for k, v in hidden_vocab_payload.items()} if isinstance(hidden_vocab_payload, dict) else {}
        provenance = provenance_payload if isinstance(provenance_payload, dict) else {}

        assays = [AssayInputDTO(key=item.key, protocol_type=item.protocol_type, protocol_display_name=item.protocol_display_name, xml_name=item.xml_name, aliases=list(item.aliases), metadata=dict(item.metadata)) for item in addon.assays]
        analytes = [AnalyteInputDTO(key=item.key, name=item.name, assay_key=item.assay_key, assay_information_type=item.assay_information_type, metadata=dict(item.metadata)) for item in addon.analytes]
        return InputDTOBundle(
            source_type="default",
            source_name="addon",
            assays=assays,
            analytes=analytes,
            sample_prep_steps=sample_prep,
            dilution_schemes=dilutions,
            hidden_vocab=hidden_vocab,
            provenance=provenance,
        )

    def build_package(
        self,
        addon: AddonModel,
        destination_root: str | Path,
        *,
        overwrite: bool = False,
        collision_policy: str = "error",
        include_metadata: bool = True,
        field_mapping_settings: dict[str, Any] | None = None,
        mapping_overrides: dict[str, Any] | None = None,
        xsd_path: str | Path = "AddOn.xsd",
        protocol_schema_path: str | Path = "protocol.schema.json",
    ) -> PackageBuildResult:
        result = self.generate_all(
            addon,
            field_mapping_settings=field_mapping_settings,
            mapping_overrides=mapping_overrides,
            xsd_path=xsd_path,
            protocol_schema_path=protocol_schema_path,
        )
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
                "app": about_payload(),
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

    @contextmanager
    def _temporary_mapping_overrides(self, overrides: dict[str, Any] | None):
        if not overrides:
            yield
            return

        original_raw = copy.deepcopy(self.mapping.raw)
        merged = copy.deepcopy(original_raw)
        self._deep_merge(merged, overrides)

        from addon_generator.mapping.config_loader import validate_mapping_config

        validated = validate_mapping_config(merged)
        self.mapping.raw.clear()
        self.mapping.raw.update(validated.raw)
        try:
            yield
        finally:
            self.mapping.raw.clear()
            self.mapping.raw.update(original_raw)

    def _deep_merge(self, destination: dict[str, Any], patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(destination.get(key), dict):
                self._deep_merge(destination[key], value)
                continue
            destination[key] = copy.deepcopy(value)


def fragments_from_protocol_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return payload

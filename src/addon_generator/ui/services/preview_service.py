from __future__ import annotations

import copy
import json
from datetime import datetime

from addon_generator.config.rule_pack_loader import mapping_path_for_rule_pack
from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService


class PreviewService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()

    def _service_for_settings(self, export_settings: dict[str, object] | None) -> GenerationService:
        selected_pack = str((export_settings or {}).get("selected_rule_pack") or "")
        return GenerationService(mapping_path=mapping_path_for_rule_pack(selected_pack or None))

    def generate(
        self,
        merged_bundle: InputDTOBundle,
        *,
        export_settings: dict[str, object] | None = None,
    ) -> tuple[str, str, dict[str, str | int | bool], dict[str, str] | None]:
        addon = None
        service = self._service_for_settings(export_settings)
        try:
            addon = self._builder.build(merged_bundle)
        except Exception:
            try:
                addon = self._build_preview_addon_from_bundle(merged_bundle)
                analytes_xml = self._fallback_analytes_xml(service, addon)
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                return "", "", {}, {
                    "code": "preview-generation-failed",
                    "message": f"Preview generation failed: {exc}",
                }

            fallback_summary = self._build_summary(addon=addon, validation_ok=False)
            return "", analytes_xml, fallback_summary, None

        try:
            result = service.generate_all(
                addon,
                dto_bundle=merged_bundle,
                field_mapping_settings=(export_settings or {}).get("field_mapping"),
                mapping_overrides=(export_settings or {}).get("mapping_overrides"),
            )
        except Exception:
            try:
                analytes_xml = self._fallback_analytes_xml(service, addon)
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                error = {
                    "code": "preview-generation-failed",
                    "message": f"Preview generation failed: {exc}",
                }
                return "", "", {}, error

            fallback_summary = self._build_summary(addon=addon, validation_ok=False)
            return "", analytes_xml, fallback_summary, None

        validation_ok = not bool(result.issues)
        summary = self._build_summary(addon=addon, validation_ok=validation_ok)
        return json.dumps(result.protocol_json, indent=2, sort_keys=True), result.analytes_xml_string, summary, None

    def _fallback_analytes_xml(self, service: GenerationService, addon: object) -> str:
        try:
            return service.generate_analytes_xml(addon)
        except ValueError as exc:
            if "AddonModel.method is required" not in str(exc):
                raise
        fallback_addon = copy.deepcopy(addon)
        if getattr(fallback_addon, "method", None) is None:
            fallback_addon.method = MethodModel(key="method:preview-fallback", method_id="", method_version="")
        return service.generate_analytes_xml(fallback_addon)

    def _build_preview_addon_from_bundle(self, bundle: InputDTOBundle) -> AddonModel:
        method = bundle.method
        method_model = MethodModel(
            key=str(getattr(method, "key", "") or "method:preview-fallback").strip(),
            method_id=str(getattr(method, "method_id", "") or "").strip(),
            method_version=str(getattr(method, "method_version", "") or "").strip(),
        )

        assays: list[AssayModel] = []
        for idx, item in enumerate(bundle.assays, start=1):
            assay_key = str(getattr(item, "key", "") or f"assay:preview:{idx}").strip()
            assays.append(
                AssayModel(
                    key=assay_key,
                    protocol_type=str(getattr(item, "protocol_type", "") or "").strip() or None,
                    protocol_display_name=str(getattr(item, "protocol_display_name", "") or "").strip() or None,
                    xml_name=str(getattr(item, "xml_name", "") or "").strip() or None,
                    aliases=list(getattr(item, "aliases", []) or []),
                    metadata=dict(getattr(item, "metadata", {}) or {}),
                )
            )

        analytes: list[AnalyteModel] = []
        for idx, item in enumerate(bundle.analytes, start=1):
            analyte_key = str(getattr(item, "key", "") or f"analyte:preview:{idx}").strip()
            analyte_name = str(getattr(item, "name", "") or f"Analyte {idx}").strip()
            assay_key = str(getattr(item, "assay_key", "") or "assay:preview:unmapped").strip()
            analytes.append(
                AnalyteModel(
                    key=analyte_key,
                    name=analyte_name,
                    assay_key=assay_key,
                    assay_information_type=str(getattr(item, "assay_information_type", "") or "").strip() or None,
                    metadata=dict(getattr(item, "metadata", {}) or {}),
                )
            )

        units: list[AnalyteUnitModel] = []
        for idx, item in enumerate(bundle.units, start=1):
            unit_key = str(getattr(item, "key", "") or f"unit:preview:{idx}").strip()
            unit_name = str(getattr(item, "name", "") or f"Unit {idx}").strip()
            analyte_key = str(getattr(item, "analyte_key", "") or "analyte:preview:1").strip()
            units.append(
                AnalyteUnitModel(
                    key=unit_key,
                    name=unit_name,
                    analyte_key=analyte_key,
                    metadata=dict(getattr(item, "metadata", {}) or {}),
                )
            )

        return AddonModel(
            addon_id=0,
            method=method_model,
            assays=assays,
            analytes=analytes,
            units=units,
            protocol_context=ProtocolContextModel(
                method_information_overrides=dict(bundle.method_information_overrides),
                assay_fragments=list(bundle.assay_fragments),
                loading_fragments=list(bundle.loading_fragments),
                processing_fragments=list(bundle.processing_fragments),
            ),
        )

    def _build_summary(self, *, addon: object, validation_ok: bool) -> dict[str, str | int | bool]:
        timestamp = datetime.now().isoformat(timespec="seconds")
        method = getattr(addon, "method", None)
        sample_prep_steps = getattr(addon, "sample_prep_steps", None)
        if sample_prep_steps is None:
            sample_prep_steps = (getattr(addon, "source_metadata", {}) or {}).get("sample_prep_steps", [])
        dilution_schemes = getattr(addon, "dilution_schemes", None)
        if dilution_schemes is None:
            dilution_schemes = (getattr(addon, "source_metadata", {}) or {}).get("dilution_schemes", [])
        return {
            "method_id": method.method_id if method else "",
            "method_version": method.method_version if method else "",
            "assay_count": len(getattr(addon, "assays", []) or []),
            "analyte_count": len(getattr(addon, "analytes", []) or []),
            "sample_prep_count": len(sample_prep_steps or []),
            "dilution_count": len(dilution_schemes or []),
            "validation_status": "valid" if validation_ok else "invalid",
            "preview_timestamp": timestamp,
            "export_readiness": validation_ok,
        }

from __future__ import annotations

import copy
import json
from datetime import datetime

from addon_generator.config.rule_pack_loader import mapping_path_for_rule_pack
from addon_generator.domain.models import MethodModel
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
            result = service.generate_all(
                addon,
                dto_bundle=merged_bundle,
                field_mapping_settings=(export_settings or {}).get("field_mapping"),
                mapping_overrides=(export_settings or {}).get("mapping_overrides"),
            )
        except Exception:
            if addon is None:
                return "", "", {}, {
                    "code": "preview-generation-failed",
                    "message": "Preview generation failed: unable to build addon model",
                }
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

    def _build_summary(self, *, addon: object, validation_ok: bool) -> dict[str, str | int | bool]:
        timestamp = datetime.now().isoformat(timespec="seconds")
        return {
            "method_id": addon.method.method_id if addon.method else "",
            "method_version": addon.method.method_version if addon.method else "",
            "assay_count": len(addon.assays),
            "analyte_count": len(addon.analytes),
            "sample_prep_count": len(addon.sample_prep_steps),
            "dilution_count": len(addon.dilution_schemes),
            "validation_status": "valid" if validation_ok else "invalid",
            "preview_timestamp": timestamp,
            "export_readiness": validation_ok,
        }

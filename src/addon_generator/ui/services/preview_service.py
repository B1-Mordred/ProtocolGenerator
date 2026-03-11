from __future__ import annotations

import json
from datetime import datetime

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService


class PreviewService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def generate(
        self,
        merged_bundle: InputDTOBundle,
        *,
        export_settings: dict[str, object] | None = None,
    ) -> tuple[str, str, dict[str, str | int | bool], dict[str, str] | None]:
        try:
            addon = self._builder.build(merged_bundle)
            result = self._service.generate_all(
                addon,
                dto_bundle=merged_bundle,
                field_mapping_settings=(export_settings or {}).get("field_mapping"),
                mapping_overrides=(export_settings or {}).get("mapping_overrides"),
            )
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            error = {
                "code": "preview-generation-failed",
                "message": f"Preview generation failed: {exc}",
            }
            return "", "", {}, error

        timestamp = datetime.now().isoformat(timespec="seconds")
        validation_ok = not bool(result.issues)
        summary = {
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
        return json.dumps(result.protocol_json, indent=2, sort_keys=True), result.analytes_xml_string, summary, None

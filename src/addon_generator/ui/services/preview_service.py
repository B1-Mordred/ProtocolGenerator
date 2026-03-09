from __future__ import annotations

import json

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService


class PreviewService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def generate(self, merged_bundle: InputDTOBundle) -> tuple[str, str, dict[str, str | int | bool]]:
        addon = self._builder.build(merged_bundle)
        result = self._service.generate_all(addon, dto_bundle=merged_bundle)
        summary = {
            "method_identity": f"{addon.method.method_id}:{addon.method.method_version}" if addon.method else "",
            "assay_count": len(addon.assays),
            "analyte_count": len(addon.analytes),
            "sample_prep_count": len(addon.sample_prep_steps),
            "dilution_scheme_count": len(addon.dilution_schemes),
            "validation_state": not bool(result.issues),
            "export_readiness": not bool(result.issues),
        }
        return json.dumps(result.protocol_json, indent=2, sort_keys=True), result.analytes_xml_string, summary

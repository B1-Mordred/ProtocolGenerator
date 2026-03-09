from __future__ import annotations

from pathlib import Path

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService


class ExportService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def export(self, merged_bundle: InputDTOBundle, *, destination_folder: str, overwrite: bool = False) -> dict[str, str]:
        addon = self._builder.build(merged_bundle)
        validation = self._service.generate_all(addon, dto_bundle=merged_bundle)
        if validation.issues:
            raise ValueError("Export blocked due to validation errors")
        package = self._service.build_package(addon, destination_root=Path(destination_folder), overwrite=overwrite)
        return {name: str(path) for name, path in package.artifacts.items()}

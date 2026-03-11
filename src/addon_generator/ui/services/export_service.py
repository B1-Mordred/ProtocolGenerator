from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService


@dataclass(slots=True)
class ExportResult:
    status: str
    written_paths: list[str] = field(default_factory=list)
    destination: str = ""
    failure_reason: str | None = None
    cleanup_note: str | None = None

    @property
    def success(self) -> bool:
        return self.status == "success"


class ExportService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def export(
        self,
        merged_bundle: InputDTOBundle,
        *,
        destination_folder: str,
        overwrite: bool = False,
        export_settings: dict[str, object] | None = None,
    ) -> ExportResult:
        destination = str(Path(destination_folder))
        field_mapping_settings = (export_settings or {}).get("field_mapping")
        addon = self._builder.build(merged_bundle)
        validation = self._service.generate_all(addon, dto_bundle=merged_bundle, field_mapping_settings=field_mapping_settings)
        if validation.issues:
            return ExportResult(
                status="failure",
                destination=destination,
                failure_reason="Export blocked due to validation errors.",
            )

        try:
            package = self._service.build_package(
                addon,
                destination_root=Path(destination_folder),
                overwrite=overwrite,
                field_mapping_settings=field_mapping_settings,
            )
        except Exception as exc:
            return ExportResult(
                status="failure",
                destination=destination,
                failure_reason=f"Export failed: {exc}",
                cleanup_note="Partial files may exist in the destination and might require manual cleanup.",
            )

        written_paths = [str(path) for path in package.artifacts.values()]
        return ExportResult(status="success", written_paths=written_paths, destination=destination)

from __future__ import annotations

from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_model_builder import CanonicalModelBuilder
from addon_generator.services.generation_service import GenerationService
from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.services.import_service import issue_from_validation_issue


class ValidationService:
    def __init__(self) -> None:
        self._builder = CanonicalModelBuilder()
        self._service = GenerationService()

    def validate(self, merged_bundle: InputDTOBundle) -> tuple[object, list[IssueViewModel]]:
        addon = self._builder.build(merged_bundle)
        result = self._service.generate_all(addon, dto_bundle=merged_bundle)
        issues = [issue_from_validation_issue(issue) for issue in result.issues + result.warnings]
        return addon, issues

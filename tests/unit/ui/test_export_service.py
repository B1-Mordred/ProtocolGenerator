from __future__ import annotations

import pytest

from addon_generator.domain.issues import ValidationIssue
from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.services.export_service import ExportService


class _ValidationResult:
    def __init__(self, issues):
        self.issues = issues


def test_export_service_blocks_when_validation_has_errors(monkeypatch, tmp_path) -> None:
    service = ExportService()
    bundle = InputDTOBundle(source_type="gui", method=MethodInputDTO(key="m", method_id="M", method_version="1"))

    monkeypatch.setattr(service._builder, "build", lambda merged_bundle: object())
    monkeypatch.setattr(
        service._service,
        "generate_all",
        lambda addon, dto_bundle=None: _ValidationResult([ValidationIssue(code="bad", message="bad", path="x")]),
    )

    with pytest.raises(ValueError, match="Export blocked"):
        service.export(bundle, destination_folder=str(tmp_path))

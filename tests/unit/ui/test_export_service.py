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

    result = service.export(bundle, destination_folder=str(tmp_path))
    assert result.status == "failure"
    assert result.failure_reason == "Export blocked due to validation errors."


def test_export_service_returns_written_paths_on_success(monkeypatch, tmp_path) -> None:
    service = ExportService()
    bundle = InputDTOBundle(source_type="gui", method=MethodInputDTO(key="m", method_id="M", method_version="1"))

    class _Package:
        artifacts = {
            "ProtocolFile.json": tmp_path / "ProtocolFile.json",
            "Analytes.xml": tmp_path / "Analytes.xml",
        }

    monkeypatch.setattr(service._builder, "build", lambda merged_bundle: object())
    monkeypatch.setattr(service._service, "generate_all", lambda addon, dto_bundle=None: _ValidationResult([]))
    monkeypatch.setattr(service._service, "build_package", lambda addon, destination_root, overwrite=False: _Package())

    result = service.export(bundle, destination_folder=str(tmp_path))
    assert result.status == "success"
    assert result.destination == str(tmp_path)
    assert str(tmp_path / "ProtocolFile.json") in result.written_paths

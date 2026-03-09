from __future__ import annotations

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.services.export_service import ExportService
from addon_generator.ui.services.import_service import ImportService
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.services.preview_service import PreviewService
from addon_generator.ui.services.validation_service import ValidationService
from addon_generator.ui.state.app_state import AppState


def test_ui_flow_import_edit_validate_preview_export(monkeypatch, tmp_path) -> None:
    app_state = AppState()

    bundle = InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m", method_id="M-100", method_version="1"))
    monkeypatch.setattr(ImportService, "load_excel", lambda self, path: (bundle, {}, []))
    monkeypatch.setattr(ValidationService, "validate", lambda self, merged: (object(), []))
    monkeypatch.setattr(PreviewService, "generate", lambda self, merged: ("{}", "<xml/>", {"export_readiness": True}))
    monkeypatch.setattr(ExportService, "export", lambda self, merged_bundle, *, destination_folder, overwrite=False: {"ProtocolFile.json": str(tmp_path / "ProtocolFile.json")})

    imported, provenance, issues = ImportService().load_excel("tests/AddOn_Input_92111_v03.xlsx")
    app_state.import_state.replace(bundles=[imported], provenance=provenance, issues=issues)

    app_state.editor_state.set_override("method.method_id", "M-101")
    merged = MergeServiceAdapter().recompute(app_state)

    _, validation_issues = ValidationService().validate(merged)
    protocol, analytes, summary = PreviewService().generate(merged)
    exported = ExportService().export(merged, destination_folder=str(tmp_path))

    assert merged.method is not None
    assert merged.method.method_id == "M-101"
    assert validation_issues == []
    assert protocol == "{}"
    assert analytes == "<xml/>"
    assert summary["export_readiness"] is True
    assert "ProtocolFile.json" in exported

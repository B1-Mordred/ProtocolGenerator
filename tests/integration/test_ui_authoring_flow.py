from __future__ import annotations

from addon_generator.input_models.dtos import DilutionSchemeInputDTO, InputDTOBundle, MethodInputDTO, SamplePrepStepInputDTO
from addon_generator.ui.models.import_review_view_model import ImportReviewFilter, ImportReviewScreenViewModel
from addon_generator.ui.models.sampleprep_view_model import SamplePrepScreenViewModel
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

def test_ui_flow_import_review_edit_and_stale_preview_lifecycle(monkeypatch) -> None:
    app_state = AppState()

    xml_bundle = InputDTOBundle(
        source_type="xml",
        method=MethodInputDTO(key="m", method_id="M-XML", method_version="1"),
        sample_prep_steps=[
            SamplePrepStepInputDTO(
                key="sp1",
                label="Mix",
                metadata={"order": "1", "source": "Tube A", "destination": "Tube B"},
            )
        ],
        dilution_schemes=[
            DilutionSchemeInputDTO(key="d1", label="Std", metadata={"buffer1_ratio": "1", "buffer2_ratio": "2", "buffer3_ratio": "3"})
        ],
        hidden_vocab={"SamplePrepAction": ["Mix", "Incubate"]},
    )
    excel_bundle = InputDTOBundle(
        source_type="excel",
        method=MethodInputDTO(key="m", method_id="M-XL", method_version="2"),
        sample_prep_steps=[
            SamplePrepStepInputDTO(
                key="sp1",
                label="Incubate",
                metadata={"order": "1", "source": "Tube A", "destination": "Tube B"},
            )
        ],
        dilution_schemes=[
            DilutionSchemeInputDTO(key="d1", label="Std", metadata={"buffer1_ratio": "1", "buffer2_ratio": "0", "buffer3_ratio": "3"})
        ],
        hidden_vocab={"SamplePrepAction": ["Mix", "Incubate"]},
    )

    monkeypatch.setattr(ValidationService, "validate", lambda self, merged: (object(), []))
    monkeypatch.setattr(PreviewService, "generate", lambda self, merged: ("{}", "<xml/>", {"export_readiness": True}))

    app_state.import_state.replace(bundles=[xml_bundle, excel_bundle], provenance={}, issues=[])
    merge = MergeServiceAdapter()
    merged = merge.recompute(app_state)
    assert merged.method is not None and merged.method.method_id == "M-XL"

    review_vm = ImportReviewScreenViewModel(app_state, merge)
    conflict_rows = review_vm.rows(ImportReviewFilter.CONFLICTS.value)
    assert any(row.path == "method.method_id" for row in conflict_rows)

    review_vm.accept_imported("method.method_id")
    assert app_state.import_state.review_resolutions["method.method_id"] == "accepted_imported"

    sample_vm = SamplePrepScreenViewModel(app_state, merge)
    step_id = sample_vm.selected_step_id
    assert step_id is not None
    sample_vm.update_field(step_id, "source", "Tube C")
    assert app_state.editor_state.sample_prep_overrides[0]["source"] == "Tube C"

    assert app_state.preview_state.stale is True
    assert app_state.validation_state.stale is True

    current = merge.recompute(app_state)
    _addon, validation_issues = ValidationService().validate(current)
    app_state.validation_state.issues = validation_issues
    app_state.validation_state.stale = False
    assert app_state.validation_state.stale is False

    protocol, analytes, summary = PreviewService().generate(current)
    app_state.preview_state.protocol_json = protocol
    app_state.preview_state.analytes_xml = analytes
    app_state.preview_state.summary = summary
    app_state.preview_state.stale = False
    assert app_state.preview_state.stale is False

    sample_vm.update_field(step_id, "destination", "Tube D")
    assert app_state.preview_state.stale is True
    assert app_state.validation_state.stale is True

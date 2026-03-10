from __future__ import annotations

from pathlib import Path

from addon_generator.input_models.dtos import DilutionSchemeInputDTO, InputDTOBundle, MethodInputDTO, SamplePrepStepInputDTO
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.ui.services.draft_service import DraftService
from addon_generator.ui.services.import_service import ImportService
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


def test_merge_service_marks_validation_and_preview_stale() -> None:
    app_state = AppState()
    app_state.import_state.bundles = [
        InputDTOBundle(
            source_type="gui",
            method=MethodInputDTO(key="m1", method_id="M-1", method_version="1"),
        )
    ]
    app_state.editor_state.set_override("method.method_id", "M-2")

    merged = MergeServiceAdapter().recompute(app_state)

    assert merged.method is not None
    assert merged.method.method_id == "M-2"
    assert app_state.validation_state.stale is True
    assert app_state.preview_state.stale is True


def test_merge_service_applies_structured_overrides_and_conflict_summary() -> None:
    app_state = AppState()
    app_state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            sample_prep_steps=[SamplePrepStepInputDTO(key="s1", label="Mix", metadata={"order": "1"})],
            dilution_schemes=[DilutionSchemeInputDTO(key="d1", label="Std", metadata={"buffer1_ratio": "1", "buffer2_ratio": "2", "buffer3_ratio": "3"})],
        ),
        InputDTOBundle(
            source_type="gui",
            method=MethodInputDTO(key="m", method_id="M", method_version="2"),
        ),
    ]
    app_state.editor_state.sample_prep_overrides = [{"order": "2", "action": "Incubate", "source": "A", "destination": "B"}]
    app_state.editor_state.dilution_overrides = [{"name": "Custom", "buffer1_ratio": "3", "buffer2_ratio": "4", "buffer3_ratio": "5"}]

    merged = MergeServiceAdapter().recompute(app_state)

    assert len(merged.sample_prep_steps) == 1
    assert merged.sample_prep_steps[0].label == "Incubate"
    assert len(merged.dilution_schemes) == 1
    assert merged.dilution_schemes[0].label == "Custom"
    assert "total" in app_state.import_state.conflict_summary


def test_draft_service_save_and_load_roundtrip(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.editor_state.manual_overrides["method.method_version"] = "2"

    service = DraftService()
    path = service.save(app_state, drafts_dir=str(tmp_path))
    restored = service.load(path)

    assert path.exists()
    assert restored["editor_state"]["manual_overrides"]["method.method_version"] == "2"


def test_draft_service_restore_roundtrip(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            method=MethodInputDTO(key="m1", method_id="MX", method_version="3"),
        )
    ]
    app_state.editor_state.selected_section_index = 4
    service = DraftService()
    path = service.save(app_state, drafts_dir=str(tmp_path))

    new_state = AppState()
    service.restore(new_state, service.load(path), source_path=str(path))

    assert new_state.import_state.bundles[0].method is not None
    assert new_state.import_state.bundles[0].method.method_id == "MX"
    assert new_state.editor_state.selected_section_index == 4
    assert new_state.draft_state.path == str(path)


def test_import_service_coerces_provenance() -> None:
    bundle = InputDTOBundle(
        source_type="excel",
        provenance={
            "method.method_id": [
                FieldProvenance(
                    source_type="excel",
                    source_file="book.xlsx",
                    source_sheet="Basics",
                    row=2,
                    column="B",
                    field_key="method.method_id",
                )
            ]
        },
    )

    provenance = ImportService._coerce_provenance(bundle)

    assert provenance["method.method_id"][0]["location"] == "book.xlsx:Basics:2:B"
    assert provenance["method.method_id"][0]["source_label"] == "Excel"
    assert provenance["method.method_id"][0]["location_text"] == "book.xlsx:Basics:2:B"

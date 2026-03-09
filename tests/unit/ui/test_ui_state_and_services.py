from __future__ import annotations

from pathlib import Path

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.ui.services.import_service import ImportService
from addon_generator.ui.services.draft_service import DraftService
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
    assert provenance["method.method_id"][0]["note"] == "method.method_id"

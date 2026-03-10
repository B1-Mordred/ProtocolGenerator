from __future__ import annotations

import json
from pathlib import Path

from addon_generator.input_models.dtos import (
    AnalyteInputDTO,
    AssayInputDTO,
    DilutionSchemeInputDTO,
    InputDTOBundle,
    MethodInputDTO,
    SamplePrepStepInputDTO,
    UnitInputDTO,
)
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.runtime.paths import RuntimePaths
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




def test_draft_service_save_uses_runtime_default_directory(monkeypatch, tmp_path: Path) -> None:
    app_state = AppState()
    runtime_paths = RuntimePaths(
        runtime_support_dir=tmp_path / "support",
        config_dir=tmp_path / "config",
        drafts_dir=tmp_path / "config" / "drafts",
        logs_dir=tmp_path / "logs",
    )
    monkeypatch.setattr("addon_generator.ui.services.draft_service.get_runtime_paths", lambda: runtime_paths)

    path = DraftService().save(app_state)

    assert path.parent == runtime_paths.drafts_dir
    assert path.exists()



def test_draft_service_save_to_user_selected_path(tmp_path: Path) -> None:
    app_state = AppState()
    target = tmp_path / "custom" / "my-draft.json"

    path = DraftService().save(app_state, draft_path=target)

    assert path == target
    assert target.exists()


def test_draft_service_save_excludes_stale_nested_payload_from_disk(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.import_state.provenance = {"source": "current-session"}
    app_state.draft_state.payload = {
        "import_state": {"provenance": {"source": "stale-session"}},
        "editor_state": {"manual_overrides": {"method.method_id": "STALE"}},
    }

    path = DraftService().save(app_state, draft_path=tmp_path / "draft.json")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["draft_state"]["payload"] == {}
    assert saved["import_state"]["provenance"] == {"source": "current-session"}
    assert saved["import_state"]["provenance"] != {"source": "stale-session"}


def test_draft_service_save_persists_top_level_import_state_as_source_of_truth(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.import_state.provenance = {"authoritative": "top-level"}
    app_state.draft_state.payload = {
        "import_state": {"provenance": {"authoritative": "old-nested"}},
    }

    path = DraftService().save(app_state, draft_path=tmp_path / "draft.json")
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["import_state"]["provenance"] == {"authoritative": "top-level"}
    assert saved["draft_state"]["payload"].get("import_state") is None
    assert app_state.draft_state.payload["import_state"]["provenance"] == {"authoritative": "top-level"}


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



def test_draft_service_restore_rebuilds_full_bundle_and_metadata(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            source_name="source.xlsx",
            method=MethodInputDTO(key="m1", method_id="M-1", method_version="1"),
            assays=[AssayInputDTO(key="a1", protocol_type="PT", protocol_display_name="Disp", xml_name="Xml", aliases=["Alias"])],
            analytes=[AnalyteInputDTO(key="an1", name="A", assay_key="a1")],
            units=[UnitInputDTO(key="u1", name="IU", analyte_key="an1")],
            sample_prep_steps=[SamplePrepStepInputDTO(key="s1", label="Mix", metadata={"order": "1"})],
            dilution_schemes=[DilutionSchemeInputDTO(key="d1", label="Std", metadata={"ratio": "1:2:3"})],
            method_information_overrides={"Custom": "X"},
            assay_fragments=[{"Assay": "A1"}],
            loading_fragments=[{"Load": "L1"}],
            processing_fragments=[{"Process": "P1"}],
            hidden_vocab={"SamplePrepAction": ["Mix"]},
            provenance={
                "method.method_id": [
                    FieldProvenance(source_type="excel", source_file="source.xlsx", source_sheet="Basics", row=2, column="B")
                ]
            },
        )
    ]
    app_state.editor_state.manual_overrides["method.method_id"] = "M-2"
    app_state.editor_state.unresolved_conflicts = {"method.method_id": [{"path": "method.method_id"}]}
    app_state.validation_state.stale = False
    app_state.preview_state.stale = False

    service = DraftService()
    path = service.save(app_state, drafts_dir=str(tmp_path))

    restored_state = AppState()
    service.restore(restored_state, service.load(path), source_path=str(path))

    bundle = restored_state.import_state.bundles[0]
    assert bundle.source_name == "source.xlsx"
    assert bundle.assays[0].key == "a1"
    assert bundle.analytes[0].assay_key == "a1"
    assert bundle.units[0].analyte_key == "an1"
    assert bundle.sample_prep_steps[0].label == "Mix"
    assert bundle.dilution_schemes[0].label == "Std"
    assert bundle.method_information_overrides["Custom"] == "X"
    assert bundle.assay_fragments[0]["Assay"] == "A1"
    assert bundle.hidden_vocab["SamplePrepAction"] == ["Mix"]
    assert bundle.provenance["method.method_id"][0].source_sheet == "Basics"
    assert restored_state.editor_state.manual_overrides["method.method_id"] == "M-2"
    assert restored_state.editor_state.unresolved_conflicts["method.method_id"][0]["path"] == "method.method_id"
    assert restored_state.preview_state.stale is False
    assert restored_state.validation_state.stale is False
    assert restored_state.draft_state.path == str(path)
    assert restored_state.draft_state.restore_metadata["source_path"] == str(path)


def test_draft_roundtrip_recompute_reproduces_preview_and_validation_state(tmp_path: Path) -> None:
    app_state = AppState()
    app_state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            method=MethodInputDTO(key="m", method_id="M-1", method_version="1"),
        ),
        InputDTOBundle(
            source_type="xml",
            method=MethodInputDTO(key="m", method_id="M-9", method_version="9"),
        ),
    ]
    app_state.editor_state.manual_overrides["method.method_id"] = "M-OVERRIDE"

    merge = MergeServiceAdapter()
    merged_before = merge.recompute(app_state)
    assert merged_before.method is not None
    assert merged_before.method.method_id == "M-OVERRIDE"

    service = DraftService()
    path = service.save(app_state, drafts_dir=str(tmp_path))

    restored_state = AppState()
    service.restore(restored_state, service.load(path), source_path=str(path))
    merged_after = merge.recompute(restored_state)

    assert merged_after.method is not None
    assert merged_after.method.method_id == "M-OVERRIDE"
    assert "method.method_id" in restored_state.editor_state.unresolved_conflicts
    assert restored_state.import_state.conflict_summary["total"] >= 1
    assert restored_state.validation_state.stale is True
    assert restored_state.preview_state.stale is True


def test_draft_service_load_combined_recovery_file_merges_manual_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "combined-recovery.json"
    path.write_text(
        json.dumps(
            {
                "draft": {
                    "draft_state": {"dirty": True, "last_saved_at": None, "path": None, "payload": {}, "restore_metadata": {}},
                    "editor_state": {
                        "manual_overrides": {},
                        "sample_prep_overrides": [],
                        "dilution_overrides": [],
                        "selected_sample_prep_step_id": None,
                        "selected_dilution_id": None,
                        "manual_edit_markers": {},
                        "effective_values": {},
                        "unresolved_conflicts": {},
                        "selected_entity": None,
                        "selected_section_index": 0,
                        "export_settings": {"admin_kit_types": ["Sample", "Reagent"]},
                    },
                    "import_state": {
                        "bundles": [],
                        "provenance": {},
                        "imported_sample_prep_dtos": [],
                        "imported_dilution_dtos": [],
                        "conflict_summary": {"total": 0, "unresolved": 0},
                        "provenance_lookup": {},
                        "issues": [],
                        "review_resolutions": {},
                    },
                    "preview_state": {
                        "stale": True,
                        "protocol_json": "",
                        "analytes_xml": "",
                        "summary": None,
                        "validation_state_snapshot": "unknown",
                        "export_readiness_snapshot": False,
                        "last_generated_at": None,
                        "generation_error": None,
                    },
                    "validation_state": {
                        "stale": True,
                        "issues": [],
                        "grouped_issues": {},
                        "severity_counts": {"error": 0, "warning": 0, "info": 0},
                        "category_counts": {},
                        "export_blocked": False,
                        "last_validated_at": None,
                    },
                },
                "manual_entry_snapshot": {
                    "method": {
                        "addon_product_name": "TDM Series A",
                        "addon_product_number": "42952",
                        "addon_series": "MassPrep®",
                        "kit_name": "TDM Series A",
                        "kit_product_number": "92711",
                        "kit_series": "MassTox®",
                    },
                    "assays": [
                        {
                            "assay_abbreviation": "",
                            "component_name": "Urine",
                            "container_type": "Sample Tube",
                            "parameter_set_name": "",
                            "parameter_set_number": "",
                            "product_number": "",
                            "type": "Sample",
                        }
                    ],
                    "analytes": [],
                    "dilutions": [{"buffer1_ratio": "100", "buffer2_ratio": "", "buffer3_ratio": "", "key": "1+2"}],
                    "sample_prep": [],
                },
            }
        ),
        encoding="utf-8",
    )

    service = DraftService()
    payload = service.load(path)
    restored_state = AppState()
    service.restore(restored_state, payload, source_path=str(path))

    bundle = restored_state.import_state.bundles[0]
    assert bundle.method is not None
    assert bundle.method.series_name == "MassTox®"
    assert bundle.assays[0].metadata["component_name"] == "Urine"
    assert bundle.dilution_schemes[0].key == "1+2"
    assert restored_state.editor_state.export_settings["admin_kit_types"] == ["Sample", "Reagent"]

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


def test_preview_service_returns_structured_summary(monkeypatch) -> None:
    from addon_generator.ui.services.preview_service import PreviewService

    class _Addon:
        def __init__(self):
            self.method = type("M", (), {"method_id": "MID", "method_version": "9"})()
            self.assays = [object(), object()]
            self.analytes = [object()]
            self.sample_prep_steps = [object()]
            self.dilution_schemes = [object(), object(), object()]

    class _Result:
        protocol_json = {"x": 1}
        analytes_xml_string = "<xml/>"
        issues = []

    svc = PreviewService()
    monkeypatch.setattr(svc._builder, "build", lambda bundle: _Addon())
    monkeypatch.setattr(svc._service, "generate_all", lambda addon, dto_bundle: _Result())

    protocol, analytes, summary, failure = svc.generate(InputDTOBundle(source_type="excel"))

    assert failure is None
    assert '"x": 1' in protocol
    assert analytes == "<xml/>"
    assert summary["method_id"] == "MID"
    assert summary["method_version"] == "9"
    assert summary["assay_count"] == 2
    assert summary["dilution_count"] == 3
    assert summary["validation_status"] == "valid"
    assert summary["export_readiness"] is True


def test_preview_service_returns_clean_failure(monkeypatch) -> None:
    from addon_generator.ui.services.preview_service import PreviewService

    svc = PreviewService()
    monkeypatch.setattr(svc._builder, "build", lambda bundle: (_ for _ in ()).throw(RuntimeError("boom")))

    protocol, analytes, summary, failure = svc.generate(InputDTOBundle(source_type="excel"))

    assert protocol == ""
    assert analytes == ""
    assert summary == {}
    assert failure is not None
    assert failure["code"] == "preview-generation-failed"
    assert "Preview generation failed" in failure["message"]

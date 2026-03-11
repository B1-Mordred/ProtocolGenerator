from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.models.import_review_view_model import ImportReviewFilter, ImportReviewScreenViewModel
from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.services.export_service import ExportResult
from addon_generator.ui.services.validation_service import ValidationSummary
from addon_generator.ui.shell import MainShell
from addon_generator.ui.state.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _ImportService:
    def __init__(self, imported_bundle: InputDTOBundle):
        self._bundle = imported_bundle

    def load_excel(self, path):
        return self._bundle, {"method.method_id": [{"source": "excel", "location": path}]}, []


class _MergeService:
    def recompute(self, app_state):
        merged = app_state.import_state.bundles[-1]
        override = app_state.editor_state.manual_overrides.get("method.method_id")
        if merged.method is not None and override:
            merged.method.method_id = override
        app_state.editor_state.effective_values = {"method": {"method_id": merged.method.method_id if merged.method else ""}}
        app_state.editor_state.unresolved_conflicts = {"method.method_id": [{"path": "method.method_id"}]}
        return merged

    def flatten_import_review_rows(self, app_state):
        return [{"path": "method.method_id", "imported": "M-IMPORTED", "effective": app_state.editor_state.manual_overrides.get("method.method_id", "M-IMPORTED")}]

    def accept_imported_value(self, app_state, path):
        app_state.import_state.review_resolutions[path] = "accepted_imported"
        app_state.editor_state.manual_overrides[path] = "M-IMPORTED"

    def keep_override_value(self, app_state, path):
        app_state.import_state.review_resolutions[path] = "kept_override"

    def revert_default_value(self, app_state, path):
        app_state.import_state.review_resolutions[path] = "reverted_default"


class _ValidationService:
    def validate(self, merged, *, export_settings=None):
        issues = [IssueViewModel(code="W-1", severity="warning", summary="Assay warning", category="Assays", entity_context="assay/A1")]
        return object(), ValidationSummary(
            issues=issues,
            grouped_issues={"Assays": issues},
            severity_counts={"error": 0, "warning": 1, "info": 0},
            category_counts={"Assays": 1},
            export_blocked=False,
        )


class _PreviewService:
    def __init__(self):
        self._run = 0

    def generate(self, merged):
        self._run += 1
        summary = {
            "validation_status": "valid",
            "export_readiness": True,
            "method_id": merged.method.method_id if merged.method else "unknown",
            "refresh_count": self._run,
        }
        return "{\"protocol\": true}", "<analytes />", summary, None


class _ExportService:
    def __init__(self):
        self.calls: list[tuple[str, bool]] = []

    def export(self, merged, *, destination_folder, overwrite=False, export_settings=None):
        self.calls.append((destination_folder, overwrite))
        protocol = Path(destination_folder) / "ProtocolFile.json"
        analytes = Path(destination_folder) / "Analytes.xml"
        return ExportResult(status="success", written_paths=[str(protocol), str(analytes)], destination=destination_folder)


class _DraftService:
    def __init__(self, draft_path: Path):
        self._draft_path = draft_path

    def save(self, app_state, drafts_dir="drafts", draft_path=None):
        chosen = Path(draft_path) if draft_path else self._draft_path
        app_state.draft_state.path = str(chosen)
        app_state.draft_state.dirty = False
        return chosen

    def load(self, path):
        return {
            "import_state": {
                "bundles": [{"source_type": "excel", "method": {"key": "m", "method_id": "M-RESTORED", "method_version": "1"}}],
                "provenance": {},
            },
            "editor_state": {
                "manual_overrides": {"method.method_id": "M-RESTORED"},
                "effective_values": {"method": {"method_id": "M-RESTORED"}},
                "unresolved_conflicts": {},
                "selected_entity": "method",
                "selected_section_index": 8,
                "sample_prep_overrides": [],
                "dilution_overrides": [],
                "export_settings": {},
            },
            "validation_state": {
                "stale": False,
                "issues": [],
                "grouped_issues": {},
                "severity_counts": {"error": 0, "warning": 0, "info": 0},
                "category_counts": {},
                "export_blocked": False,
                "last_validated_at": None,
            },
            "preview_state": {
                "stale": False,
                "protocol_json": "{\"restored\":true}",
                "analytes_xml": "<restored />",
                "summary": {"validation_status": "valid", "export_readiness": True},
                "validation_state_snapshot": "valid",
                "export_readiness_snapshot": True,
                "last_generated_at": None,
                "generation_error": None,
            },
            "draft_state": {"path": str(path), "payload": {}},
        }

    def restore(self, app_state, payload, *, source_path=None):
        app_state.editor_state.selected_section_index = payload["editor_state"]["selected_section_index"]
        app_state.editor_state.manual_overrides = payload["editor_state"]["manual_overrides"]
        app_state.draft_state.dirty = False


def test_gui_workflow_import_edit_resolve_validate_preview_export_save_restore(qapp, monkeypatch, tmp_path) -> None:
    info_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda parent, title, text: info_calls.append((title, text)) or QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *args, **kwargs: str(tmp_path)))

    import_bundle = InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m", method_id="M-IMPORTED", method_version="1"))
    export_service = _ExportService()
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(import_bundle),
        merge_service=_MergeService(),
        validation_service=_ValidationService(),
        preview_service=_PreviewService(),
        export_service=export_service,
        draft_service=_DraftService(tmp_path / "draft.json"),
    )

    shell.app_state.editor_state.export_settings["excel_path"] = "fixtures/input.xlsx"
    shell.import_excel()
    assert shell.app_state.draft_state.dirty is True

    shell.app_state.editor_state.set_override("method.method_id", "M-EDIT")
    shell._mark_dirty(reason="editor")

    review_vm = ImportReviewScreenViewModel(shell.app_state, shell.merge_service)
    conflicts = review_vm.rows(ImportReviewFilter.CONFLICTS.value)
    assert any(row.path == "method.method_id" for row in conflicts)
    review_vm.accept_imported("method.method_id")
    assert shell.app_state.import_state.review_resolutions["method.method_id"] == "accepted_imported"

    shell.run_validation()
    assert shell.validation_view.status_message.text() == "Validation current: export is allowed."

    issue_group = shell.validation_view.issues.tree.topLevelItem(0)
    shell.validation_view.issues.tree.setCurrentItem(issue_group.child(0))
    assert shell.sidebar.currentRow() == 1

    shell.run_preview()
    shell._mark_dirty(reason="editor")
    shell._refresh_status()
    assert shell.preview_view.stale_banner.text() == "Preview status: stale"
    shell.run_preview()
    summary = json.loads(shell.preview_view.tabs.summary.toPlainText())
    assert summary["refresh_count"] == 2

    shell.choose_export_destination()
    shell.run_export()
    assert export_service.calls
    assert shell.export_view.result_status.text() == "Export succeeded"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(tmp_path / "draft.json"), "")))
    shell.save_draft()
    assert shell.app_state.draft_state.dirty is False

    shell.app_state.editor_state.export_settings["draft_path"] = str(tmp_path / "draft.json")
    shell.app_state.draft_state.dirty = True
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (str(tmp_path / "draft.json"), "")))
    shell.restore_draft()
    assert shell.app_state.draft_state.dirty is False
    assert shell.stack.currentIndex() == 8
    assert any(title == "Status Saved" for title, _ in info_calls)
    assert any(title == "Draft Recovered" for title, _ in info_calls)

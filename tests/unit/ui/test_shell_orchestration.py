from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from PySide6.QtWidgets import QMessageBox

from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.services.export_service import ExportResult
from addon_generator.ui.shell import MainShell
from addon_generator.ui.services.validation_service import ValidationSummary
from addon_generator.ui.state.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def messagebox_spy(monkeypatch):
    calls = {"info": [], "question": []}

    def _info(parent, title, text):
        calls["info"].append((title, text))
        return QMessageBox.StandardButton.Ok

    def _question(parent, title, text, buttons, default):
        calls["question"].append((title, text))
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "information", staticmethod(_info))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(_question))
    return calls


class _ImportService:
    def load_excel(self, path):
        bundle = InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m", method_id="M-1", method_version="1"))
        return bundle, {}, []

    def load_xml(self, path):
        bundle = InputDTOBundle(source_type="xml", method=MethodInputDTO(key="m", method_id="M-2", method_version="1"))
        return bundle, {}, []


class _MergeService:
    def recompute(self, app_state):
        return app_state.import_state.bundles[0]


class _ValidationService:
    def __init__(self, issues):
        self._issues = issues

    def validate(self, merged):
        grouped = {}
        category_counts = {}
        severity_counts = {"error": 0, "warning": 0, "info": 0}
        for issue in self._issues:
            grouped.setdefault(issue.category, []).append(issue)
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        return object(), ValidationSummary(
            issues=self._issues,
            grouped_issues=grouped,
            severity_counts=severity_counts,
            category_counts=category_counts,
            export_blocked=severity_counts.get("error", 0) > 0,
        )


class _PreviewService:
    def generate(self, merged):
        return "{}", "<xml/>", {"export_readiness": True, "validation_status": "valid"}, None


class _ExportService:
    def __init__(self, result: ExportResult | None = None):
        self.called = False
        self.result = result or ExportResult(status="success", written_paths=[])

    def export(self, merged, *, destination_folder, overwrite=False):
        self.called = True
        self.result.destination = destination_folder
        return self.result


class _DraftService:
    def __init__(self):
        self.saved = False

    def save(self, app_state, drafts_dir="drafts"):
        self.saved = True

    def load(self, path):
        return {
            "import_state": {"bundles": [{"source_type": "excel", "method": {"key": "m", "method_id": "RM", "method_version": "1"}}], "provenance": {}},
            "editor_state": {"manual_overrides": {}, "effective_values": {}, "unresolved_conflicts": {}, "selected_entity": None, "selected_section_index": 8, "export_settings": {}},
            "validation_state": {"stale": True, "issues": []},
            "preview_state": {"stale": True, "protocol_json": "", "analytes_xml": "", "summary": None, "validation_state_snapshot": "unknown", "export_readiness_snapshot": False, "last_generated_at": None, "generation_error": None},
            "draft_state": {"path": path, "payload": {}},
        }

    def restore(self, app_state, payload, *, source_path=None):
        app_state.editor_state.selected_section_index = payload["editor_state"]["selected_section_index"]
        app_state.validation_state.stale = payload["validation_state"]["stale"]
        app_state.preview_state.stale = payload["preview_state"]["stale"]
        app_state.draft_state.dirty = False


def test_shell_blocks_export_button_when_validation_has_blockers(qapp):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([IssueViewModel(code="E1", severity="error", summary="bad", category="Export Blockers")]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()

    shell.run_validation()
    assert shell.export_view.export_button.isEnabled() is False


def test_shell_renders_successful_export_result_with_written_files(qapp, tmp_path):
    export_service = _ExportService(
        ExportResult(
            status="success",
            written_paths=[str(tmp_path / "ProtocolFile.json"), str(tmp_path / "Analytes.xml")],
        )
    )
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=export_service,
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()
    shell.run_validation()
    shell.export_view.destination.setText(str(tmp_path))
    shell.run_export()

    assert export_service.called is True
    assert shell.export_view.result_status.text() == "Export succeeded"
    assert shell.export_view.result_written_paths.count() == 2
    assert shell.export_view.result_written_paths.item(0).text().endswith("ProtocolFile.json")


def test_shell_renders_failed_export_result_with_reason(qapp, tmp_path):
    export_service = _ExportService(
        ExportResult(
            status="failure",
            destination=str(tmp_path),
            failure_reason="disk full",
            cleanup_note="Partial files may exist.",
        )
    )
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=export_service,
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()
    shell.run_validation()
    shell.export_view.destination.setText(str(tmp_path))
    shell.run_export()

    assert shell.export_view.result_status.text() == "Export failed: disk full"
    assert shell.export_view.result_cleanup_note.text() == "Partial files may exist."


def test_shell_validate_preview_and_export_flow(qapp, tmp_path):
    export_service = _ExportService()
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([IssueViewModel(code="E1", severity="error", summary="bad", category="Export Blockers")]),
        preview_service=_PreviewService(),
        export_service=export_service,
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()

    shell.run_validation()
    assert shell.status_banner.text() == "Validation: current | Preview: stale | Export: blocked | Draft: dirty"

    shell.app_state.validation_state.issues = []
    shell.app_state.validation_state.severity_counts = {"error": 0, "warning": 0, "info": 0}
    shell.app_state.validation_state.export_blocked = False
    shell.app_state.validation_state.stale = False
    shell.run_preview()
    assert shell.app_state.preview_state.protocol_json == "{}"
    assert shell.preview_view.stale_banner.text() == "Preview status: current"
    assert shell.preview_view.export_readiness.text() == "Export readiness: ready"

    shell.export_view.destination.setText(str(tmp_path))
    shell.run_export()
    assert export_service.called is True


def test_shell_restore_draft_applies_section_selection(qapp, messagebox_spy):
    draft_service = _DraftService()
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=draft_service,
    )
    shell.app_state.editor_state.export_settings["draft_path"] = "drafts/sample.json"

    shell.restore_draft()

    assert shell.app_state.editor_state.selected_section_index == 8
    assert shell.stack.currentIndex() == 8
    assert messagebox_spy["info"]



def test_shell_prompts_before_restore_when_dirty(qapp, messagebox_spy):
    draft_service = _DraftService()
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=draft_service,
    )
    shell.app_state.editor_state.export_settings["draft_path"] = "drafts/sample.json"
    shell.app_state.draft_state.dirty = True

    shell.restore_draft()

    assert messagebox_spy["question"]


def test_shell_marks_dirty_after_import_and_review_recompute(qapp):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"

    shell.import_excel()

    assert shell.app_state.draft_state.dirty is True
    assert shell.app_state.draft_state.restore_metadata["last_dirty_reason"] == "excel_import"


def test_shell_preview_persists_last_preview_payload_metadata(qapp):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()

    shell.run_preview()

    payload = shell.app_state.editor_state.export_settings["last_preview_payload"]
    assert payload["protocol_json"] == "{}"
    assert payload["analytes_xml"] == "<xml/>"
    assert shell.app_state.editor_state.export_settings["preview_staleness"]["stale"] is False

def test_shell_refresh_status_sets_section_badges(qapp):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.effective_values = {
        "hidden_vocab": {"SamplePrepAction": ["Mix"]},
        "method": {"method_id": "", "method_version": "1"},
    }
    shell.app_state.editor_state.sample_prep_overrides = [
        {"order": "", "action": "Nope", "source": "S", "destination": "", "volume": "", "duration": "", "force": ""}
    ]
    shell.app_state.editor_state.dilution_overrides = [
        {"name": "D1", "buffer1_ratio": "x", "buffer2_ratio": "", "buffer3_ratio": "3"}
    ]
    shell.app_state.editor_state.unresolved_conflicts = {
        "sample_prep.steps.0.action": [{}],
        "dilution_schemes.0.buffer2_ratio": [{}],
    }
    shell.app_state.validation_state.issues = [IssueViewModel(code="W1", severity="warning", summary="warn", category="Warnings")]
    shell.app_state.validation_state.severity_counts = {"error": 0, "warning": 1, "info": 0}

    shell._refresh_status()

    assert shell.sidebar.item(3).text() == "Sample Prep (4)"
    assert shell.sidebar.item(4).text() == "Dilutions (3)"
    assert shell.sidebar.item(5).text() == "Import Review (3)"
    assert shell.sidebar.item(6).text() == "Validation (1)"



def test_shell_status_transitions_post_edit_validate_preview_export_and_save_restore(qapp, tmp_path, messagebox_spy):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()

    # post-edit/import transition
    assert shell.app_state.validation_is_stale is True
    assert shell.app_state.preview_is_stale is True
    assert shell.app_state.draft_is_dirty is True
    assert shell.sidebar.item(7).text() == "Output Preview (1)"
    assert shell.sidebar.item(8).text() == "Export (2)"

    # post-validate transition
    shell.run_validation()
    assert shell.app_state.validation_is_current is True
    assert shell.app_state.export_is_ready is True
    assert shell.sidebar.item(6).text() == "Validation"
    assert shell.sidebar.item(8).text() == "Export (1)"

    # post-preview transition
    shell.run_preview()
    assert shell.app_state.preview_is_current is True
    assert shell.sidebar.item(7).text() == "Output Preview"
    assert shell.sidebar.item(8).text() == "Export (1)"

    # post-export transition
    shell.export_view.destination.setText(str(tmp_path))
    shell.run_export()
    assert shell.status_banner.text() == "Validation: current | Preview: current | Export: ready | Draft: dirty"

    # post-save transition
    shell.save_draft()
    assert shell.app_state.draft_is_saved is True
    assert shell.sidebar.item(8).text() == "Export"

    # post-restore transition
    shell.app_state.editor_state.export_settings["draft_path"] = "drafts/sample.json"
    shell.restore_draft()
    assert shell.app_state.draft_is_saved is True
    assert shell.status_banner.text() == "Validation: stale | Preview: stale | Export: blocked | Draft: saved"

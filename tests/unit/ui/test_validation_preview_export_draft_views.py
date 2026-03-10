from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.services.export_service import ExportResult
from addon_generator.ui.services.validation_service import ValidationSummary
from addon_generator.ui.shell import MainShell
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.export_view import ExportView


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


class _MergeService:
    def recompute(self, app_state):
        return app_state.import_state.bundles[-1]


class _ValidationService:
    def __init__(self, issues):
        self._issues = issues

    def validate(self, merged):
        grouped: dict[str, list[IssueViewModel]] = {}
        category_counts: dict[str, int] = {}
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
    def __init__(self):
        self._runs = 0

    def generate(self, merged):
        self._runs += 1
        summary = {
            "method_id": "M-1",
            "validation_status": "valid",
            "export_readiness": self._runs > 1,
            "preview_timestamp": f"2026-01-01T00:00:0{self._runs}",
        }
        return "{}", "<xml/>", summary, None


class _ExportService:
    def __init__(self, result: ExportResult | None = None):
        self.called = False
        self.result = result or ExportResult(status="success", written_paths=[])

    def export(self, merged, *, destination_folder, overwrite=False):
        self.called = True
        self.result.destination = destination_folder
        return self.result


class _DraftService:
    def __init__(self, path: Path):
        self.path = path
        self.restore_called = False

    def save(self, app_state, drafts_dir="drafts"):
        app_state.draft_state.dirty = False
        app_state.draft_state.path = str(self.path)
        return self.path

    def load(self, path):
        return {
            "import_state": {"bundles": [{"source_type": "excel", "method": {"key": "m", "method_id": "RM", "method_version": "1"}}], "provenance": {}},
            "editor_state": {
                "manual_overrides": {},
                "effective_values": {},
                "unresolved_conflicts": {},
                "selected_entity": None,
                "selected_section_index": 8,
                "export_settings": {},
                "sample_prep_overrides": [],
                "dilution_overrides": [],
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
                "protocol_json": "{}",
                "analytes_xml": "<xml/>",
                "summary": {"validation_status": "valid", "export_readiness": True},
                "validation_state_snapshot": "valid",
                "export_readiness_snapshot": True,
                "last_generated_at": None,
                "generation_error": None,
            },
            "draft_state": {"path": path, "payload": {}},
        }

    def restore(self, app_state, payload, *, source_path=None):
        self.restore_called = True
        app_state.editor_state.selected_section_index = payload["editor_state"]["selected_section_index"]
        app_state.draft_state.dirty = False


def _build_shell(*, issues: list[IssueViewModel], export_result: ExportResult | None = None, draft_path: Path | None = None) -> MainShell:
    draft_service = _DraftService(draft_path or Path("drafts/mock.json"))
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService(issues),
        preview_service=_PreviewService(),
        export_service=_ExportService(export_result),
        draft_service=draft_service,
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()
    return shell


def test_validation_grouped_rendering_filters_and_navigation_callback(qapp) -> None:
    shell = _build_shell(
        issues=[
            IssueViewModel(code="E-1", severity="error", summary="Method missing", category="Method", entity_context="method"),
            IssueViewModel(code="W-1", severity="warning", summary="Assay warning", category="Assays", entity_context="assay/A1"),
            IssueViewModel(code="I-1", severity="info", summary="Assay info", category="Assays", entity_context="assay/A2"),
        ]
    )

    shell.run_validation()
    issue_list = shell.validation_view.issues

    assert issue_list.tree.topLevelItemCount() == 2
    assert issue_list.tree.topLevelItem(0).text(0) == "Assays (2)"
    assert issue_list.tree.topLevelItem(1).text(0) == "Method (1)"

    issue_list.severity_filter.setCurrentText("warning")
    assert issue_list.tree.topLevelItemCount() == 1
    assert issue_list.tree.topLevelItem(0).text(0) == "Assays (1)"

    issue_list.severity_filter.setCurrentText("all")
    issue_list.category_filter.setCurrentText("Method")
    assert issue_list.tree.topLevelItemCount() == 1
    assert issue_list.tree.topLevelItem(0).child(0).text(0).startswith("[error] E-1")

    issue_list.category_filter.setCurrentText("all")
    method_group = issue_list.tree.topLevelItem(1)
    method_issue = method_group.child(0)
    issue_list.tree.setCurrentItem(method_issue)

    assert shell.sidebar.currentRow() == 0
    assert shell.app_state.editor_state.selected_entity == "method"


def test_preview_stale_banner_transitions_and_summary_refresh(qapp) -> None:
    shell = _build_shell(issues=[])

    shell.run_preview()
    first_summary = json.loads(shell.preview_view.tabs.summary.toPlainText())

    assert shell.preview_view.stale_banner.text() == "Preview status: current"
    assert first_summary["export_readiness"] is False

    shell._mark_dirty(reason="editor")
    shell._refresh_status()
    assert shell.preview_view.stale_banner.text() == "Preview status: stale"

    shell.run_preview()
    second_summary = json.loads(shell.preview_view.tabs.summary.toPlainText())
    assert shell.preview_view.stale_banner.text() == "Preview status: current"
    assert second_summary["export_readiness"] is True


def test_export_view_validation_gating_and_result_rendering(qapp, tmp_path) -> None:
    blocking_issue = IssueViewModel(code="E-9", severity="error", summary="Blocking", category="Export", entity_context="method")
    blocking_shell = _build_shell(issues=[blocking_issue])
    blocking_shell.export_view.destination.setText(str(tmp_path))

    blocking_shell.run_export()

    assert blocking_shell.export_view.result_status.text().startswith("Export failed: Export blocked by validation blockers")

    success_shell = _build_shell(
        issues=[],
        export_result=ExportResult(status="success", written_paths=[str(tmp_path / "ProtocolFile.json")], destination=str(tmp_path)),
    )
    success_shell.run_validation()
    success_shell.export_view.destination.setText(str(tmp_path))
    success_shell.run_export()

    assert success_shell.export_view.result_status.text() == "Export succeeded"
    assert success_shell.export_view.result_written_paths.count() == 1

    failure_view = ExportView()
    failure_view.set_export_result(ExportResult(status="failure", destination=str(tmp_path), failure_reason="disk full", cleanup_note="remove temp files"))
    assert failure_view.result_status.text() == "Export failed: disk full"
    assert failure_view.result_cleanup_note.text() == "remove temp files"


def test_draft_save_restore_dirty_state_handling(qapp, tmp_path, monkeypatch, messagebox_spy) -> None:
    draft_path = tmp_path / "draft.json"
    shell = _build_shell(issues=[], draft_path=draft_path)
    draft_service = shell.draft_service

    shell.app_state.draft_state.dirty = True
    shell.save_draft()
    assert shell.app_state.draft_state.dirty is False
    assert any(title == "Draft Saved" for title, _ in messagebox_spy["info"])

    def _deny(*args, **kwargs):
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_deny))
    shell.app_state.editor_state.export_settings["draft_path"] = str(draft_path)
    shell.app_state.draft_state.dirty = True
    shell.restore_draft()
    assert draft_service.restore_called is False

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes))
    shell.restore_draft()
    assert draft_service.restore_called is True
    assert shell.app_state.draft_state.dirty is False

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import (
    AnalyteInputDTO,
    AssayInputDTO,
    DilutionSchemeInputDTO,
    InputDTOBundle,
    MethodInputDTO,
    SamplePrepStepInputDTO,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.services.export_service import ExportResult
from addon_generator.ui.services.draft_service import DraftService
from addon_generator.ui.shell import MainShell
from addon_generator.ui.services.validation_service import ValidationSummary
from addon_generator.ui.state.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def messagebox_spy(monkeypatch):
    calls = {"info": [], "question": [], "warning": [], "about": []}

    def _info(parent, title, text):
        calls["info"].append((title, text))
        return QMessageBox.StandardButton.Ok

    def _question(parent, title, text, buttons, default):
        calls["question"].append((title, text))
        return QMessageBox.StandardButton.Yes

    def _warning(parent, title, text):
        calls["warning"].append((title, text))
        return QMessageBox.StandardButton.Ok

    def _about(parent, title, text):
        calls["about"].append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", staticmethod(_info))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(_question))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(_warning))
    monkeypatch.setattr(QMessageBox, "about", staticmethod(_about))
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




class _UpdateService:
    def __init__(self, *, check_result=(None, None), stage_result=(None, None)):
        self.check_result = check_result
        self.stage_result = stage_result
        self.check_calls = []
        self.stage_calls = []

    def check(self, *, manifest_url):
        self.check_calls.append(manifest_url)
        return self.check_result

    def stage_update(self, *, manifest_url, download_dir, restart_command):
        self.stage_calls.append((manifest_url, download_dir, restart_command))
        return self.stage_result

class _DraftService:
    def __init__(self):
        self.saved = False

    def save(self, app_state, drafts_dir="drafts", draft_path=None):
        self.saved = True
        return Path(draft_path) if draft_path else Path("drafts/mock.json")

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


def test_shell_save_draft_syncs_manual_entry_into_saved_json(qapp, monkeypatch, tmp_path):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=DraftService(),
    )

    shell.manual_entry_view.set_assays_rows(
        [
            {
                "product_number": "P-100",
                "component_name": "Calibrator",
                "parameter_set_number": "PS-01",
                "assay_abbreviation": "CAL",
                "parameter_set_name": "BASIC Kit",
                "type": "Liquid",
                "container_type": "Vial",
            }
        ]
    )
    shell.manual_entry_view.set_analytes_rows(
        [
            {
                "name": "Glucose",
                "assay_key": "BASIC Kit",
                "unit_names": "mg/dL",
            }
        ]
    )

    shell.manual_entry_view.sample_prep_table.setItem(0, 0, None)
    shell.manual_entry_view.sample_prep_table.setItem(0, 1, None)
    shell.manual_entry_view.sample_prep_table.setItem(0, 2, None)
    shell.manual_entry_view.sample_prep_table.cellWidget(0, 0).setCurrentText("Mix")
    shell.manual_entry_view.sample_prep_table.cellWidget(0, 1).setCurrentText("Calibrator")
    shell.manual_entry_view.sample_prep_table.cellWidget(0, 2).setCurrentText("Calibrator")

    draft_path = tmp_path / "synced-draft.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(draft_path), "")))

    shell.save_draft()

    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    bundle = payload["import_state"]["bundles"][0]

    assert bundle["analytes"]
    assert bundle["sample_prep_steps"]
    assert bundle["assays"][0]["metadata"]["component_name"] == "Calibrator"

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


def test_shell_restore_draft_applies_section_selection(qapp, messagebox_spy, monkeypatch):
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
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("drafts/sample.json", "")))

    shell.restore_draft()

    assert shell.app_state.editor_state.selected_section_index == 8
    assert shell.stack.currentIndex() == 8
    assert messagebox_spy["info"]


def test_shell_restore_draft_reapplies_admin_dropdown_values(qapp, monkeypatch):
    class _DraftServiceWithAdmin(_DraftService):
        def load(self, path):
            payload = super().load(path)
            payload["editor_state"]["export_settings"] = {
                "admin_kit_types": ["Solid", "Powder"],
                "admin_container_types": ["Bottle", "Pouch"],
                "admin_analyte_units": ["mg/dL", "IU/L"],
                "admin_sample_prep_actions": ["Mix", "Shake"],
            }
            return payload

        def restore(self, app_state, payload, *, source_path=None):
            app_state.editor_state.export_settings = dict(payload["editor_state"]["export_settings"])
            super().restore(app_state, payload, source_path=source_path)

    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftServiceWithAdmin(),
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("drafts/sample.json", "")))
    shell.restore_draft()

    assay_type_combo = shell.manual_entry_view.assays_table.cellWidget(0, 5)
    container_combo = shell.manual_entry_view.assays_table.cellWidget(0, 6)
    analyte_unit_combo = shell.manual_entry_view.analytes_table.cellWidget(0, 2)
    action_combo = shell.manual_entry_view.sample_prep_table.cellWidget(0, 0)

    assert assay_type_combo.findText("Powder") >= 0
    assert container_combo.findText("Pouch") >= 0
    assert analyte_unit_combo.findText("IU/L") >= 0
    assert action_combo.findText("Shake") >= 0


def test_shell_restore_draft_populates_manual_tables_from_restored_bundle(qapp, monkeypatch):
    class _DraftServiceWithBundle(_DraftService):
        def restore(self, app_state, payload, *, source_path=None):
            app_state.import_state.bundles = [
                InputDTOBundle(
                    source_type="draft",
                    method=MethodInputDTO(
                        key="method:1",
                        display_name="Restored Kit",
                        series_name="Series-R",
                        order_number="KIT-R",
                    ),
                    assays=[
                        AssayInputDTO(
                            key="PS-R",
                            protocol_display_name="Component A",
                            xml_name="Basic Kit",
                            metadata={"component_name": "Component A", "parameter_set_name": "Basic Kit"},
                        )
                    ],
                    analytes=[AnalyteInputDTO(key="analyte:1", name="A", assay_key="Basic Kit")],
                    sample_prep_steps=[
                        SamplePrepStepInputDTO(
                            key="sample-1",
                            label="Mix",
                            metadata={"source": "Component A", "destination": "Component A", "duration": "00:30"},
                        )
                    ],
                    dilution_schemes=[
                        DilutionSchemeInputDTO(
                            key="1+4",
                            label="1+4",
                            metadata={"buffer1_ratio": "50", "buffer2_ratio": "50"},
                        )
                    ],
                )
            ]
            app_state.editor_state.selected_section_index = payload["editor_state"]["selected_section_index"]

    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftServiceWithBundle(),
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("drafts/sample.json", "")))
    shell.restore_draft()

    assert shell.manual_entry_view.sample_prep_table.cellWidget(0, 0).currentText() == "Mix"
    assert shell.manual_entry_view.sample_prep_table.cellWidget(0, 1).currentText() == "Component A"
    assert shell.manual_entry_view.dilutions_table.item(0, 0).text() == "1+4"
    assert shell.manual_entry_view.dilutions_table.item(0, 1).text() == "50"



def test_shell_prompts_before_restore_when_dirty(qapp, messagebox_spy, monkeypatch):
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
    shell.app_state.draft_state.dirty = True
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("drafts/sample.json", "")))

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
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(tmp_path / "draft.json"), "")))
    shell.save_draft()
    assert shell.app_state.draft_is_saved is True
    assert shell.sidebar.item(8).text() == "Export"

    # post-restore transition
    shell.app_state.editor_state.export_settings["draft_path"] = "drafts/sample.json"
    shell.restore_draft()
    assert shell.app_state.draft_is_saved is True
    assert shell.status_banner.text() == "Validation: stale | Preview: stale | Export: blocked | Draft: saved"


def test_shell_help_menu_actions_present(qapp):
    shell = MainShell()
    labels = [action.text() for action in shell.help_menu.actions()]

    assert labels == ["Check for Updates", "Open Logs", "About"]


def test_shell_about_dialog_uses_about_metadata(qapp, messagebox_spy):
    shell = MainShell()

    shell.show_about_dialog()

    assert messagebox_spy["about"]
    _title, message = messagebox_spy["about"][0]
    assert "App Version:" in message
    assert "Build Version:" in message
    assert "Draft Format Version:" in message
    assert "Config Schema Version:" in message


def test_shell_check_for_updates_prompts_and_stages(qapp, messagebox_spy):
    update_service = _UpdateService(
        check_result=(type("R", (), {"status": "available", "available_version": "9.9.9", "current_version": "0.1.0"})(), None),
        stage_result=(type("R", (), {"details": "Installer launched."})(), None),
    )
    shell = MainShell(update_service=update_service)

    shell.check_for_updates()

    assert update_service.check_calls
    assert messagebox_spy["question"]
    assert update_service.stage_calls
    assert messagebox_spy["info"]


def test_shell_check_for_updates_handles_error(qapp, messagebox_spy):
    update_service = _UpdateService(check_result=(None, {"message": "offline"}))
    shell = MainShell(update_service=update_service)

    shell.check_for_updates()

    assert messagebox_spy["warning"] == [("Update Check Failed", "offline")]


def test_shell_open_logs_uses_runtime_log_directory(qapp, monkeypatch, tmp_path):
    shell = MainShell()
    opened = []

    class _Paths:
        logs_dir = tmp_path / "logs"

    monkeypatch.setattr("addon_generator.ui.shell.get_runtime_paths", lambda: _Paths())
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toLocalFile()) or True))

    shell.open_logs_directory()

    assert opened == [str(tmp_path / "logs")]
    assert (tmp_path / "logs").exists()


def test_shell_import_excel_prompts_for_file_when_setting_missing(qapp, monkeypatch):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )

    chosen = "/tmp/from-dialog.xlsx"

    def _open_file_name(*_args, **_kwargs):
        return chosen, "Excel Files (*.xlsx *.xlsm *.xls)"

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(_open_file_name))

    shell.import_excel()

    assert shell.app_state.editor_state.export_settings["excel_path"] == chosen
    assert shell.app_state.import_state.bundles[0].source_type == "excel"


def test_shell_import_xml_prompts_for_file_when_setting_missing(qapp, monkeypatch):
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([]),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )

    chosen = "/tmp/from-dialog.xml"

    def _open_file_name(*_args, **_kwargs):
        return chosen, "XML Files (*.xml)"

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(_open_file_name))

    shell.import_xml()

    assert shell.app_state.editor_state.export_settings["xml_path"] == chosen
    assert shell.app_state.import_state.bundles[0].source_type == "xml"

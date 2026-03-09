from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.shell import MainShell
from addon_generator.ui.state.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


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
        return object(), self._issues


class _PreviewService:
    def generate(self, merged):
        return "{}", "<xml/>", {"export_readiness": True}


class _ExportService:
    def __init__(self):
        self.called = False

    def export(self, merged, *, destination_folder, overwrite=False):
        self.called = True
        return {"ProtocolFile.json": f"{destination_folder}/ProtocolFile.json"}


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
            "preview_state": {"stale": True, "protocol_json": "", "analytes_xml": "", "summary": None},
            "draft_state": {"path": path, "payload": {}},
        }

    def restore(self, app_state, payload, *, source_path=None):
        app_state.editor_state.selected_section_index = payload["editor_state"]["selected_section_index"]


def test_shell_validate_preview_and_export_flow(qapp, tmp_path):
    export_service = _ExportService()
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService([IssueViewModel(code="E1", severity="error", summary="bad")]),
        preview_service=_PreviewService(),
        export_service=export_service,
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()

    shell.run_validation()
    assert shell.status_banner.text() == "Validation errors present"
    assert shell.export_view.export_button.isEnabled() is False

    shell.app_state.validation_state.issues = []
    shell.run_preview()
    assert shell.app_state.preview_state.protocol_json == "{}"

    shell.export_view.destination.setText(str(tmp_path))
    shell.run_export()
    assert export_service.called is True


def test_shell_restore_draft_applies_section_selection(qapp):
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

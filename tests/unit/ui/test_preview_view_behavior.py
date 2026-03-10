from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO
from addon_generator.ui.shell import MainShell
from addon_generator.ui.state.app_state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _ImportService:
    def load_excel(self, path):
        bundle = InputDTOBundle(source_type="excel", method=MethodInputDTO(key="m", method_id="M-1", method_version="2"))
        return bundle, {}, []


class _MergeService:
    def recompute(self, app_state):
        app_state.preview_state.stale = True
        return app_state.import_state.bundles[0]


class _ValidationService:
    def validate(self, merged):
        raise AssertionError("not used")


class _PreviewService:
    def generate(self, merged):
        summary = {
            "method_id": "M-1",
            "method_version": "2",
            "assay_count": 1,
            "analyte_count": 3,
            "sample_prep_count": 2,
            "dilution_count": 1,
            "validation_status": "valid",
            "preview_timestamp": "2026-01-01T00:00:00",
            "export_readiness": True,
        }
        return "{}", "<analytes/>", summary, None


class _ExportService:
    def export(self, merged, *, destination_folder, overwrite=False):
        return {}


class _DraftService:
    def save(self, app_state, drafts_dir="drafts"):
        return None


def _build_shell() -> MainShell:
    shell = MainShell(
        app_state=AppState(),
        import_service=_ImportService(),
        merge_service=_MergeService(),
        validation_service=_ValidationService(),
        preview_service=_PreviewService(),
        export_service=_ExportService(),
        draft_service=_DraftService(),
    )
    shell.app_state.editor_state.export_settings["excel_path"] = "dummy.xlsx"
    shell.import_excel()
    return shell


def test_preview_stale_indicator_transition_after_edit(qapp):
    shell = _build_shell()
    shell.run_preview()
    assert shell.preview_view.stale_banner.text() == "Preview status: current"

    shell.app_state.preview_state.stale = True
    shell._refresh_status()
    assert shell.preview_view.stale_banner.text() == "Preview status: stale"


def test_preview_refresh_updates_summary_and_readiness(qapp):
    shell = _build_shell()
    shell.run_preview()

    assert '"method_id": "M-1"' in shell.preview_view.tabs.summary.toPlainText()
    assert shell.preview_view.validation_readiness.text() == "Validation: valid"
    assert shell.preview_view.export_readiness.text() == "Export readiness: ready"

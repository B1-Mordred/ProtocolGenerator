from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QPushButton, QStackedWidget, QStatusBar, QToolBar

from addon_generator.ui.services.draft_service import DraftService
from addon_generator.ui.services.export_service import ExportService
from addon_generator.ui.services.import_service import ImportService
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.services.preview_service import PreviewService
from addon_generator.ui.services.validation_service import ValidationService
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.analytes_view import AnalytesView
from addon_generator.ui.views.assays_view import AssaysView
from addon_generator.ui.views.dilutions_view import DilutionsView
from addon_generator.ui.views.export_view import ExportView
from addon_generator.ui.views.import_review_view import ImportReviewView
from addon_generator.ui.views.method_view import MethodView
from addon_generator.ui.views.preview_view import PreviewView
from addon_generator.ui.views.sampleprep_view import SamplePrepView
from addon_generator.ui.views.validation_view import ValidationView
from addon_generator.ui.widgets.field_help_panel import FieldHelpPanel
from addon_generator.ui.widgets.navigation_sidebar import NavigationSidebar
from addon_generator.ui.widgets.status_banner import StatusBanner


SECTIONS = [
    "Method",
    "Assays",
    "Analytes",
    "Sample Prep",
    "Dilutions",
    "Import Review",
    "Validation",
    "Output Preview",
    "Export",
]


class MainShell(QMainWindow):
    def __init__(
        self,
        app_state: AppState | None = None,
        *,
        import_service: ImportService | None = None,
        merge_service: MergeServiceAdapter | None = None,
        validation_service: ValidationService | None = None,
        preview_service: PreviewService | None = None,
        export_service: ExportService | None = None,
        draft_service: DraftService | None = None,
    ) -> None:
        super().__init__()
        self.app_state = app_state or AppState()
        self.import_service = import_service or ImportService()
        self.merge_service = merge_service or MergeServiceAdapter()
        self.validation_service = validation_service or ValidationService()
        self.preview_service = preview_service or PreviewService()
        self.export_service = export_service or ExportService()
        self.draft_service = draft_service or DraftService()

        self.setWindowTitle("AddOn Authoring")
        self._last_merged_bundle = None

        self.sidebar = NavigationSidebar(SECTIONS, self)
        self.sidebar.section_changed.connect(self._switch_section)

        dock = QDockWidget("Navigation", self)
        dock.setWidget(self.sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(MethodView(self))
        self.stack.addWidget(AssaysView(self))
        self.stack.addWidget(AnalytesView(self))
        self.stack.addWidget(SamplePrepView(self, app_state=self.app_state, merge_service=self.merge_service))
        self.stack.addWidget(DilutionsView(self, app_state=self.app_state, merge_service=self.merge_service))
        self.stack.addWidget(ImportReviewView(self))
        self.validation_view = ValidationView(self)
        self.stack.addWidget(self.validation_view)
        self.preview_view = PreviewView(self)
        self.stack.addWidget(self.preview_view)
        self.export_view = ExportView(self)
        self.stack.addWidget(self.export_view)
        self.setCentralWidget(self.stack)

        context_dock = QDockWidget("Context", self)
        context_dock.setWidget(FieldHelpPanel("Field Help", "Select a field to view provenance and validation context."))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, context_dock)

        self.toolbar = QToolBar("Actions", self)
        self.actions: dict[str, QPushButton] = {}
        self._add_toolbar_action("Import Excel", self.import_excel)
        self._add_toolbar_action("Import XML", self.import_xml)
        self._add_toolbar_action("Validate", self.run_validation)
        self._add_toolbar_action("Preview Outputs", self.run_preview)
        self._add_toolbar_action("Save Draft", self.save_draft)
        self._add_toolbar_action("Restore Draft", self.restore_draft)
        self._add_toolbar_action("Export", self.run_export)
        self.addToolBar(self.toolbar)

        self.status_banner = StatusBanner(self)
        status_bar = QStatusBar(self)
        status_bar.addWidget(self.status_banner)
        self.setStatusBar(status_bar)

        self.preview_view.regenerate_button.clicked.connect(self.run_preview)
        self.export_view.export_button.clicked.connect(self.run_export)
        self.validation_view.issues.issue_selected.connect(self._on_issue_selected)

        self.sidebar.setCurrentRow(self.app_state.editor_state.selected_section_index)
        self._refresh_status()

    def _add_toolbar_action(self, label: str, callback: Callable[[], None]) -> None:
        button = QPushButton(label, self)
        button.clicked.connect(callback)
        self.toolbar.addWidget(button)
        self.actions[label] = button

    def import_excel(self) -> None:
        source_path = self.app_state.editor_state.export_settings.get("excel_path")
        if not source_path:
            return
        bundle, provenance, issues = self.import_service.load_excel(source_path)
        self.app_state.import_state.replace(bundles=[bundle], provenance=provenance, issues=issues)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        self._refresh_status()

    def import_xml(self) -> None:
        source_path = self.app_state.editor_state.export_settings.get("xml_path")
        if not source_path:
            return
        bundle, provenance, issues = self.import_service.load_xml(source_path)
        self.app_state.import_state.replace(bundles=[bundle], provenance=provenance, issues=issues)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        self._refresh_status()

    def run_validation(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return
        _addon, issues = self.validation_service.validate(merged)
        self.app_state.validation_state.issues = issues
        self.app_state.validation_state.stale = False
        self.validation_view.issues.set_issues(issues)
        self.sidebar.set_issue_count(6, len(issues))
        self._refresh_status()

    def run_preview(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return
        protocol, analytes, summary = self.preview_service.generate(merged)
        self.app_state.preview_state.protocol_json = protocol
        self.app_state.preview_state.analytes_xml = analytes
        self.app_state.preview_state.summary = summary
        self.app_state.preview_state.stale = False
        self.preview_view.tabs.set_preview(protocol, analytes, str(summary))
        self._refresh_status()

    def run_export(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return
        destination = self.export_view.destination.text().strip() or self.app_state.editor_state.export_settings.get("destination_folder")
        if not destination:
            return
        overwrite = self.export_view.overwrite.isChecked()
        self.app_state.editor_state.export_settings["destination_folder"] = destination
        self.app_state.editor_state.export_settings["overwrite"] = overwrite
        self.export_service.export(merged, destination_folder=destination, overwrite=overwrite)

    def save_draft(self) -> None:
        drafts_dir = self.app_state.editor_state.export_settings.get("drafts_dir", "drafts")
        self.draft_service.save(self.app_state, drafts_dir=drafts_dir)

    def restore_draft(self) -> None:
        draft_path = self.app_state.editor_state.export_settings.get("draft_path") or self.app_state.draft_state.path
        if not draft_path:
            return
        payload = self.draft_service.load(draft_path)
        self.draft_service.restore(self.app_state, payload, source_path=draft_path)
        self.sidebar.setCurrentRow(self.app_state.editor_state.selected_section_index)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state) if self.app_state.import_state.bundles else None
        self._refresh_status()

    def _current_merged_bundle(self):
        if self._last_merged_bundle is None and self.app_state.import_state.bundles:
            self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        return self._last_merged_bundle

    def _on_issue_selected(self, issue) -> None:
        section_map = {"Import": 5, "Validation": 6, "Preview": 7, "Export": 8}
        self.sidebar.setCurrentRow(section_map.get(issue.section, 6))

    def _switch_section(self, index: int) -> None:
        self.app_state.editor_state.selected_section_index = index
        self.stack.setCurrentIndex(index)

    def _refresh_status(self) -> None:
        self.sidebar.set_issue_count(5, len(self.app_state.import_state.issues))
        self.sidebar.set_issue_count(6, len(self.app_state.validation_state.issues))
        self.status_banner.set_status(
            preview_stale=self.app_state.preview_state.stale,
            has_errors=self.app_state.validation_state.has_blockers,
        )
        self.export_view.export_button.setEnabled(not self.app_state.validation_state.has_blockers)

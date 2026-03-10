from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QToolBar,
)

from addon_generator.ui.services.draft_service import DraftService
from addon_generator.ui.services.export_service import ExportResult, ExportService
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
        self.stack.addWidget(
            SamplePrepView(
                self,
                app_state=self.app_state,
                merge_service=self.merge_service,
                on_state_changed=self._on_edit_state_changed,
            )
        )
        self.stack.addWidget(
            DilutionsView(
                self,
                app_state=self.app_state,
                merge_service=self.merge_service,
                on_state_changed=self._on_edit_state_changed,
            )
        )
        self.import_review_view = ImportReviewView(
            self,
            app_state=self.app_state,
            merge_service=self.merge_service,
            navigate_to_owner=self._navigate_to_owner,
            on_state_changed=self._on_import_review_state_changed,
        )
        self.stack.addWidget(self.import_review_view)
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
        self.export_view.choose_destination_button.clicked.connect(self.choose_export_destination)
        self.export_view.validate_button.clicked.connect(self.run_validation)
        self.export_view.export_button.clicked.connect(self.run_export)
        self.validation_view.issues.issue_navigation_requested.connect(self._on_issue_selected)

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
        self._mark_dirty(reason="excel_import")
        self.import_review_view.refresh_table()
        self._refresh_status()

    def import_xml(self) -> None:
        source_path = self.app_state.editor_state.export_settings.get("xml_path")
        if not source_path:
            return
        bundle, provenance, issues = self.import_service.load_xml(source_path)
        self.app_state.import_state.replace(bundles=[bundle], provenance=provenance, issues=issues)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        self._mark_dirty(reason="xml_import")
        self.import_review_view.refresh_table()
        self._refresh_status()

    def run_validation(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return
        _addon, summary = self.validation_service.validate(merged)
        self.app_state.validation_state.issues = summary.issues
        self.app_state.validation_state.grouped_issues = summary.grouped_issues
        self.app_state.validation_state.severity_counts = summary.severity_counts
        self.app_state.validation_state.category_counts = summary.category_counts
        self.app_state.validation_state.export_blocked = summary.export_blocked
        self.app_state.validation_state.last_validated_at = datetime.now()
        self.app_state.validation_state.stale = False
        self.validation_view.issues.set_issues(summary.issues)
        self.validation_view.set_validation_state(self.app_state.validation_state)
        self.preview_view.set_preview_meta(
            stale=self.app_state.preview_state.stale,
            validation_state=self.app_state.preview_state.validation_state_snapshot,
            export_ready=self.app_state.preview_state.export_readiness_snapshot,
            generation_error=self.app_state.preview_state.generation_error,
        )
        self._refresh_status()

    def run_preview(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return
        protocol, analytes, summary, failure = self.preview_service.generate(merged)
        self.app_state.preview_state.protocol_json = protocol
        self.app_state.preview_state.analytes_xml = analytes
        self.app_state.preview_state.summary = summary or None
        self.app_state.preview_state.generation_error = failure.get("message") if failure else None
        self.app_state.preview_state.last_generated_at = datetime.now()
        self.app_state.preview_state.validation_state_snapshot = str(summary.get("validation_status", "unknown")) if summary else "unknown"
        self.app_state.preview_state.export_readiness_snapshot = bool(summary.get("export_readiness", False)) if summary else False
        self.app_state.preview_state.stale = False
        self.app_state.editor_state.export_settings["last_preview_payload"] = {
            "protocol_json": protocol,
            "analytes_xml": analytes,
            "summary": summary,
            "failure": failure,
        }
        self.app_state.editor_state.export_settings["preview_staleness"] = {
            "stale": False,
            "generated_at": self.app_state.preview_state.last_generated_at.isoformat(),
            "validation_snapshot": self.app_state.preview_state.validation_state_snapshot,
            "export_ready": self.app_state.preview_state.export_readiness_snapshot,
        }
        summary_text = json.dumps(summary, indent=2, sort_keys=True) if summary else json.dumps(failure or {}, indent=2, sort_keys=True)
        self.preview_view.tabs.set_preview(protocol, analytes, summary_text)
        self._refresh_status()

    def run_export(self) -> None:
        merged = self._current_merged_bundle()
        if merged is None:
            return

        if self.app_state.validation_state.stale:
            self.run_validation()
        if self.app_state.validation_state.has_blockers:
            self.export_view.set_export_result(
                ExportResult(
                    status="failure",
                    destination=self.export_view.destination.text().strip(),
                    failure_reason="Export blocked by validation blockers. Resolve errors and validate again.",
                )
            )
            return

        destination = self.export_view.destination.text().strip() or self.app_state.editor_state.export_settings.get("destination_folder")
        if not destination:
            self.export_view.set_export_result(
                ExportResult(
                    status="failure",
                    failure_reason="Select a destination folder before exporting.",
                )
            )
            return
        overwrite = self.export_view.overwrite.isChecked()
        self.app_state.editor_state.export_settings["destination_folder"] = destination
        self.app_state.editor_state.export_settings["overwrite"] = overwrite
        result = self.export_service.export(merged, destination_folder=destination, overwrite=overwrite)
        self.export_view.set_export_result(result)

    def choose_export_destination(self) -> None:
        current = self.export_view.destination.text().strip() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "Select Export Destination", current)
        if selected:
            self.export_view.destination.setText(selected)
            self.app_state.editor_state.export_settings["destination_folder"] = selected
            self._mark_dirty(reason="destination_changed")
            self._refresh_status()

    def save_draft(self) -> None:
        drafts_dir = self.app_state.editor_state.export_settings.get("drafts_dir", "drafts")
        path = self.draft_service.save(self.app_state, drafts_dir=drafts_dir)
        QMessageBox.information(self, "Draft Saved", f"Draft saved to:\n{path}")
        self._refresh_status()

    def restore_draft(self) -> None:
        draft_path = self.app_state.editor_state.export_settings.get("draft_path") or self.app_state.draft_state.path
        if not draft_path:
            return
        if self.app_state.draft_state.dirty and not self._confirm_unsaved("restore this draft"):
            return
        payload = self.draft_service.load(draft_path)
        self.draft_service.restore(self.app_state, payload, source_path=draft_path)
        self.sidebar.setCurrentRow(self.app_state.editor_state.selected_section_index)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state) if self.app_state.import_state.bundles else None
        QMessageBox.information(self, "Draft Restored", f"Draft restored from:\n{draft_path}")
        self._refresh_status()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.app_state.draft_state.dirty and not self._confirm_unsaved("close the window"):
            event.ignore()
            return
        super().closeEvent(event)

    def _current_merged_bundle(self):
        if self._last_merged_bundle is None and self.app_state.import_state.bundles:
            self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        return self._last_merged_bundle

    def _on_issue_selected(self, jump_target: dict[str, object]) -> None:
        section_index = int(jump_target.get("section_index", 6))
        self.app_state.editor_state.selected_entity = str(jump_target.get("entity", ""))
        self.sidebar.setCurrentRow(section_index)

    def _switch_section(self, index: int) -> None:
        self.app_state.editor_state.selected_section_index = index
        self.stack.setCurrentIndex(index)

    def _on_import_review_state_changed(self) -> None:
        if self.app_state.import_state.bundles:
            self._last_merged_bundle = self.merge_service.recompute(self.app_state)
            self._mark_dirty(reason="import_review")
        self._refresh_status()

    def _on_edit_state_changed(self) -> None:
        self._mark_dirty(reason="editor")
        self._refresh_status()

    def _navigate_to_owner(self, jump_target: dict[str, object]) -> None:
        section_index = int(jump_target.get("section_index", 5))
        self.app_state.editor_state.selected_entity = str(jump_target.get("entity", ""))
        self.sidebar.setCurrentRow(section_index)

    def _refresh_status(self) -> None:
        self.sidebar.set_issue_count(3, self.app_state.sample_prep_badge_count)
        self.sidebar.set_issue_count(4, self.app_state.dilutions_badge_count)
        self.sidebar.set_issue_count(5, self.app_state.import_review_badge_count)
        self.sidebar.set_issue_count(6, self.app_state.validation_badge_count)
        self.status_banner.set_status(
            preview_stale=self.app_state.preview_state.stale,
            has_errors=self.app_state.validation_state.has_blockers,
        )
        self.export_view.export_button.setEnabled(not self.app_state.validation_state.has_blockers)
        self.validation_view.set_validation_state(self.app_state.validation_state)
        self.preview_view.set_preview_meta(
            stale=self.app_state.preview_state.stale,
            validation_state=self.app_state.preview_state.validation_state_snapshot,
            export_ready=self.app_state.preview_state.export_readiness_snapshot,
            generation_error=self.app_state.preview_state.generation_error,
        )

    def _mark_dirty(self, *, reason: str) -> None:
        self.app_state.draft_state.dirty = True
        self.app_state.draft_state.restore_metadata["last_dirty_reason"] = reason
        self.app_state.draft_state.restore_metadata["last_dirty_at"] = datetime.now(tz=timezone.utc).isoformat()
        self.app_state.editor_state.export_settings["preview_staleness"] = {
            "stale": self.app_state.preview_state.stale,
            "validation_stale": self.app_state.validation_state.stale,
            "dirty": self.app_state.draft_state.dirty,
        }

    def _confirm_unsaved(self, action: str) -> bool:
        response = QMessageBox.question(
            self,
            "Unsaved changes",
            f"You have unsaved draft changes. Do you want to {action}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

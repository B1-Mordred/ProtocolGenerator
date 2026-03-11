from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QToolBar,
)

from addon_generator.__about__ import (
    __app_name__,
    __config_schema_version__,
    __draft_format_version__,
    __version__,
)
from addon_generator.importers.gui_mapper import map_gui_payload_to_bundle
from addon_generator.input_models.dtos import DilutionSchemeInputDTO, SamplePrepStepInputDTO
from addon_generator.runtime.paths import get_runtime_paths
from addon_generator.ui.services.draft_service import DraftService
from addon_generator.ui.services.export_service import ExportResult, ExportService
from addon_generator.ui.services.import_service import ImportService
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.services.preview_service import PreviewService
from addon_generator.ui.services.update_service import UpdateService
from addon_generator.ui.services.validation_service import ValidationService
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.views.analytes_view import AnalytesView
from addon_generator.ui.views.assays_view import AssaysView
from addon_generator.ui.views.dilutions_view import DilutionsView
from addon_generator.ui.views.data_entry_home_view import DataEntryHomeView
from addon_generator.ui.views.export_view import ExportView
from addon_generator.ui.views.field_mapping_view import FieldMappingView
from addon_generator.ui.views.import_review_view import ImportReviewView
from addon_generator.ui.views.manual_entry_view import ManualEntryView
from addon_generator.ui.views.method_view import MethodView
from addon_generator.ui.views.preview_view import PreviewView
from addon_generator.ui.views.sampleprep_view import SamplePrepView
from addon_generator.ui.views.validation_view import ValidationView
from addon_generator.ui.widgets.field_help_panel import FieldHelpPanel
from addon_generator.ui.widgets.navigation_sidebar import NavigationSidebar
from addon_generator.ui.widgets.status_banner import StatusBanner




DEFAULT_UPDATE_MANIFEST_URL = "https://example.invalid/addon-generator/update.json"

SECTIONS = [
    "Method",
    "Assays",
    "Analytes",
    "Sample Prep",
    "Dilutions",
    "Import Review",
    "Validation",
    "Output Preview",
    "Field Mapping",
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
        update_service: UpdateService | None = None,
    ) -> None:
        super().__init__()
        self.app_state = app_state or AppState()
        self.import_service = import_service or ImportService()
        self.merge_service = merge_service or MergeServiceAdapter()
        self.validation_service = validation_service or ValidationService()
        self.preview_service = preview_service or PreviewService()
        self.export_service = export_service or ExportService()
        self.draft_service = draft_service or DraftService()
        self.update_service = update_service or UpdateService()

        self.setWindowTitle(__app_name__)
        self._last_merged_bundle = None

        self.sidebar = NavigationSidebar(SECTIONS, self)
        self.sidebar.section_changed.connect(self._switch_section)

        dock = QDockWidget("Navigation", self)
        dock.setWidget(self.sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.main_stack = QStackedWidget(self)
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
        self.field_mapping_view = FieldMappingView(self, app_state=self.app_state, on_state_changed=self._on_edit_state_changed)
        self.stack.addWidget(self.field_mapping_view)
        self.export_view = ExportView(self)
        self.stack.addWidget(self.export_view)

        self.entry_home_view = DataEntryHomeView(
            self,
            on_manual_selected=self.show_manual_entry,
            on_excel_selected=self.import_excel,
        )
        self.manual_entry_view = ManualEntryView(self, on_data_changed=self._on_manual_data_changed)
        self._apply_admin_dropdown_settings()

        self.main_stack.addWidget(self.entry_home_view)
        self.main_stack.addWidget(self.manual_entry_view)
        self.main_stack.addWidget(self.stack)
        self.main_stack.setCurrentIndex(2)
        self.setCentralWidget(self.main_stack)

        context_dock = QDockWidget("Context", self)
        context_dock.setWidget(FieldHelpPanel("Field Help", "Select a field to view provenance and validation context."))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, context_dock)

        self.toolbar = QToolBar("Actions", self)
        self.actions: dict[str, QPushButton] = {}
        self._add_toolbar_action("Import Excel", self.import_excel)
        self._add_toolbar_action("Import XML", self.import_xml)
        self._add_toolbar_action("Validate", self.run_validation)
        self._add_toolbar_action("Preview Outputs", self.run_preview)
        self._add_toolbar_action("Save Status", self.save_draft)
        self._add_toolbar_action("Recover from Draft", self.restore_draft)
        self._add_toolbar_action("Export", self.run_export)
        self.addToolBar(self.toolbar)

        self.help_menu = self._build_help_menu()
        self._build_main_menu()

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

    def _build_help_menu(self) -> QMenu:
        help_menu = self.menuBar().addMenu("Help")

        check_updates_action = QAction("Check for Updates", self)
        check_updates_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates_action)

        open_logs_action = QAction("Open Logs", self)
        open_logs_action.triggered.connect(self.open_logs_directory)
        help_menu.addAction(open_logs_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        return help_menu

    def _build_main_menu(self) -> None:
        data_entry_menu = self.menuBar().addMenu("AddOn Data Entry")
        manual_action = QAction("Enter Data Manually", self)
        manual_action.triggered.connect(self.show_manual_entry)
        data_entry_menu.addAction(manual_action)

        import_action = QAction("Import Excel File", self)
        import_action.triggered.connect(self.import_excel)
        data_entry_menu.addAction(import_action)

        data_review_menu = self.menuBar().addMenu("Data Review")
        review_action = QAction("Open Data Review", self)
        review_action.triggered.connect(self.show_data_review)
        data_review_menu.addAction(review_action)

        admin_menu = self.menuBar().addMenu("Admin")

        kit_type_action = QAction("Configure Kit Type Values", self)
        kit_type_action.triggered.connect(self.configure_kit_type_values)
        admin_menu.addAction(kit_type_action)

        container_type_action = QAction("Configure Container Type Values", self)
        container_type_action.triggered.connect(self.configure_container_type_values)
        admin_menu.addAction(container_type_action)

        analyte_unit_action = QAction("Configure Unit of Measurement Values", self)
        analyte_unit_action.triggered.connect(self.configure_analyte_unit_values)
        admin_menu.addAction(analyte_unit_action)

        sample_prep_action = QAction("Configure Sample Prep Action Values", self)
        sample_prep_action.triggered.connect(self.configure_sample_prep_action_values)
        admin_menu.addAction(sample_prep_action)

        field_mapping_action = QAction("Field Mapping", self)
        field_mapping_action.triggered.connect(self.show_field_mapping)
        admin_menu.addAction(field_mapping_action)

    def show_manual_entry(self) -> None:
        current_bundle = self._current_merged_bundle()
        if current_bundle is not None:
            self._populate_manual_entry_from_bundle(current_bundle)
        self.main_stack.setCurrentIndex(1)

    def show_data_entry_home(self) -> None:
        self.main_stack.setCurrentIndex(0)

    def show_data_review(self) -> None:
        self.main_stack.setCurrentIndex(2)
        self.sidebar.setCurrentRow(5)
        self.import_review_view.refresh_table()

    def show_field_mapping(self) -> None:
        self.main_stack.setCurrentIndex(2)
        self.sidebar.setCurrentRow(8)

    def check_for_updates(self) -> None:
        manifest_url = self.app_state.editor_state.export_settings.get("update_manifest_url") or DEFAULT_UPDATE_MANIFEST_URL
        check_result, check_error = self.update_service.check(manifest_url=manifest_url)
        if check_error:
            QMessageBox.warning(self, "Update Check Failed", check_error["message"])
            return
        if check_result.status != "available":
            QMessageBox.information(self, "Updates", "You are already up to date.")
            return

        response = QMessageBox.question(
            self,
            "Update Available",
            f"Version {check_result.available_version} is available (current: {check_result.current_version}).\n"
            "Would you like to download and install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        stage_result, stage_error = self.update_service.stage_update(
            manifest_url=manifest_url,
            download_dir=get_runtime_paths().runtime_support_dir / "updates",
            restart_command=[str(Path(__file__).resolve())],
        )
        if stage_error:
            QMessageBox.warning(self, "Update Failed", stage_error["message"])
            return
        QMessageBox.information(
            self,
            "Update Ready",
            stage_result.details or "Update installer launched. Follow installer instructions to complete the update.",
        )

    def open_logs_directory(self) -> None:
        logs_dir = get_runtime_paths().logs_dir
        logs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))

    def show_about_dialog(self) -> None:
        build_version = __version__.split("+", maxsplit=1)[1] if "+" in __version__ else "n/a"
        QMessageBox.about(
            self,
            "About",
            "\n".join(
                [
                    __app_name__,
                    f"App Version: {__version__}",
                    f"Build Version: {build_version}",
                    f"Draft Format Version: {__draft_format_version__}",
                    f"Config Schema Version: {__config_schema_version__}",
                ]
            ),
        )

    def _add_toolbar_action(self, label: str, callback: Callable[[], None]) -> None:
        button = QPushButton(label, self)
        button.clicked.connect(callback)
        self.toolbar.addWidget(button)
        self.actions[label] = button

    def import_excel(self) -> None:
        source_path = self._resolve_import_source_path(
            setting_key="excel_path",
            title="Select Excel Workbook",
            file_filter="Excel Files (*.xlsx *.xlsm *.xls)",
        )
        if not source_path:
            return
        bundle, provenance, issues = self.import_service.load_excel(source_path)
        self.app_state.import_state.replace(bundles=[bundle], provenance=provenance, issues=issues)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        self._populate_manual_entry_from_bundle(self._last_merged_bundle)
        self._mark_dirty(reason="excel_import")
        self.import_review_view.refresh_table()
        self.main_stack.setCurrentIndex(1)
        self._refresh_status()

    def import_xml(self) -> None:
        source_path = self._resolve_import_source_path(
            setting_key="xml_path",
            title="Select AddOn XML",
            file_filter="XML Files (*.xml)",
        )
        if not source_path:
            return
        bundle, provenance, issues = self.import_service.load_xml(source_path)
        self.app_state.import_state.replace(bundles=[bundle], provenance=provenance, issues=issues)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        self._populate_manual_entry_from_bundle(bundle)
        self._mark_dirty(reason="xml_import")
        self.import_review_view.refresh_table()
        self.show_data_review()
        self._refresh_status()

    def _populate_manual_entry_from_bundle(self, bundle) -> None:
        method = bundle.method
        basics = {
            "kit_series": str(method.series_name or "") if method else "",
            "kit_name": str(method.display_name or "") if method else "",
            "kit_product_number": str(method.order_number or "") if method else "",
            "addon_series": str(method.main_title or "") if method else "",
            "addon_product_name": str(method.sub_title or "") if method else "",
            "addon_product_number": str(method.product_number or "") if method else "",
        }
        self.manual_entry_view.set_basics_values(basics)

        assay_rows = []
        for assay in bundle.assays:
            meta = dict(assay.metadata or {})
            assay_rows.append(
                {
                    "product_number": str(meta.get("product_number") or ""),
                    "component_name": str(meta.get("component_name") or assay.protocol_display_name or assay.xml_name or ""),
                    "parameter_set_number": str(meta.get("parameter_set_number") or assay.key or ""),
                    "assay_abbreviation": str(meta.get("assay_abbreviation") or ""),
                    "parameter_set_name": str(meta.get("parameter_set_name") or assay.xml_name or ""),
                    "type": str(meta.get("type") or assay.protocol_type or ""),
                    "container_type": str(meta.get("container_type") or ""),
                }
            )
        self.manual_entry_view.set_assays_rows(assay_rows)

        analyte_rows = []
        units_by_analyte: dict[str, list[str]] = {}
        for unit in bundle.units:
            units_by_analyte.setdefault(unit.analyte_key, []).append(str(unit.name or ""))
        for analyte in bundle.analytes:
            analyte_rows.append(
                {
                    "name": str(analyte.name or ""),
                    "assay_key": str(analyte.assay_key or ""),
                    "unit_names": "; ".join([u for u in units_by_analyte.get(analyte.key, []) if u]),
                }
            )
        self.manual_entry_view.set_analytes_rows(analyte_rows)

        sample_prep_rows = []
        for step in bundle.sample_prep_steps:
            metadata = dict(step.metadata or {})
            sample_prep_rows.append(
                {
                    "action": str(metadata.get("action") or step.label or ""),
                    "source": str(metadata.get("source") or ""),
                    "destination": str(metadata.get("destination") or ""),
                    "volume": str(metadata.get("volume") or ""),
                    "duration": str(metadata.get("duration") or ""),
                    "force": str(metadata.get("force") or ""),
                }
            )
        self.manual_entry_view.set_sample_prep_rows(sample_prep_rows)

        dilution_rows = []
        for dilution in bundle.dilution_schemes:
            metadata = dict(dilution.metadata or {})
            dilution_rows.append(
                {
                    "key": str(dilution.key or dilution.label or ""),
                    "buffer1_ratio": str(metadata.get("buffer1_ratio") or ""),
                    "buffer2_ratio": str(metadata.get("buffer2_ratio") or ""),
                    "buffer3_ratio": str(metadata.get("buffer3_ratio") or ""),
                }
            )
        self.manual_entry_view.set_dilutions_rows(dilution_rows)

    def _on_manual_data_changed(self) -> None:
        payload = self._sync_manual_entry_to_state()
        if payload is None:
            return
        self.import_review_view.refresh_table()
        self._mark_dirty(reason="manual_entry")
        self._autosave_manual_snapshot(payload)
        self._refresh_status()

    def _sync_manual_entry_to_state(self) -> dict[str, object] | None:
        self.manual_entry_view.refresh_dynamic_dropdowns()
        payload = self.manual_entry_view.payload()
        method = payload["method"]
        current_method = self._current_merged_bundle().method if self._current_merged_bundle() else None
        bundle = map_gui_payload_to_bundle(
            {
                "method_id": method.get("method_id", "") or (current_method.method_id if current_method else ""),
                "method_version": method.get("method_version", "") or (current_method.method_version if current_method else ""),
                "MethodInformation": {
                    "DisplayName": method.get("display_name", "") or method.get("kit_name", ""),
                    "SeriesName": method.get("kit_series", ""),
                    "OrderNumber": method.get("kit_product_number", ""),
                    "MainTitle": method.get("addon_series", ""),
                    "SubTitle": method.get("addon_product_name", ""),
                    "ProductNumber": method.get("addon_product_number", ""),
                },
                "assays": payload["assays"],
                "analytes": payload["analytes"],
            }
        )
        bundle.sample_prep_steps = [
            SamplePrepStepInputDTO(
                key=row.get("key") or f"sample-prep-{index + 1}",
                label=row.get("action") or row.get("key") or f"sample-prep-{index + 1}",
                metadata={k: v for k, v in row.items() if k not in {"key"}},
            )
            for index, row in enumerate(payload["sample_prep"])
            if row.get("action") or row.get("source") or row.get("destination") or row.get("volume") or row.get("duration") or row.get("force")
        ]
        bundle.dilution_schemes = [
            DilutionSchemeInputDTO(
                key=row["key"],
                label=row["key"],
                metadata={k: v for k, v in row.items() if k not in {"key"}},
            )
            for row in payload["dilutions"]
            if row.get("key")
        ]
        self.app_state.import_state.replace(bundles=[bundle], provenance={}, issues=[])
        self._last_merged_bundle = self.merge_service.recompute(self.app_state)
        return payload

    def _autosave_manual_snapshot(self, payload: dict[str, object]) -> None:
        autosave_path = get_runtime_paths().runtime_support_dir / "manual_entry_autosave.json"
        autosave_path.parent.mkdir(parents=True, exist_ok=True)
        autosave_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _parse_csv_options(self, raw: str, defaults: list[str]) -> list[str]:
        values = [part.strip() for part in raw.split(",") if part.strip()]
        return values or defaults

    def _apply_admin_dropdown_settings(self) -> None:
        settings = self.app_state.editor_state.export_settings
        self.manual_entry_view.set_dropdown_options(
            kit_types=list(settings.get("admin_kit_types", ["Solid", "Liquid"])),
            container_types=list(settings.get("admin_container_types", ["Tube", "Bottle", "Vial"])),
            analyte_units=list(settings.get("admin_analyte_units", ["mg/dL", "mmol/L", "ng/mL"])),
            sample_prep_actions=list(settings.get("admin_sample_prep_actions", ["Mix", "Incubate", "Heat"])),
        )

    def _configure_dropdown_setting(
        self,
        *,
        setting_key: str,
        defaults: list[str],
        title: str,
        prompt: str,
        reason: str,
    ) -> None:
        settings = self.app_state.editor_state.export_settings
        current = ", ".join(settings.get(setting_key, defaults))
        raw, ok = QInputDialog.getText(self, title, prompt, text=current)
        if not ok:
            return
        settings[setting_key] = self._parse_csv_options(raw, defaults)
        self._apply_admin_dropdown_settings()
        self._mark_dirty(reason=reason)
        self._refresh_status()

    def configure_kit_type_values(self) -> None:
        self._configure_dropdown_setting(
            setting_key="admin_kit_types",
            defaults=["Solid", "Liquid"],
            title="Configure Type Values",
            prompt="Type values (comma-separated):",
            reason="admin_kit_types",
        )

    def configure_container_type_values(self) -> None:
        self._configure_dropdown_setting(
            setting_key="admin_container_types",
            defaults=["Tube", "Bottle", "Vial"],
            title="Configure Container Type Values",
            prompt="Container Type values (comma-separated):",
            reason="admin_container_types",
        )

    def configure_analyte_unit_values(self) -> None:
        self._configure_dropdown_setting(
            setting_key="admin_analyte_units",
            defaults=["mg/dL", "mmol/L", "ng/mL"],
            title="Configure Unit of Measurement Values",
            prompt="Unit of Measurement values (comma-separated):",
            reason="admin_analyte_units",
        )

    def configure_sample_prep_action_values(self) -> None:
        self._configure_dropdown_setting(
            setting_key="admin_sample_prep_actions",
            defaults=["Mix", "Incubate", "Heat"],
            title="Configure Sample Prep Action Values",
            prompt="Sample Prep Action values (comma-separated):",
            reason="admin_sample_prep_actions",
        )

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
        self._refresh_status()

    def choose_export_destination(self) -> None:
        current = self.export_view.destination.text().strip() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "Select Export Destination", current)
        if selected:
            self.export_view.destination.setText(selected)
            self.app_state.editor_state.export_settings["destination_folder"] = selected
            self._mark_dirty(reason="destination_changed")
            self._refresh_status()

    def _resolve_import_source_path(self, *, setting_key: str, title: str, file_filter: str) -> str:
        source_path = self.app_state.editor_state.export_settings.get(setting_key)
        if source_path:
            return source_path

        selected, _ = QFileDialog.getOpenFileName(self, title, str(Path.cwd()), file_filter)
        if not selected:
            return ""

        self.app_state.editor_state.export_settings[setting_key] = selected
        self._mark_dirty(reason=f"{setting_key}_changed")
        self._refresh_status()
        return selected

    def save_draft(self) -> None:
        self._sync_manual_entry_to_state()
        suggested_dir = self.app_state.editor_state.export_settings.get("drafts_dir") or str(get_runtime_paths().drafts_dir)
        suggested_name = self.app_state.editor_state.export_settings.get("draft_file_name") or "addon_status_draft.json"
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Current Status",
            str(Path(suggested_dir) / suggested_name),
            "Draft Files (*.json)",
        )
        if not selected_path:
            return
        path = self.draft_service.save(self.app_state, draft_path=selected_path)
        self.app_state.editor_state.export_settings["draft_path"] = str(path)
        self.app_state.editor_state.export_settings["drafts_dir"] = str(Path(path).parent)
        self.app_state.editor_state.export_settings["draft_file_name"] = Path(path).name
        QMessageBox.information(self, "Status Saved", f"Current status saved to:\n{path}")
        self._refresh_status()

    def restore_draft(self) -> None:
        draft_path, _ = QFileDialog.getOpenFileName(
            self,
            "Recover from Draft",
            self.app_state.editor_state.export_settings.get("drafts_dir") or str(get_runtime_paths().drafts_dir),
            "Draft Files (*.json)",
        )
        if not draft_path:
            draft_path = self.app_state.editor_state.export_settings.get("draft_path") or self.app_state.draft_state.path
        if not draft_path:
            return
        if self.app_state.draft_state.dirty and not self._confirm_unsaved("restore this draft"):
            return
        payload = self.draft_service.load(draft_path)
        self.draft_service.restore(self.app_state, payload, source_path=draft_path)
        self._apply_admin_dropdown_settings()
        self.sidebar.setCurrentRow(self.app_state.editor_state.selected_section_index)
        self._last_merged_bundle = self.merge_service.recompute(self.app_state) if self.app_state.import_state.bundles else None
        if self._last_merged_bundle is not None:
            self._populate_manual_entry_from_bundle(self._last_merged_bundle)
        QMessageBox.information(self, "Draft Recovered", f"Status recovered from:\n{draft_path}")
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
        self.sidebar.set_issue_count(7, self.app_state.preview_badge_contribution)
        self.sidebar.set_issue_count(8, 0)
        self.sidebar.set_issue_count(9, self.app_state.export_badge_contribution + self.app_state.draft_badge_contribution)
        self.status_banner.set_status(
            validation_stale=self.app_state.validation_is_stale,
            preview_stale=self.app_state.preview_is_stale,
            export_ready=self.app_state.export_is_ready,
            draft_dirty=self.app_state.draft_is_dirty,
        )
        self.export_view.export_button.setEnabled(self.app_state.export_is_ready)
        self.validation_view.set_validation_state(self.app_state.validation_state)
        self.preview_view.set_preview_meta(
            stale=self.app_state.preview_state.stale,
            validation_state=self.app_state.preview_state.validation_state_snapshot,
            export_ready=self.app_state.preview_state.export_readiness_snapshot,
            generation_error=self.app_state.preview_state.generation_error,
        )

    def _mark_dirty(self, *, reason: str) -> None:
        self.app_state.validation_state.stale = True
        self.app_state.preview_state.stale = True
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

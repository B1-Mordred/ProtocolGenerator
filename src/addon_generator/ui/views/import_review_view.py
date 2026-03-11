from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from addon_generator.ui.models.import_review_view_model import ImportReviewFilter, ImportReviewScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


class ImportReviewView(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        app_state: AppState | None = None,
        merge_service: MergeServiceAdapter | None = None,
        navigate_to_owner: Callable[[dict[str, object]], None] | None = None,
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_state = app_state or AppState()
        self._vm = ImportReviewScreenViewModel(self._app_state, merge_service or MergeServiceAdapter())
        self._navigate_to_owner = navigate_to_owner
        self._on_state_changed = on_state_changed
        self._rows = []

        outer = QHBoxLayout(self)
        left = QVBoxLayout()
        self.filter_box = QComboBox(self)
        self.filter_box.addItems([item.value for item in ImportReviewFilter])
        self.filter_box.setCurrentText(ImportReviewFilter.ACTION_REQUIRED.value)
        self.filter_box.currentTextChanged.connect(self.refresh_table)
        left.addWidget(self.filter_box)

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Entity", "Field", "Imported", "Effective", "Source", "Class", "Override", "Conflict"])
        self.table.itemSelectionChanged.connect(self._update_detail_panel)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        left.addWidget(self.table)

        action_row = QHBoxLayout()
        self.accept_btn = QPushButton("Accept Imported", self)
        self.accept_default_btn = QPushButton("Accept Default", self)
        self.keep_btn = QPushButton("Keep Override", self)
        self.revert_btn = QPushButton("Revert Default", self)
        self.clear_btn = QPushButton("Clear Override", self)
        self.jump_btn = QPushButton("Go To Owner", self)
        self.accept_btn.clicked.connect(lambda: self._apply_resolution("accept"))
        self.accept_default_btn.clicked.connect(lambda: self._apply_resolution("accept_default"))
        self.keep_btn.clicked.connect(lambda: self._apply_resolution("keep"))
        self.revert_btn.clicked.connect(lambda: self._apply_resolution("revert"))
        self.clear_btn.clicked.connect(lambda: self._apply_resolution("clear"))
        self.jump_btn.clicked.connect(self._jump_to_owner)
        for button in (self.accept_btn, self.accept_default_btn, self.keep_btn, self.revert_btn, self.clear_btn, self.jump_btn):
            action_row.addWidget(button)
        left.addLayout(action_row)

        outer.addLayout(left, 2)

        right = QVBoxLayout()
        self.detail_title = QLabel("Select a review row", self)
        self.detail_payload = QTextEdit(self)
        self.detail_payload.setReadOnly(True)
        right.addWidget(self.detail_title)
        right.addWidget(self.detail_payload)
        outer.addLayout(right, 1)

        self.refresh_table()

    def refresh_table(self) -> None:
        self._rows = self._vm.rows(self.filter_box.currentText())
        self.table.setRowCount(len(self._rows))
        for row_idx, row in enumerate(self._rows):
            cells = [
                row.entity,
                row.field,
                row.imported_value,
                row.effective_value,
                row.source,
                row.required_classification,
                "Yes" if row.override_status else "No",
                "Yes" if row.conflict_status else "No",
            ]
            for col_idx, cell in enumerate(cells):
                item = QTableWidgetItem(cell)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)
        if self._rows:
            self.table.selectRow(0)
        else:
            self.detail_payload.setPlainText("")

    def _selected_row(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return None
        return self._rows[selected[0].row()]

    def _update_detail_panel(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self.detail_title.setText(f"{row.entity}.{row.field}")
        self.detail_payload.setPlainText(
            "\n".join(
                [
                    f"Imported: {row.imported_value}",
                    f"Effective: {row.effective_value}",
                    f"Classification: {row.required_classification}",
                    f"Fallback: {row.fallback_hint or '(none)'}",
                    f"Override: {row.override_status}",
                    f"Resolution: {row.resolution_state}",
                    "",
                    "Raw provenance:",
                    row.raw_provenance_detail or "(none)",
                    "",
                    "Normalization notes:",
                    row.normalization_notes or "(none)",
                ]
            )
        )

    def _apply_resolution(self, action: str) -> None:
        row = self._selected_row()
        if row is None:
            return
        if action == "accept":
            self._vm.accept_imported(row.path)
        elif action == "accept_default":
            self._vm.accept_default(row.path)
        elif action == "keep":
            self._vm.keep_override(row.path)
        elif action == "revert":
            self._vm.revert_default(row.path)
        elif action == "clear":
            self._vm.clear_override(row.path)
        self.refresh_table()
        if self._on_state_changed:
            self._on_state_changed()

    def _jump_to_owner(self) -> None:
        row = self._selected_row()
        if row is None or self._navigate_to_owner is None:
            return
        self._navigate_to_owner(row.jump_target_metadata)

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from addon_generator.ui.models.dilution_view_model import DILUTION_FIELDS, DilutionScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState

HEADERS = ["Dilution Name", "Buffer 1 Ratio", "Buffer 2 Ratio", "Buffer 3 Ratio", "Provenance summary", "Status"]
FORM_LABELS = {
    "name": "Dilution Name",
    "buffer1_ratio": "Buffer 1 Ratio",
    "buffer2_ratio": "Buffer 2 Ratio",
    "buffer3_ratio": "Buffer 3 Ratio",
}


class _DilutionTableModel(QAbstractTableModel):
    def __init__(self, vm: DilutionScreenViewModel) -> None:
        super().__init__()
        self._vm = vm

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return len(self._vm.dilutions)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return len(HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        dilution = self._vm.dilutions[index.row()]
        row = dilution.to_table_row()
        if role == Qt.DisplayRole:
            return row[index.column()]
        if role == Qt.BackgroundRole and not dilution.is_valid:
            return Qt.GlobalColor.yellow
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class DilutionsView(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        app_state: AppState | None = None,
        merge_service: MergeServiceAdapter | None = None,
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = DilutionScreenViewModel(app_state or AppState(), merge_service or MergeServiceAdapter())
        self._on_state_changed = on_state_changed

        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.delete_btn = QPushButton("Delete")
        self.duplicate_btn = QPushButton("Duplicate")
        for btn in (self.add_btn, self.delete_btn, self.duplicate_btn):
            actions.addWidget(btn)
        layout.addLayout(actions)

        splitter = QSplitter(self)
        self.table = QTableView(self)
        self.table_model = _DilutionTableModel(self._vm)
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.table)

        detail_wrap = QWidget(self)
        detail_layout = QFormLayout(detail_wrap)
        self.inputs: dict[str, QLineEdit] = {}
        self.provenance_labels: dict[str, QLabel] = {}
        self.reference_labels: dict[str, QLabel] = {}
        self.reset_buttons: dict[str, QPushButton] = {}
        for name in DILUTION_FIELDS:
            edit = QLineEdit(self)
            detail_layout.addRow(FORM_LABELS[name], edit)
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            provenance = QLabel("", self)
            reference = QLabel("", self)
            reset = QPushButton("Reset", self)
            row_layout.addWidget(provenance)
            row_layout.addWidget(reference)
            row_layout.addStretch(1)
            row_layout.addWidget(reset)
            detail_layout.addRow("", row)
            self.inputs[name] = edit
            self.provenance_labels[name] = provenance
            self.reference_labels[name] = reference
            self.reset_buttons[name] = reset

        self.status_label = QLabel("", self)
        detail_layout.addRow("Status", self.status_label)
        splitter.addWidget(detail_wrap)
        layout.addWidget(splitter)

        self.add_btn.clicked.connect(self._add_dilution)
        self.delete_btn.clicked.connect(self._delete_dilution)
        self.duplicate_btn.clicked.connect(self._duplicate_dilution)
        self.table.selectionModel().selectionChanged.connect(self._select_from_table)
        for name in DILUTION_FIELDS:
            self.inputs[name].editingFinished.connect(lambda n=name: self._update_field(n))
            self.reset_buttons[name].clicked.connect(lambda _=False, n=name: self._reset_field(n))

        self._refresh_all()

    def _current_dilution_id(self) -> str | None:
        return self._vm.selected_dilution_id

    def _select_from_table(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        dilution = self._vm.dilutions[rows[0].row()]
        self._vm.select_dilution(dilution.dilution_id)
        self._refresh_detail()

    def _add_dilution(self) -> None:
        dilution_id = self._vm.add_dilution()
        self._refresh_all(select_dilution=dilution_id)
        self._notify_state_changed()

    def _delete_dilution(self) -> None:
        dilution_id = self._current_dilution_id()
        if dilution_id:
            self._vm.delete_dilution(dilution_id)
            self._refresh_all(select_dilution=self._vm.selected_dilution_id)
            self._notify_state_changed()

    def _duplicate_dilution(self) -> None:
        dilution_id = self._current_dilution_id()
        if dilution_id:
            new_id = self._vm.duplicate_dilution(dilution_id)
            self._refresh_all(select_dilution=new_id)
            self._notify_state_changed()

    def _update_field(self, field: str) -> None:
        dilution_id = self._current_dilution_id()
        if dilution_id:
            self._vm.update_field(dilution_id, field, self.inputs[field].text())
            self._refresh_all(select_dilution=dilution_id)
            self._notify_state_changed()

    def _reset_field(self, field: str) -> None:
        dilution_id = self._current_dilution_id()
        if dilution_id:
            self._vm.reset_field(dilution_id, field)
            self._refresh_all(select_dilution=dilution_id)
            self._notify_state_changed()

    def _refresh_all(self, *, select_dilution: str | None = None) -> None:
        self.table_model.refresh()
        chosen = select_dilution or self._vm.selected_dilution_id
        if chosen:
            for row, dilution in enumerate(self._vm.dilutions):
                if dilution.dilution_id == chosen:
                    self.table.selectRow(row)
                    self._vm.select_dilution(dilution.dilution_id)
                    break
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        dilution = self._vm.selected_dilution()
        if dilution is None:
            for name in DILUTION_FIELDS:
                self.inputs[name].setText("")
                self.inputs[name].setStyleSheet("")
                self.provenance_labels[name].setText("")
                self.reference_labels[name].setText("")
            self.status_label.setText("No dilution selected")
            return

        for name in DILUTION_FIELDS:
            field = dilution.fields[name]
            self.inputs[name].setText(field.value)
            self.inputs[name].setStyleSheet("border: 1px solid #cc0000;" if not field.is_valid else "")
            self.provenance_labels[name].setText(
                f"[{field.provenance or 'manual'} | {field.status} | effective={field.effective_value}]"
            )
            ref_state = "used" if field.has_reference else "unused"
            ref_context = f" ({field.reference_context})" if field.reference_context else ""
            self.reference_labels[name].setText(f"ref:{ref_state}{ref_context}")

        if dilution.is_valid:
            self.status_label.setText("ok")
        elif not dilution.is_complete and not dilution.is_ratio_valid:
            self.status_label.setText("incomplete and invalid ratio")
        elif not dilution.is_complete:
            self.status_label.setText("incomplete")
        else:
            self.status_label.setText("invalid ratio")

    def _notify_state_changed(self) -> None:
        if self._on_state_changed:
            self._on_state_changed()

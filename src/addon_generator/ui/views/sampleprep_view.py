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

from addon_generator.ui.models.sampleprep_view_model import FIELD_ORDER, SamplePrepScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.widgets.detail_form import DetailForm

HEADERS = ["Order", "Action", "Source", "Destination", "Volume", "Duration", "Force", "Provenance", "Status"]
FORM_LABELS = {
    "order": "Order",
    "action": "Action",
    "source": "Source",
    "destination": "Destination",
    "volume": "Volume",
    "duration": "Duration",
    "force": "Force",
}


class _SamplePrepTableModel(QAbstractTableModel):
    def __init__(self, vm: SamplePrepScreenViewModel) -> None:
        super().__init__()
        self._vm = vm

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return len(self._vm.steps)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return len(HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        step = self._vm.steps[index.row()]
        row = step.to_table_row(index.row())
        if role == Qt.DisplayRole:
            return row[index.column()]
        if role == Qt.BackgroundRole and index.column() == len(HEADERS) - 1 and not step.is_valid:
            return Qt.GlobalColor.yellow
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()


class SamplePrepView(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        app_state: AppState | None = None,
        merge_service: MergeServiceAdapter | None = None,
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = SamplePrepScreenViewModel(app_state or AppState(), merge_service or MergeServiceAdapter())
        self._on_state_changed = on_state_changed

        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.delete_btn = QPushButton("Delete")
        self.up_btn = QPushButton("Up")
        self.down_btn = QPushButton("Down")
        self.duplicate_btn = QPushButton("Duplicate")
        for btn in [self.add_btn, self.delete_btn, self.up_btn, self.down_btn, self.duplicate_btn]:
            actions.addWidget(btn)
        layout.addLayout(actions)

        splitter = QSplitter(self)
        self.table = QTableView(self)
        self.table_model = _SamplePrepTableModel(self._vm)
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.table)

        self.detail = DetailForm([FORM_LABELS[name] for name in FIELD_ORDER], self)
        detail_wrap = QWidget(self)
        detail_layout = QFormLayout(detail_wrap)
        detail_layout.addRow(self.detail)
        self.provenance_labels: dict[str, QLabel] = {}
        self.reset_buttons: dict[str, QPushButton] = {}
        for name in FIELD_ORDER:
            prov = QLabel("", self)
            reset = QPushButton("Reset", self)
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(prov)
            row_layout.addStretch(1)
            row_layout.addWidget(reset)
            detail_layout.addRow("", row)
            self.provenance_labels[name] = prov
            self.reset_buttons[name] = reset
        splitter.addWidget(detail_wrap)
        layout.addWidget(splitter)

        self.add_btn.clicked.connect(self._add_step)
        self.delete_btn.clicked.connect(self._delete_step)
        self.up_btn.clicked.connect(self._move_up)
        self.down_btn.clicked.connect(self._move_down)
        self.duplicate_btn.clicked.connect(self._duplicate_step)
        self.table.selectionModel().selectionChanged.connect(self._select_from_table)
        for name in FIELD_ORDER:
            self.detail.inputs[FORM_LABELS[name]].editingFinished.connect(lambda n=name: self._update_field(n))
            self.reset_buttons[name].clicked.connect(lambda _=False, n=name: self._reset_field(n))

        self._refresh_all()

    def _current_step_id(self) -> str | None:
        return self._vm.selected_step_id

    def _select_from_table(self) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        step = self._vm.steps[indexes[0].row()]
        self._vm.select_step(step.step_id)
        self._refresh_detail()

    def _add_step(self) -> None:
        step_id = self._vm.add_step()
        self._refresh_all(select_step=step_id)
        self._notify_state_changed()

    def _delete_step(self) -> None:
        step_id = self._current_step_id()
        if step_id:
            self._vm.delete_step(step_id)
            self._refresh_all(select_step=self._vm.selected_step_id)
            self._notify_state_changed()

    def _move_up(self) -> None:
        step_id = self._current_step_id()
        if step_id:
            self._vm.move_up(step_id)
            self._refresh_all(select_step=step_id)
            self._notify_state_changed()

    def _move_down(self) -> None:
        step_id = self._current_step_id()
        if step_id:
            self._vm.move_down(step_id)
            self._refresh_all(select_step=step_id)
            self._notify_state_changed()

    def _duplicate_step(self) -> None:
        step_id = self._current_step_id()
        if step_id:
            new_id = self._vm.duplicate_step(step_id)
            self._refresh_all(select_step=new_id)
            self._notify_state_changed()

    def _update_field(self, field: str) -> None:
        step_id = self._current_step_id()
        if not step_id:
            return
        self._vm.update_field(step_id, field, self.detail.inputs[FORM_LABELS[field]].text())
        self._refresh_all(select_step=step_id)
        self._notify_state_changed()

    def _reset_field(self, field: str) -> None:
        step_id = self._current_step_id()
        if not step_id:
            return
        self._vm.reset_field(step_id, field)
        self._refresh_all(select_step=step_id)
        self._notify_state_changed()

    def _refresh_all(self, *, select_step: str | None = None) -> None:
        self.table_model.refresh()
        chosen = select_step or self._vm.selected_step_id
        if chosen:
            for row, step in enumerate(self._vm.steps):
                if step.step_id == chosen:
                    self.table.selectRow(row)
                    self._vm.select_step(step.step_id)
                    break
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        step = self._vm.selected_step()
        for name in FIELD_ORDER:
            edit = self.detail.inputs[FORM_LABELS[name]]
            if step is None:
                edit.setText("")
                edit.setStyleSheet("")
                self.provenance_labels[name].setText("")
                continue
            field = step.fields[name]
            edit.setText(field.value)
            edit.setStyleSheet("border: 1px solid #cc0000;" if not field.is_valid else "")
            self.provenance_labels[name].setText(f"[{field.provenance or 'manual'} | {field.status}]")

    def _notify_state_changed(self) -> None:
        if self._on_state_changed:
            self._on_state_changed()

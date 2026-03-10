from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QHeaderView, QTableView


class SimpleEntityTableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[str]] | None = None) -> None:
        super().__init__()
        self.headers = headers
        self.rows = rows or []

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: N802
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.rows[index.row()][index.column()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None


class EntityTable(QTableView):
    def set_table_data(self, headers: list[str], rows: list[list[str]]) -> None:
        self.setModel(SimpleEntityTableModel(headers, rows))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)

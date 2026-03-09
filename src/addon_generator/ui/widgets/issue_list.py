from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from addon_generator.ui.models.issue_view_model import IssueViewModel


class IssueList(QListWidget):
    issue_selected = Signal(IssueViewModel)

    def set_issues(self, issues: list[IssueViewModel]) -> None:
        self.clear()
        for issue in issues:
            item = QListWidgetItem(f"[{issue.severity}] {issue.code}: {issue.summary}")
            item.setData(32, issue)
            self.addItem(item)

    def mouseReleaseEvent(self, event):  # noqa: N802
        super().mouseReleaseEvent(event)
        item = self.currentItem()
        if item:
            issue = item.data(32)
            if issue:
                self.issue_selected.emit(issue)

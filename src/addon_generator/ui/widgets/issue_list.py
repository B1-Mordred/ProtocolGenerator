from __future__ import annotations

from collections import defaultdict
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from addon_generator.ui.models.issue_view_model import IssueViewModel


class IssueList(QWidget):
    issue_selected = Signal(IssueViewModel)
    issue_navigation_requested = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._issues: list[IssueViewModel] = []

        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.severity_filter = QComboBox(self)
        self.severity_filter.addItems(["all", "error", "warning", "info"])
        self.category_filter = QComboBox(self)
        self.category_filter.addItem("all")
        self.search_filter = QLineEdit(self)
        self.search_filter.setPlaceholderText("Search code, summary, or context")

        toolbar.addWidget(self.severity_filter)
        toolbar.addWidget(self.category_filter)
        toolbar.addWidget(self.search_filter)
        root.addLayout(toolbar)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Issues"])
        root.addWidget(self.tree)

        self.severity_filter.currentTextChanged.connect(self._apply_filters)
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        self.search_filter.textChanged.connect(self._apply_filters)
        self.tree.itemSelectionChanged.connect(self._emit_selected_issue)

    def set_issues(self, issues: list[IssueViewModel]) -> None:
        self._issues = list(issues)
        categories = sorted({issue.category or "General" for issue in self._issues})
        current = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("all")
        self.category_filter.addItems(categories)
        if current and self.category_filter.findText(current) >= 0:
            self.category_filter.setCurrentText(current)
        self.category_filter.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self) -> None:
        severity = self.severity_filter.currentText().strip().lower()
        category = self.category_filter.currentText().strip()
        search = self.search_filter.text().strip().lower()

        grouped: dict[str, list[IssueViewModel]] = defaultdict(list)
        for issue in self._issues:
            if severity != "all" and issue.severity.lower() != severity:
                continue
            issue_category = issue.category or "General"
            if category.lower() != "all" and issue_category != category:
                continue
            haystack = f"{issue.code} {issue.summary} {issue.entity_context}".lower()
            if search and search not in haystack:
                continue
            grouped[issue_category].append(issue)

        self.tree.clear()
        for issue_category in sorted(grouped):
            issues = grouped[issue_category]
            group_item = QTreeWidgetItem([f"{issue_category} ({len(issues)})"])
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(group_item)
            for issue in issues:
                item = QTreeWidgetItem([f"[{issue.severity}] {issue.code}: {issue.summary}"])
                item.setData(0, 32, issue)
                group_item.addChild(item)
            group_item.setExpanded(True)

    def _emit_selected_issue(self) -> None:
        item = self.tree.currentItem()
        if not item:
            return
        issue = item.data(0, 32)
        if not issue:
            return
        self.issue_selected.emit(issue)
        self.issue_navigation_requested.emit(self._navigation_target_for_issue(issue))

    @staticmethod
    def _navigation_target_for_issue(issue: IssueViewModel) -> dict[str, Any]:
        if issue.navigation_target:
            return issue.navigation_target
        context = (issue.entity_context or "").lower()
        section_index = 6
        entity = issue.entity_context or "validation"
        if "method" in context:
            section_index = 0
            entity = "method"
        elif "assay" in context:
            section_index = 1
            entity = "assay"
        elif "analyte" in context:
            section_index = 2
            entity = "analyte"
        elif "sample" in context or "prep" in context:
            section_index = 3
            entity = "sample_prep"
        elif "dilution" in context:
            section_index = 4
            entity = "dilution"
        elif issue.section == "Import":
            section_index = 5
            entity = "import_review"
        return {"section_index": section_index, "entity": entity, "path": issue.entity_context}

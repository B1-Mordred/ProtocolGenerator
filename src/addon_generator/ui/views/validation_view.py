from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QSplitter, QVBoxLayout, QWidget

from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.state.validation_state import ValidationState
from addon_generator.ui.widgets.issue_list import IssueList


class ValidationView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.status_message = QLabel("Validation has not been run.", self)
        layout.addWidget(self.status_message)

        splitter = QSplitter(self)
        self.issues = IssueList(self)
        splitter.addWidget(self.issues)

        detail_widget = QWidget(self)
        detail_layout = QFormLayout(detail_widget)
        self.detail_code = QLabel("-")
        self.detail_severity = QLabel("-")
        self.detail_summary = QLabel("-")
        self.detail_context = QLabel("-")
        self.detail_provenance = QLabel("-")
        self.detail_recommended = QLabel("-")
        self.detail_navigation = QLabel("-")
        detail_layout.addRow("Code", self.detail_code)
        detail_layout.addRow("Severity", self.detail_severity)
        detail_layout.addRow("Summary", self.detail_summary)
        detail_layout.addRow("Entity Context", self.detail_context)
        detail_layout.addRow("Provenance", self.detail_provenance)
        detail_layout.addRow("Recommended Action", self.detail_recommended)
        detail_layout.addRow("Navigation Target", self.detail_navigation)
        splitter.addWidget(detail_widget)

        layout.addWidget(splitter)
        self.issues.issue_selected.connect(self.set_selected_issue)

    def set_validation_state(self, validation_state: ValidationState) -> None:
        if validation_state.stale:
            self.status_message.setText("Validation is out of date. Run validation before export.")
        elif validation_state.has_blockers:
            self.status_message.setText("Export blocked: validation errors must be resolved.")
        else:
            self.status_message.setText("Validation current: export is allowed.")

    def set_selected_issue(self, issue: IssueViewModel) -> None:
        nav = issue.navigation_target or self.issues._navigation_target_for_issue(issue)
        self.detail_code.setText(issue.code)
        self.detail_severity.setText(issue.severity)
        self.detail_summary.setText(issue.summary)
        self.detail_context.setText(issue.entity_context or "-")
        self.detail_provenance.setText(issue.provenance or "-")
        self.detail_recommended.setText(issue.recommended_action or "-")
        self.detail_navigation.setText(f"section={nav.get('section_index')} entity={nav.get('entity')}")

from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.views.validation_view import ValidationView
from addon_generator.ui.widgets.issue_list import IssueList


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _issues() -> list[IssueViewModel]:
    return [
        IssueViewModel(code="M-1", severity="error", summary="Method id missing", category="Method", entity_context="method"),
        IssueViewModel(code="A-1", severity="warning", summary="Assay label missing", category="Assays", entity_context="assay/a1"),
        IssueViewModel(code="D-1", severity="error", summary="Dilution invalid", category="Dilutions", entity_context="dilution/d1"),
    ]


def test_issue_list_groups_and_counts(qapp) -> None:
    widget = IssueList()
    widget.set_issues(_issues())

    assert widget.tree.topLevelItemCount() == 3
    labels = [widget.tree.topLevelItem(i).text(0) for i in range(widget.tree.topLevelItemCount())]
    assert "Method (1)" in labels
    assert "Assays (1)" in labels


def test_issue_list_filters_and_search(qapp) -> None:
    widget = IssueList()
    widget.set_issues(_issues())

    widget.severity_filter.setCurrentText("warning")
    assert widget.tree.topLevelItemCount() == 1
    assert widget.tree.topLevelItem(0).text(0) == "Assays (1)"

    widget.severity_filter.setCurrentText("all")
    widget.category_filter.setCurrentText("Dilutions")
    assert widget.tree.topLevelItemCount() == 1

    widget.category_filter.setCurrentText("all")
    widget.search_filter.setText("method id")
    assert widget.tree.topLevelItemCount() == 1
    assert widget.tree.topLevelItem(0).text(0) == "Method (1)"


def test_issue_click_emits_navigation_target(qapp) -> None:
    widget = IssueList()
    widget.set_issues(_issues())

    payload = {}
    widget.issue_navigation_requested.connect(lambda jump: payload.update(jump))

    method_group = widget.tree.topLevelItem(2)
    method_child = method_group.child(0)
    widget.tree.setCurrentItem(method_child)

    assert payload["section_index"] == 0
    assert payload["entity"] == "method"


def test_validation_view_status_message_uses_validation_state(qapp) -> None:
    view = ValidationView()
    view.set_validation_state(type("State", (), {"stale": True, "has_blockers": False})())
    assert "out of date" in view.status_message.text().lower()

    view.set_validation_state(type("State", (), {"stale": False, "has_blockers": True})())
    assert "export blocked" in view.status_message.text().lower()

from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.ui.widgets.field_help_panel import FieldHelpPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_field_help_panel_initializes_with_title_and_details(qapp) -> None:
    panel = FieldHelpPanel("Field Help", "Select a field to view provenance and validation context.")

    assert panel.text() == "Field Help\n\nSelect a field to view provenance and validation context."

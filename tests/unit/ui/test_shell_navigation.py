from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.__about__ import __app_name__
from addon_generator.ui.shell import MainShell


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_shell_navigation_switches_sections(qapp) -> None:
    shell = MainShell()
    shell.sidebar.setCurrentRow(3)
    assert shell.stack.currentIndex() == 3
    assert shell.app_state.editor_state.selected_section_index == 3
    shell.sidebar.setCurrentRow(8)
    assert shell.stack.currentIndex() == 8
    assert shell.app_state.editor_state.selected_section_index == 8


def test_shell_sidebar_badges_refresh_when_counts_change(qapp) -> None:
    shell = MainShell()

    shell.app_state.editor_state.effective_values = {
        "hidden_vocab": {"SamplePrepAction": ["Mix"]},
        "method": {"method_id": "", "method_version": "1"},
    }
    shell.app_state.editor_state.sample_prep_overrides = [
        {
            "order": "",
            "action": "Bad",
            "source": "A",
            "destination": "",
            "volume": "1",
            "duration": "1",
            "force": "1",
        }
    ]
    shell.app_state.editor_state.dilution_overrides = [
        {"name": "D1", "buffer1_ratio": "x", "buffer2_ratio": "", "buffer3_ratio": "3"}
    ]
    shell.app_state.editor_state.unresolved_conflicts = {
        "sample_prep.steps.0.action": [{}],
        "dilution_schemes.0.buffer1_ratio": [{}],
        "method.method_id": [{}],
    }

    shell._refresh_status()
    assert shell.sidebar.item(3).text().endswith("(4)")
    assert shell.sidebar.item(4).text().endswith("(3)")
    assert shell.sidebar.item(5).text().endswith("(4)")

    shell.app_state.editor_state.sample_prep_overrides = []
    shell.app_state.editor_state.dilution_overrides = []
    shell.app_state.editor_state.unresolved_conflicts = {}
    shell._refresh_status()

    assert shell.sidebar.item(3).text() == "Sample Prep"
    assert shell.sidebar.item(4).text() == "Dilutions"
    assert shell.sidebar.item(5).text().endswith("(2)")


def test_shell_window_title_uses_about_metadata(qapp) -> None:
    shell = MainShell()

    assert shell.windowTitle() == __app_name__

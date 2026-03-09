from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

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

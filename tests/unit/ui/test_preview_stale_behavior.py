from __future__ import annotations

from addon_generator.ui.state.app_state import AppState


def test_preview_starts_stale() -> None:
    app_state = AppState()
    assert app_state.preview_state.stale is True
    assert app_state.validation_state.stale is True

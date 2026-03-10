from __future__ import annotations

from addon_generator.ui.models.issue_view_model import IssueViewModel
from addon_generator.ui.state.app_state import AppState


def test_app_state_badges_aggregate_editor_issues_and_conflicts() -> None:
    state = AppState()
    state.editor_state.effective_values = {
        "hidden_vocab": {"SamplePrepAction": ["Mix"]},
        "method": {"method_id": "", "method_version": "1"},
    }
    state.editor_state.sample_prep_overrides = [
        {
            "order": "",
            "action": "Nope",
            "source": "Tube A",
            "destination": "",
            "volume": "1",
            "duration": "1",
            "force": "1",
        }
    ]
    state.editor_state.dilution_overrides = [
        {"name": "D1", "buffer1_ratio": "x", "buffer2_ratio": "", "buffer3_ratio": "3"}
    ]
    state.editor_state.unresolved_conflicts = {
        "sample_prep.steps.0.action": [{}],
        "dilution_schemes.0.buffer1_ratio": [{}],
        "method.method_id": [{}],
    }
    state.validation_state.issues = [IssueViewModel(code="E", severity="error", summary="bad")]
    state.validation_state.severity_counts = {"error": 1, "warning": 0, "info": 0}

    assert state.sample_prep_issue_count == 3
    assert state.sample_prep_conflict_count == 1
    assert state.sample_prep_badge_count == 4

    assert state.dilutions_issue_count == 2
    assert state.dilutions_conflict_count == 1
    assert state.dilutions_badge_count == 3

    assert state.import_review_unresolved_required_count == 1
    assert state.import_review_badge_count == 4
    assert state.validation_badge_count == 1


def test_import_review_required_count_defaults_when_effective_method_missing() -> None:
    state = AppState()
    state.editor_state.effective_values = {}
    assert state.import_review_unresolved_required_count == 2


def test_app_state_status_dimensions_and_badge_contributions() -> None:
    state = AppState()

    assert state.validation_is_stale is True
    assert state.validation_is_current is False
    assert state.preview_is_stale is True
    assert state.preview_is_current is False
    assert state.export_is_ready is False
    assert state.export_is_blocked is True
    assert state.draft_is_dirty is False
    assert state.draft_is_saved is True
    assert state.preview_badge_contribution == 1
    assert state.export_badge_contribution == 1
    assert state.draft_badge_contribution == 0

    state.validation_state.stale = False
    state.validation_state.export_blocked = False
    state.preview_state.stale = False
    state.draft_state.dirty = True

    assert state.validation_is_stale is False
    assert state.validation_is_current is True
    assert state.preview_is_stale is False
    assert state.preview_is_current is True
    assert state.export_is_ready is True
    assert state.export_is_blocked is False
    assert state.draft_is_dirty is True
    assert state.draft_is_saved is False
    assert state.preview_badge_contribution == 0
    assert state.export_badge_contribution == 0
    assert state.draft_badge_contribution == 1

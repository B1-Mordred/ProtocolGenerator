from __future__ import annotations

from dataclasses import dataclass, field

SAMPLE_PREP_REQUIRED_FIELDS = {"order", "action", "source", "destination"}
DILUTION_FIELDS = ("name", "buffer1_ratio", "buffer2_ratio", "buffer3_ratio")
RATIO_FIELDS = {"buffer1_ratio", "buffer2_ratio", "buffer3_ratio"}

from addon_generator.ui.state.draft_state import DraftState
from addon_generator.ui.state.editor_state import EditorState
from addon_generator.ui.state.import_state import ImportState
from addon_generator.ui.state.preview_state import PreviewState
from addon_generator.ui.state.validation_state import ValidationState


@dataclass(slots=True)
class AppState:
    import_state: ImportState = field(default_factory=ImportState)
    editor_state: EditorState = field(default_factory=EditorState)
    validation_state: ValidationState = field(default_factory=ValidationState)
    preview_state: PreviewState = field(default_factory=PreviewState)
    draft_state: DraftState = field(default_factory=DraftState)

    @property
    def sample_prep_issue_count(self) -> int:
        valid_actions = {
            str(v).strip().casefold()
            for v in self.editor_state.effective_values.get("hidden_vocab", {}).get("SamplePrepAction", [])
            if str(v).strip()
        }
        issue_count = 0
        for step in self.editor_state.sample_prep_overrides:
            action = str(step.get("action") or "").strip()
            for field in SAMPLE_PREP_REQUIRED_FIELDS:
                if not str(step.get(field) or "").strip():
                    issue_count += 1
            if action and valid_actions and action.casefold() not in valid_actions:
                issue_count += 1
        return issue_count

    @property
    def sample_prep_conflict_count(self) -> int:
        return sum(1 for path in self.editor_state.unresolved_conflicts if path.startswith("sample_prep"))

    @property
    def sample_prep_badge_count(self) -> int:
        return self.sample_prep_issue_count + self.sample_prep_conflict_count

    @property
    def dilutions_issue_count(self) -> int:
        issue_count = 0
        for scheme in self.editor_state.dilution_overrides:
            for field in DILUTION_FIELDS:
                value = str(scheme.get(field) or "").strip()
                if not value:
                    issue_count += 1
                    continue
                if field in RATIO_FIELDS and (not value.isdigit() or int(value) <= 0):
                    issue_count += 1
        return issue_count

    @property
    def dilutions_conflict_count(self) -> int:
        return sum(1 for path in self.editor_state.unresolved_conflicts if path.startswith("dilution"))

    @property
    def dilutions_badge_count(self) -> int:
        return self.dilutions_issue_count + self.dilutions_conflict_count

    @property
    def import_review_unresolved_required_count(self) -> int:
        effective_method = self.editor_state.effective_values.get("method", {})
        if not isinstance(effective_method, dict):
            return 2
        missing = 0
        for key in ("method_id", "method_version"):
            if not str(effective_method.get(key) or "").strip():
                missing += 1
        return missing

    @property
    def import_review_badge_count(self) -> int:
        return len(self.editor_state.unresolved_conflicts) + self.import_review_unresolved_required_count

    @property
    def validation_badge_count(self) -> int:
        return len(self.validation_state.issues)

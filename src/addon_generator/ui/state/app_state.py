from __future__ import annotations

from dataclasses import dataclass, field

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

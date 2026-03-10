from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Any

from addon_generator.input_models.dtos import SamplePrepStepInputDTO
from addon_generator.mapping.normalizers import normalize_for_matching
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState

FIELD_ORDER = ["order", "action", "source", "destination", "volume", "duration", "force"]
REQUIRED_FIELDS = {"order", "action", "source", "destination"}


@dataclass(slots=True)
class SamplePrepFieldState:
    value: str = ""
    provenance: str = ""
    status: str = "ok"
    is_valid: bool = True


@dataclass(slots=True)
class SamplePrepStepState:
    step_id: str
    fields: dict[str, SamplePrepFieldState] = field(default_factory=dict)
    row_status: str = "ok"
    is_valid: bool = True

    def to_table_row(self, index: int) -> list[str]:
        values = [self.fields[name].value for name in FIELD_ORDER]
        provenance_summary = ", ".join(sorted({f.provenance for f in self.fields.values() if f.provenance})) or "manual"
        return [str(index + 1), *values[1:], provenance_summary, self.row_status]


class SamplePrepScreenViewModel:
    def __init__(self, app_state: AppState, merge_adapter: MergeServiceAdapter) -> None:
        self._app_state = app_state
        self._merge_adapter = merge_adapter
        self.steps: list[SamplePrepStepState] = []
        self.selected_step_id: str | None = None
        self._counter = count(1)
        self._valid_actions: set[str] = set()
        self.load_from_state()

    def load_from_state(self) -> None:
        merged = self._merge_adapter.recompute(self._app_state) if self._app_state.import_state.bundles else None
        self._valid_actions = {
            normalize_for_matching(v)
            for v in (merged.hidden_vocab.get("SamplePrepAction", []) if merged else [])
            if str(v).strip()
        }
        overrides = self._app_state.editor_state.sample_prep_overrides or self._app_state.editor_state.manual_overrides.get("sample_prep.steps")
        if isinstance(overrides, list):
            source_steps = overrides
            provenance = "manual"
        elif merged is not None:
            source_steps = [self._dto_to_payload(step) for step in merged.sample_prep_steps]
            if not source_steps and self._app_state.import_state.bundles:
                source_steps = [
                    self._dto_to_payload(step)
                    for bundle in self._app_state.import_state.bundles
                    for step in bundle.sample_prep_steps
                ]
            provenance = "import"
        else:
            source_steps = []
            provenance = ""

        self.steps = []
        for payload in source_steps:
            self.steps.append(self._make_step(payload, default_provenance=provenance))
        if self.steps:
            self.selected_step_id = self._app_state.editor_state.selected_sample_prep_step_id or self.steps[0].step_id
        else:
            self.selected_step_id = None
        self._validate()

    def add_step(self) -> str:
        step = self._make_step({}, default_provenance="manual")
        self.steps.append(step)
        self.selected_step_id = step.step_id
        self._app_state.editor_state.selected_sample_prep_step_id = step.step_id
        self._commit()
        return step.step_id

    def delete_step(self, step_id: str) -> None:
        self.steps = [step for step in self.steps if step.step_id != step_id]
        if self.selected_step_id == step_id:
            self.selected_step_id = self.steps[0].step_id if self.steps else None
        self._commit()

    def move_up(self, step_id: str) -> None:
        idx = self._index_of(step_id)
        if idx <= 0:
            return
        self.steps[idx - 1], self.steps[idx] = self.steps[idx], self.steps[idx - 1]
        self._commit()

    def move_down(self, step_id: str) -> None:
        idx = self._index_of(step_id)
        if idx < 0 or idx >= len(self.steps) - 1:
            return
        self.steps[idx + 1], self.steps[idx] = self.steps[idx], self.steps[idx + 1]
        self._commit()

    def duplicate_step(self, step_id: str) -> str | None:
        idx = self._index_of(step_id)
        if idx < 0:
            return None
        clone_payload = {name: self.steps[idx].fields[name].value for name in FIELD_ORDER}
        clone = self._make_step(clone_payload, default_provenance="manual")
        self.steps.insert(idx + 1, clone)
        self.selected_step_id = clone.step_id
        self._commit()
        return clone.step_id

    def update_field(self, step_id: str, field: str, value: str) -> None:
        step = self._get_step(step_id)
        if step is None or field not in FIELD_ORDER:
            return
        field_state = step.fields[field]
        field_state.value = value
        field_state.provenance = "manual"
        self._commit()

    def reset_field(self, step_id: str, field: str) -> None:
        step = self._get_step(step_id)
        if step is None or field not in FIELD_ORDER:
            return
        step.fields[field] = SamplePrepFieldState(value="", provenance="", status="ok", is_valid=True)
        self._commit()

    def select_step(self, step_id: str | None) -> None:
        self.selected_step_id = step_id if step_id and self._index_of(step_id) >= 0 else None
        self._app_state.editor_state.selected_sample_prep_step_id = self.selected_step_id

    def selected_step(self) -> SamplePrepStepState | None:
        return self._get_step(self.selected_step_id) if self.selected_step_id else None

    def _commit(self) -> None:
        self._validate()
        self._app_state.editor_state.sample_prep_overrides = [
            {name: step.fields[name].value for name in FIELD_ORDER} for step in self.steps
        ]
        self._app_state.editor_state.manual_overrides["sample_prep.steps"] = list(self._app_state.editor_state.sample_prep_overrides)
        for step in self.steps:
            for name in FIELD_ORDER:
                if step.fields[name].provenance == "manual":
                    self._app_state.editor_state.mark_manual_edit(f"sample_prep.steps.{step.step_id}.{name}")
        self._merge_adapter.recompute(self._app_state)

    def _validate(self) -> None:
        for step in self.steps:
            row_issues: list[str] = []
            for name in FIELD_ORDER:
                fstate = step.fields[name]
                missing_required = name in REQUIRED_FIELDS and not fstate.value.strip()
                invalid_action = name == "action" and fstate.value.strip() and self._valid_actions and normalize_for_matching(fstate.value) not in self._valid_actions
                fstate.is_valid = not (missing_required or invalid_action)
                if missing_required:
                    fstate.status = "required"
                    row_issues.append(f"missing {name}")
                elif invalid_action:
                    fstate.status = "invalid-action"
                    row_issues.append("invalid action")
                else:
                    fstate.status = "ok"
            step.is_valid = not row_issues
            step.row_status = "ok" if step.is_valid else "; ".join(row_issues)

    def _make_step(self, payload: dict[str, Any], *, default_provenance: str) -> SamplePrepStepState:
        step_id = payload.get("step_id") or f"step-{next(self._counter)}"
        return SamplePrepStepState(
            step_id=step_id,
            fields={
                name: SamplePrepFieldState(value=str(payload.get(name, "") or ""), provenance=default_provenance)
                for name in FIELD_ORDER
            },
        )

    def _dto_to_payload(self, step: SamplePrepStepInputDTO) -> dict[str, str]:
        metadata = step.metadata or {}
        return {
            "order": str(metadata.get("order", "") or ""),
            "action": str(step.label or metadata.get("raw_action", "") or ""),
            "source": str(metadata.get("source", "") or ""),
            "destination": str(metadata.get("destination", "") or ""),
            "volume": str(metadata.get("volume", "") or ""),
            "duration": str(metadata.get("duration", "") or ""),
            "force": str(metadata.get("force", "") or ""),
        }

    def _index_of(self, step_id: str | None) -> int:
        if not step_id:
            return -1
        for idx, step in enumerate(self.steps):
            if step.step_id == step_id:
                return idx
        return -1

    def _get_step(self, step_id: str | None) -> SamplePrepStepState | None:
        idx = self._index_of(step_id)
        return self.steps[idx] if idx >= 0 else None

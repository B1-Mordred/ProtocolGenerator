from __future__ import annotations

from dataclasses import asdict

from addon_generator.input_models.dtos import InputDTOBundle, SamplePrepStepInputDTO
from addon_generator.services.input_merge_service import InputMergeService
from addon_generator.ui.state.app_state import AppState


class MergeServiceAdapter:
    def __init__(self) -> None:
        self._merge = InputMergeService()

    def recompute(self, app_state: AppState) -> InputDTOBundle:
        merged, report = self._merge.merge(app_state.import_state.bundles)
        for key, value in app_state.editor_state.manual_overrides.items():
            self._apply_override(merged, key, value)
        app_state.editor_state.effective_values = asdict(merged)
        app_state.editor_state.unresolved_conflicts = report.get("conflicts", {})
        app_state.validation_state.stale = True
        app_state.preview_state.stale = True
        return merged

    def _apply_override(self, merged: InputDTOBundle, key: str, value: object) -> None:
        if key.startswith("method.") and merged.method:
            setattr(merged.method, key.split(".", 1)[1], value)
            return
        if key == "sample_prep.steps" and isinstance(value, list):
            merged.sample_prep_steps = []
            for idx, step in enumerate(value, start=1):
                if not isinstance(step, dict):
                    continue
                step_order = str(step.get("order") or idx)
                merged.sample_prep_steps.append(
                    SamplePrepStepInputDTO(
                        key=f"sampleprep:{step_order}:{idx}",
                        label=str(step.get("action") or "") or None,
                        metadata={
                            "order": step_order,
                            "raw_action": str(step.get("action") or ""),
                            "source": str(step.get("source") or ""),
                            "destination": str(step.get("destination") or ""),
                            "volume": str(step.get("volume") or ""),
                            "duration": str(step.get("duration") or ""),
                            "force": str(step.get("force") or ""),
                        },
                    )
                )

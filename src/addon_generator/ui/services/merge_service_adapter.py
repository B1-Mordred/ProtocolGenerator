from __future__ import annotations

from dataclasses import asdict
from typing import Any

from addon_generator.input_models.dtos import DilutionSchemeInputDTO, InputDTOBundle, SamplePrepStepInputDTO
from addon_generator.services.input_merge_service import InputMergeService
from addon_generator.ui.state.app_state import AppState


class MergeServiceAdapter:
    def __init__(self) -> None:
        self._merge = InputMergeService()

    def recompute(self, app_state: AppState) -> InputDTOBundle:
        merged, report = self._merge.merge(app_state.import_state.bundles)
        app_state.import_state.imported_sample_prep_dtos = [self._sample_prep_to_payload(step) for step in merged.sample_prep_steps]
        app_state.import_state.imported_dilution_dtos = [self._dilution_to_payload(scheme) for scheme in merged.dilution_schemes]

        for key, value in app_state.editor_state.manual_overrides.items():
            self._apply_override(merged, key, value)

        merged.sample_prep_steps = self._effective_sample_prep_steps(app_state, merged)
        merged.dilution_schemes = self._effective_dilution_schemes(app_state, merged)

        app_state.editor_state.effective_values = asdict(merged)
        app_state.editor_state.unresolved_conflicts = self._conflicts_by_path(report.get("conflicts", []))
        app_state.import_state.conflict_summary = {
            "total": len(report.get("conflicts", [])),
            "unresolved": len(app_state.editor_state.unresolved_conflicts),
        }
        app_state.validation_state.stale = True
        app_state.preview_state.stale = True
        return merged

    def flatten_import_review_rows(self, app_state: AppState) -> list[dict[str, Any]]:
        imported = self._flatten_bundle(asdict(app_state.import_state.bundles[-1])) if app_state.import_state.bundles else {}
        effective = self._flatten_bundle(app_state.editor_state.effective_values)
        keys = sorted(set(imported) | set(effective) | set(app_state.import_state.provenance) | set(app_state.editor_state.manual_overrides))
        return [
            {
                "path": key,
                "imported": imported.get(key),
                "effective": effective.get(key),
                "has_override": key in app_state.editor_state.manual_overrides,
                "has_conflict": key in app_state.editor_state.unresolved_conflicts,
            }
            for key in keys
        ]

    def accept_imported_value(self, app_state: AppState, path: str) -> None:
        imported = self._flatten_bundle(asdict(app_state.import_state.bundles[-1])) if app_state.import_state.bundles else {}
        app_state.editor_state.set_override(path, imported.get(path))
        app_state.import_state.review_resolutions[path] = "accepted_imported"
        self.recompute(app_state)

    def keep_override_value(self, app_state: AppState, path: str) -> None:
        if path not in app_state.editor_state.manual_overrides:
            app_state.editor_state.set_override(path, self._flatten_bundle(app_state.editor_state.effective_values).get(path))
        app_state.import_state.review_resolutions[path] = "kept_override"
        self.recompute(app_state)

    def revert_default_value(self, app_state: AppState, path: str) -> None:
        app_state.editor_state.clear_override(path)
        app_state.import_state.review_resolutions[path] = "reverted_default"
        self.recompute(app_state)

    def _effective_sample_prep_steps(self, app_state: AppState, merged: InputDTOBundle) -> list[SamplePrepStepInputDTO]:
        overrides = app_state.editor_state.sample_prep_overrides or app_state.editor_state.manual_overrides.get("sample_prep.steps")
        if not isinstance(overrides, list):
            return merged.sample_prep_steps
        out: list[SamplePrepStepInputDTO] = []
        for idx, step in enumerate(overrides, start=1):
            if not isinstance(step, dict):
                continue
            step_order = str(step.get("order") or idx)
            out.append(
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
        return out

    def _effective_dilution_schemes(self, app_state: AppState, merged: InputDTOBundle) -> list[DilutionSchemeInputDTO]:
        overrides = app_state.editor_state.dilution_overrides or app_state.editor_state.manual_overrides.get("dilution_schemes")
        if not isinstance(overrides, list):
            return merged.dilution_schemes
        out: list[DilutionSchemeInputDTO] = []
        for idx, scheme in enumerate(overrides, start=1):
            if not isinstance(scheme, dict):
                continue
            buffer1 = str(scheme.get("buffer1_ratio") or "").strip()
            buffer2 = str(scheme.get("buffer2_ratio") or "").strip()
            buffer3 = str(scheme.get("buffer3_ratio") or "").strip()
            ratio_parts = [part for part in (buffer1, buffer2, buffer3) if part]
            out.append(
                DilutionSchemeInputDTO(
                    key=f"dilution:{idx}",
                    label=str(scheme.get("name") or "") or None,
                    metadata={
                        "name": str(scheme.get("name") or ""),
                        "buffer1_ratio": buffer1,
                        "buffer2_ratio": buffer2,
                        "buffer3_ratio": buffer3,
                        "ratio": ":".join(ratio_parts),
                    },
                )
            )
        return out

    def _apply_override(self, merged: InputDTOBundle, key: str, value: object) -> None:
        if key.startswith("method.") and merged.method:
            setattr(merged.method, key.split(".", 1)[1], value)
            return
        if key == "source_name":
            merged.source_name = str(value) if value is not None else None
            return
        if key == "method_information_overrides" and isinstance(value, dict):
            merged.method_information_overrides = dict(value)
            return

    @staticmethod
    def _conflicts_by_path(conflicts: list[dict[str, Any]]) -> dict[str, list[Any]]:
        out: dict[str, list[Any]] = {}
        for conflict in conflicts:
            path = str(conflict.get("path") or "")
            if not path:
                continue
            out.setdefault(path, []).append(conflict)
        return out

    def _sample_prep_to_payload(self, step: SamplePrepStepInputDTO) -> dict[str, str]:
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

    def _dilution_to_payload(self, scheme: DilutionSchemeInputDTO) -> dict[str, str]:
        metadata = scheme.metadata or {}
        parts = [str(p).strip() for p in str(metadata.get("ratio", "") or "").split(":") if str(p).strip()]
        return {
            "name": str(scheme.label or metadata.get("name", "") or ""),
            "buffer1_ratio": str(metadata.get("buffer1_ratio") or (parts[0] if len(parts) >= 1 else "") or ""),
            "buffer2_ratio": str(metadata.get("buffer2_ratio") or (parts[1] if len(parts) >= 2 else "") or ""),
            "buffer3_ratio": str(metadata.get("buffer3_ratio") or (parts[2] if len(parts) >= 3 else "") or ""),
        }

    def _flatten_bundle(self, payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                out.update(self._flatten_bundle(value, path))
            elif isinstance(value, list):
                continue
            else:
                out[path] = value
        return out

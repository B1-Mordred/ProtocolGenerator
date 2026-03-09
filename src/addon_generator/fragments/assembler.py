from __future__ import annotations

import json
from typing import Any


class WorkflowAssembler:
    """Normalize fragment payloads into deterministic, schema-shaped workflow sections."""

    def assemble_sections(self, sections: dict[str, Any]) -> dict[str, Any]:
        assembled = dict(sections)
        if "AssayInformation" in assembled:
            assembled["AssayInformation"] = self.normalize_assay_information(assembled["AssayInformation"])
        if "LoadingWorkflowSteps" in assembled:
            assembled["LoadingWorkflowSteps"] = self.normalize_loading_steps(assembled["LoadingWorkflowSteps"])
        if "ProcessingWorkflowSteps" in assembled:
            assembled["ProcessingWorkflowSteps"] = self.normalize_processing_steps(assembled["ProcessingWorkflowSteps"])
        return assembled

    def normalize_assay_information(self, value: Any) -> list[dict[str, Any]]:
        items = [item for item in self._as_list(value) if isinstance(item, dict)]
        return self._ordered(items)

    def normalize_loading_steps(self, value: Any) -> list[dict[str, Any]]:
        steps = [dict(item) for item in self._as_list(value) if isinstance(item, dict)]
        normalized_steps: list[dict[str, Any]] = []
        for step in self._ordered(steps):
            step_name = step.get("StepName")
            step_type = step.get("StepType")
            if not (isinstance(step_name, str) and step_name.strip()) and not (isinstance(step_type, str) and step_type.strip()):
                continue
            params = step.get("StepParameters")
            if isinstance(params, dict) and params:
                step["StepParameters"] = params
            else:
                step.pop("StepParameters", None)
            normalized_steps.append(step)
        return normalized_steps

    def normalize_processing_steps(self, value: Any) -> list[dict[str, Any]]:
        groups = [dict(item) for item in self._as_list(value) if isinstance(item, dict)]
        if groups and all("GroupSteps" not in item for item in groups):
            if all(self._is_group_descriptor(item) for item in groups):
                return self._ordered([{"GroupDisplayName": item.get("GroupDisplayName")} for item in groups if isinstance(item.get("GroupDisplayName"), str) and item.get("GroupDisplayName", "").strip()])
            groups = [{"GroupDisplayName": "Default", "GroupSteps": groups}]

        normalized_groups: list[dict[str, Any]] = []
        for group in self._ordered(groups):
            group_steps = [dict(step) for step in self._as_list(group.get("GroupSteps")) if isinstance(step, dict)]
            if not group_steps:
                continue

            normalized_steps: list[dict[str, Any]] = []
            for step_index, step in enumerate(self._ordered(group_steps)):
                step.setdefault("StepType", step.get("StepName", "UnknownStep"))
                step["StepIndex"] = step_index
                step["StaticDurationInSeconds"] = int(step.get("StaticDurationInSeconds", 0) or 0)
                step["DynamicDurationInSeconds"] = int(step.get("DynamicDurationInSeconds", 0) or 0)
                params = step.get("StepParameters")
                if not isinstance(params, dict):
                    params = {}
                params.setdefault("StaticDurationInSeconds", step["StaticDurationInSeconds"])
                params.setdefault("DynamicDurationInSeconds", step["DynamicDurationInSeconds"])
                step["StepParameters"] = params
                normalized_steps.append(step)

            group_display_name = group.get("GroupDisplayName")
            normalized_groups.append(
                {
                    "GroupDisplayName": group_display_name if isinstance(group_display_name, str) and group_display_name.strip() else "Default",
                    "GroupIndex": 0,
                    "GroupSteps": normalized_steps,
                }
            )

        for idx, group in enumerate(normalized_groups):
            group["GroupIndex"] = idx
        return normalized_groups

    @staticmethod
    def _is_group_descriptor(item: dict[str, Any]) -> bool:
        keys = set(item)
        return "GroupDisplayName" in keys and keys.issubset({"GroupDisplayName", "GroupIndex"})

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    @staticmethod
    def _ordered(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        indexed = list(enumerate(values))
        indexed.sort(key=lambda item: (json.dumps(item[1], sort_keys=True, default=str), item[0]))
        return [value for _, value in indexed]

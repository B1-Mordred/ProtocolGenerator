from __future__ import annotations

import copy
from collections import Counter
from typing import Any

from addon_generator.domain.models import AddonModel


class DefaultDerivationService:
    """Infers protocol_defaults fragments from canonical assay/analyte metadata."""

    _ASSAY_FAMILY_LOADING_TEMPLATES: dict[str, list[dict[str, Any]]] = {
        "immunoassay": [
            {
                "StepType": "LoadMfxCarriers",
                "StepParameters": {
                    "BarcodeMask": "*",
                    "FullFilename": "immuno-loading-template",
                    "RequiredPlates": [],
                    "RequiredTipRacks": [],
                },
            }
        ],
        "chemistry": [
            {
                "StepType": "LoadMfxCarriers",
                "StepParameters": {
                    "BarcodeMask": "*",
                    "FullFilename": "chemistry-loading-template",
                    "RequiredPlates": [],
                    "RequiredTipRacks": [],
                },
            }
        ],
        "generic": [
            {
                "StepType": "LoadMfxCarriers",
                "StepParameters": {
                    "BarcodeMask": "*",
                    "FullFilename": "default-loading-template",
                    "RequiredPlates": [],
                    "RequiredTipRacks": [],
                },
            }
        ],
    }

    def derive_protocol_defaults(self, addon: AddonModel) -> dict[str, Any]:
        dominant_family = self._dominant_assay_family(addon)
        assay_defaults = self._derive_assay_information_defaults(addon)
        processing_templates = self._derive_processing_group_templates(addon)

        protocol_defaults: dict[str, Any] = {
            "assay_information": assay_defaults,
            "processing_workflow_steps": processing_templates,
        }

        loading_templates = self._ASSAY_FAMILY_LOADING_TEMPLATES.get(dominant_family)
        if loading_templates:
            protocol_defaults["loading_workflow_steps"] = copy.deepcopy(loading_templates)

        return {"protocol_defaults": protocol_defaults}

    def _derive_assay_information_defaults(self, addon: AddonModel) -> dict[str, Any]:
        kit_component_names = {
            str((assay.metadata or {}).get("component_name") or "").strip()
            for assay in addon.assays
        }
        has_calibrators = self._has_marker(addon, "calibrator")
        has_controls = self._has_marker(addon, "control")

        return {
            "DisplayName": "Assay",
            "MinimumNumberOfPatientSamplesOnFirstPlate": 0,
            "StopPreparationWithFailedCalibrator": has_calibrators,
            "StopPreparationWithFailedControl": has_controls,
            "ValidDurationInDays": 0,
            "DerivedComponentCount": len({name for name in kit_component_names if name}),
        }

    def _derive_processing_group_templates(self, addon: AddonModel) -> list[dict[str, Any]]:
        templates: list[dict[str, Any]] = []
        for idx, assay in enumerate(sorted(addon.assays, key=lambda item: item.key)):
            metadata = assay.metadata or {}
            display_name = (
                str(metadata.get("parameter_set_number") or "").strip()
                or str(metadata.get("component_name") or "").strip()
                or assay.protocol_display_name
                or assay.protocol_type
                or assay.key
            )
            assay_type = str(metadata.get("type") or "").strip()
            container_type = str(metadata.get("container_type") or "").strip()
            templates.append(
                {
                    "GroupDisplayName": display_name,
                    "GroupIndex": idx,
                    "GroupSteps": [
                        {
                            "StepIndex": 0,
                            "StepType": "UnloadHeaterShaker",
                            "StaticDurationInSeconds": 0,
                            "DynamicDurationInSeconds": 0,
                            "StepParameters": {
                                "KeepGripperTools": False,
                                "StaticDurationInSeconds": 0,
                                "DynamicDurationInSeconds": 0,
                                "DerivedAssayType": assay_type,
                                "DerivedContainerType": container_type,
                            },
                        }
                    ],
                }
            )

        if templates:
            return templates

        return [
            {
                "GroupDisplayName": "Default",
                "GroupIndex": 0,
                "GroupSteps": [
                    {
                        "StepIndex": 0,
                        "StepType": "UnloadHeaterShaker",
                        "StaticDurationInSeconds": 0,
                        "DynamicDurationInSeconds": 0,
                        "StepParameters": {
                            "KeepGripperTools": False,
                            "StaticDurationInSeconds": 0,
                            "DynamicDurationInSeconds": 0,
                        },
                    }
                ],
            }
        ]

    def _dominant_assay_family(self, addon: AddonModel) -> str:
        counts: Counter[str] = Counter()
        for assay in addon.assays:
            counts[self._infer_family_from_values(
                assay.protocol_type,
                assay.protocol_display_name,
                assay.xml_name,
                (assay.metadata or {}).get("type"),
                (assay.metadata or {}).get("container_type"),
            )] += 1
        for analyte in addon.analytes:
            counts[self._infer_family_from_values(analyte.assay_information_type)] += 1

        if not counts:
            return "generic"

        sorted_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        family, _ = sorted_counts[0]
        return family

    def _has_marker(self, addon: AddonModel, marker: str) -> bool:
        for assay in addon.assays:
            metadata = assay.metadata or {}
            candidates = [
                metadata.get("component_name"),
                metadata.get("type"),
                assay.protocol_type,
                assay.protocol_display_name,
            ]
            if any(marker in str(candidate or "").strip().lower() for candidate in candidates):
                return True
        return False

    def _infer_family_from_values(self, *values: Any) -> str:
        haystack = " ".join(str(value or "").strip().lower() for value in values if str(value or "").strip())
        if "immun" in haystack:
            return "immunoassay"
        if "chem" in haystack:
            return "chemistry"
        return "generic"

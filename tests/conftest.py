from __future__ import annotations

from pathlib import Path

import pytest

from protocol_generator_gui.schema_utils import load_schema


@pytest.fixture(scope="session")
def schema() -> dict:
    return load_schema(Path(__file__).resolve().parents[1] / "protocol.schema.json")


@pytest.fixture
def minimal_protocol() -> dict:
    return {
        "MethodInformation": {
            "Id": "m1",
            "DisplayName": "Method",
            "Version": "1",
            "MainTitle": "Main",
            "SubTitle": "Sub",
            "OrderNumber": "O-1",
            "MaximumNumberOfSamples": 1,
            "MaximumNumberOfProcessingCycles": 1,
            "MaximumNumberOfAssays": 1,
            "SamplesLayoutType": "SAMPLES_LAYOUT_COMBINED",
            "MethodInformationType": "REGULAR",
        },
        "AssayInformation": [
            {
                "Type": "A",
                "DisplayName": "Assay",
                "MinimumNumberOfPatientSamplesOnFirstPlate": 0,
                "StopPreparationWithFailedCalibrator": False,
                "StopPreparationWithFailedControl": False,
                "ValidDurationInDays": 0,
                "DilutionFactors": [
                    {
                        "DilutionFactor": "1x",
                        "IsUsed": True,
                        "AspirationVolumeEluate": 0,
                        "DispensationVolumeEluate": 0,
                        "DispensationVolumeDilutionBuffer1": 0,
                        "DispensationVolumeDilutionBuffer2": 0,
                        "DispensationVolumeDilutionBuffer3": 0,
                    }
                ],
                "CalibratorLayoutRules": [
                    {
                        "DisplayName": "C",
                        "Level": 0,
                        "PrependToPatientSamples": True,
                        "AppendToPatientSamples": False,
                        "FrequencyOfInterspersal": 0,
                        "OffsetOfInterspersal": 0,
                    }
                ],
                "ControlLayoutRules": [
                    {
                        "DisplayName": "K",
                        "Level": 0,
                        "PrependToPatientSamples": False,
                        "AppendToPatientSamples": True,
                        "FrequencyOfInterspersal": 0,
                        "OffsetOfInterspersal": 0,
                    }
                ],
            }
        ],
        "LoadingWorkflowSteps": [
            {
                "StepType": "LoadMfxCarriers",
                "StepParameters": {
                    "BarcodeMask": "*",
                    "FullFilename": "file",
                    "RequiredPlates": [
                        {
                            "LabwareType": "L",
                            "DisplayName": "D",
                            "ArticleNumber": "A",
                            "BarcodeMask": "B",
                            "FullFilename": "F",
                            "IsReusable": False,
                            "PlateControlType": "DWP",
                        }
                    ],
                    "RequiredTipRacks": [
                        {
                            "LabwareType": "L",
                            "DisplayName": "D",
                            "ArticleNumber": "A",
                            "BarcodeMask": "B",
                            "FullFilename": "F",
                        }
                    ],
                },
            }
        ],
        "ProcessingWorkflowSteps": [
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
        ],
    }

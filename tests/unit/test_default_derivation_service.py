from addon_generator.domain.models import AddonModel, AnalyteModel, AssayModel
from addon_generator.services.default_derivation_service import DefaultDerivationService


def test_default_derivation_service_inferrs_assay_processing_and_loading_templates() -> None:
    service = DefaultDerivationService()
    addon = AddonModel(
        assays=[
            AssayModel(
                key="assay:cal",
                protocol_type="Immuno",
                protocol_display_name="Calibrator Assay",
                metadata={
                    "component_name": "Calibrator A",
                    "parameter_set_number": "PS-01",
                    "type": "Calibrator",
                    "container_type": "Vial",
                },
            ),
            AssayModel(
                key="assay:ctrl",
                protocol_type="Immuno",
                protocol_display_name="Control Assay",
                metadata={
                    "component_name": "Control B",
                    "parameter_set_number": "PS-02",
                    "type": "Control",
                    "container_type": "Bottle",
                },
            ),
        ],
        analytes=[AnalyteModel(key="analyte:1", name="AN1", assay_key="assay:cal", assay_information_type="Immunology")],
    )

    derived = service.derive_protocol_defaults(addon)
    defaults = derived["protocol_defaults"]

    assert defaults["assay_information"]["StopPreparationWithFailedCalibrator"] is True
    assert defaults["assay_information"]["StopPreparationWithFailedControl"] is True
    assert defaults["assay_information"]["DerivedComponentCount"] == 2

    processing = defaults["processing_workflow_steps"]
    assert [group["GroupDisplayName"] for group in processing] == ["PS-01", "PS-02"]
    assert processing[0]["GroupSteps"][0]["StepParameters"]["DerivedAssayType"] == "Calibrator"
    assert processing[1]["GroupSteps"][0]["StepParameters"]["DerivedContainerType"] == "Bottle"

    assert defaults["loading_workflow_steps"][0]["StepParameters"]["FullFilename"] == "immuno-loading-template"


def test_default_derivation_service_is_deterministic_for_equal_payloads() -> None:
    service = DefaultDerivationService()
    addon = AddonModel(
        assays=[
            AssayModel(
                key="assay:1",
                protocol_type="Chem",
                metadata={
                    "component_name": "Component A",
                    "parameter_set_number": "PS-01",
                    "type": "Reagent",
                    "container_type": "Tube",
                },
            )
        ]
    )

    assert service.derive_protocol_defaults(addon) == service.derive_protocol_defaults(addon)

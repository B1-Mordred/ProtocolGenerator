from addon_generator.input_models.dtos import AnalyteInputDTO, AssayInputDTO, DilutionSchemeInputDTO, InputDTOBundle, SamplePrepStepInputDTO
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.validation.dto_validator import validate_dto_bundle


def test_dto_validator_detects_scope_parameter_set_vocab_and_dilution_errors() -> None:
    bundle = InputDTOBundle(
        source_type="excel",
        source_name="book.xlsx",
        assays=[AssayInputDTO(key="assay:chem", protocol_type="CHEM")],
        analytes=[
            AnalyteInputDTO(key="a1", name="GLU", assay_key="assay:chem"),
            AnalyteInputDTO(key="a2", name="glu", assay_key="assay:ia", assay_information_type="PS1"),
        ],
        sample_prep_steps=[SamplePrepStepInputDTO(key="s1", label="Spin")],
        dilution_schemes=[
            DilutionSchemeInputDTO(key="d1", label="D1", metadata={"ratio": "foo"}),
            DilutionSchemeInputDTO(key="d2", label="D2", metadata={"ratio": "1:0"}),
        ],
        hidden_vocab={"SamplePrepAction": ["Mix"]},
        provenance={"dilutions.ratio": [FieldProvenance(source_type="excel", source_file="book.xlsx", source_sheet="Dilutions", row=3, column="B")]},
    )

    result = validate_dto_bundle(bundle)
    codes = {issue.code for issue in result.issues.issues}

    assert "duplicate-analyte-incompatible-scope" in codes
    assert "unresolved-parameter-set-assay-link" in codes
    assert "unsupported-sample-prep-action" in codes
    assert "malformed-dilution-scheme" in codes
    assert "invalid-dilution-ratio" in codes
    assert any(issue.source_location == "book.xlsx:Dilutions:row=3:col=B" for issue in result.issues.issues if issue.code in {"malformed-dilution-scheme", "invalid-dilution-ratio"})

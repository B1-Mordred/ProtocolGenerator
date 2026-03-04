from pathlib import Path

from protocol_generator_gui.schema_utils import (
    load_schema,
    loading_step_types,
    processing_step_types,
)


def test_extract_loading_step_types():
    schema = load_schema(Path(__file__).resolve().parents[1] / "protocol.schema.json")
    mapping = loading_step_types(schema)
    assert "LoadCalibratorAndControlCarrier" in mapping
    required = mapping["LoadCalibratorAndControlCarrier"]["required"]
    assert "RequiredCalibrators" in required
    assert "RequiredControls" in required


def test_extract_processing_step_types():
    schema = load_schema(Path(__file__).resolve().parents[1] / "protocol.schema.json")
    mapping = processing_step_types(schema)
    assert "SingleTransfer" in mapping
    assert "StepParameters" not in mapping["SingleTransfer"]
    assert "required" in mapping["SingleTransfer"]

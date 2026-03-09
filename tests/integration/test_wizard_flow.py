from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from protocol_generator_gui.persistence import DraftPersistence
from protocol_generator_gui.validation import validate_protocol
from protocol_generator_gui.wizard_logic import build_import_conflicts, can_progress, resolve_conflict


class WizardFlowHarness:
    def __init__(self, schema: dict, persistence: DraftPersistence):
        self.schema = schema
        self.persistence = persistence
        self.current_step = 0
        self.save_path: Path | None = None
        self.payload: dict = {}
        self.conflicts = []

    def set_payload(self, payload: dict) -> None:
        self.payload = payload

    def set_conflicts(self, conflicts: list) -> None:
        self.conflicts = conflicts

    def attempt_transition(self, next_step: int) -> bool:
        if next_step > 0 and self.save_path is None:
            return False
        if validate_protocol(self.schema, self.payload):
            return False
        allowed, _ = can_progress("validation", self.conflicts)
        if not allowed:
            return False
        self.current_step = next_step
        return True

    def reorder_processing_step(self, from_idx: int, to_idx: int) -> None:
        steps = self.payload["ProcessingWorkflowSteps"][0]["GroupSteps"]
        moved = steps.pop(from_idx)
        steps.insert(to_idx, moved)
        for index, step in enumerate(steps):
            step["StepIndex"] = index

    def edit_processing_step(self, index: int, *, step_type: str) -> None:
        steps = self.payload["ProcessingWorkflowSteps"][0]["GroupSteps"]
        steps[index]["StepType"] = step_type

    def autosave(self) -> Path | None:
        if self.save_path is None:
            return None
        self.persistence.write_json_atomic(self.save_path, self.payload)
        return self.save_path


def test_wizard_blocks_invalid_data_and_allows_valid_transition(schema: dict, minimal_protocol: dict, tmp_path: Path):
    harness = WizardFlowHarness(schema, DraftPersistence(tmp_path / "draft.json"))
    harness.set_payload({})

    assert harness.attempt_transition(1) is False

    harness.save_path = tmp_path / "protocol.json"
    harness.set_payload(deepcopy(minimal_protocol))

    assert harness.attempt_transition(1) is True
    assert harness.current_step == 1


def test_processing_step_reorder_and_edit(schema: dict, minimal_protocol: dict, tmp_path: Path):
    harness = WizardFlowHarness(schema, DraftPersistence(tmp_path / "draft.json"))
    harness.save_path = tmp_path / "protocol.json"
    payload = deepcopy(minimal_protocol)
    payload["ProcessingWorkflowSteps"][0]["GroupSteps"].append(
        {
            "StepIndex": 1,
            "StepType": "UnloadCentrifuge",
            "StaticDurationInSeconds": 0,
            "DynamicDurationInSeconds": 0,
            "StepParameters": {
                "KeepGripperTools": False,
                "StaticDurationInSeconds": 0,
                "DynamicDurationInSeconds": 0,
            },
        }
    )
    harness.set_payload(payload)

    harness.reorder_processing_step(1, 0)
    harness.edit_processing_step(1, step_type="UnloadCentrifuge")

    steps = harness.payload["ProcessingWorkflowSteps"][0]["GroupSteps"]
    assert [step["StepIndex"] for step in steps] == [0, 1]
    assert steps[0]["StepType"] == "UnloadCentrifuge"


def test_autosave_runs_only_after_save_path_selected(schema: dict, minimal_protocol: dict, tmp_path: Path):
    harness = WizardFlowHarness(schema, DraftPersistence(tmp_path / "draft.json"))
    harness.set_payload(deepcopy(minimal_protocol))

    assert harness.autosave() is None

    harness.save_path = tmp_path / "protocol.json"
    output_path = harness.autosave()

    assert output_path == tmp_path / "protocol.json"
    assert output_path.exists()


def test_required_conflicts_block_progress_until_resolved(schema: dict, minimal_protocol: dict, tmp_path: Path):
    harness = WizardFlowHarness(schema, DraftPersistence(tmp_path / "draft.json"))
    harness.save_path = tmp_path / "protocol.json"
    harness.set_payload(deepcopy(minimal_protocol))
    conflicts = build_import_conflicts({"MethodInformation": {"Id": "m1"}}, {"MethodInformation": {"Id": "m2"}}, {"MethodInformation"})
    harness.set_conflicts(conflicts)

    assert harness.attempt_transition(1) is False

    resolve_conflict(conflicts, "MethodInformation", "use_imported")
    assert harness.attempt_transition(1) is True

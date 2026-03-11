from __future__ import annotations

from addon_generator.input_models.dtos import InputDTOBundle, SamplePrepStepInputDTO
from addon_generator.ui.models.sampleprep_view_model import SamplePrepScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


def _state() -> AppState:
    state = AppState()
    state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            hidden_vocab={"SamplePrepAction": ["Mix", "Incubate"]},
            sample_prep_steps=[SamplePrepStepInputDTO(key="s1", label="Mix", metadata={"order": "1", "source": "A", "destination": "B"})],
        )
    ]
    return state


def test_sampleprep_vm_mutations_and_validation() -> None:
    state = _state()
    vm = SamplePrepScreenViewModel(state, MergeServiceAdapter())

    assert len(vm.steps) == 1
    first_id = vm.steps[0].step_id
    vm.update_field(first_id, "action", "Unknown")
    assert vm.steps[0].fields["action"].status == "invalid-action"

    added_id = vm.add_step()
    assert added_id is not None
    vm.update_field(added_id, "order", "2")
    vm.update_field(added_id, "action", "Mix")
    vm.update_field(added_id, "source", "tube-a")
    vm.update_field(added_id, "destination", "tube-b")
    assert vm.selected_step_id == added_id

    cloned_id = vm.duplicate_step(added_id)
    assert cloned_id is not None
    assert len(vm.steps) == 3

    vm.move_up(cloned_id)
    vm.move_down(cloned_id)
    vm.reset_field(cloned_id, "destination")
    assert vm.selected_step() is not None
    assert vm.selected_step().fields["destination"].status == "required"

    vm.delete_step(cloned_id)
    assert len(vm.steps) == 2
    assert "sample_prep.steps" in state.editor_state.manual_overrides
    assert state.validation_state.stale is True
    assert state.preview_state.stale is True


def test_sampleprep_vm_load_keeps_imported_step_order() -> None:
    state = AppState()
    state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            sample_prep_steps=[
                SamplePrepStepInputDTO(key="sample-prep-1", label="Mix", metadata={"order": "1"}),
                SamplePrepStepInputDTO(key="sample-prep-10", label="Heat", metadata={"order": "10"}),
                SamplePrepStepInputDTO(key="sample-prep-2", label="Shake", metadata={"order": "2"}),
            ],
        )
    ]

    vm = SamplePrepScreenViewModel(state, MergeServiceAdapter())

    assert [step.fields["action"].value for step in vm.steps] == ["Mix", "Heat", "Shake"]

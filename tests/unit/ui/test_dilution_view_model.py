from __future__ import annotations

from addon_generator.input_models.dtos import DilutionSchemeInputDTO, InputDTOBundle
from addon_generator.ui.models.dilution_view_model import DilutionScreenViewModel
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState


def _state() -> AppState:
    state = AppState()
    state.import_state.bundles = [
        InputDTOBundle(
            source_type="excel",
            dilution_schemes=[
                DilutionSchemeInputDTO(
                    key="d1",
                    label="Standard",
                    metadata={
                        "buffer1_ratio": "1",
                        "buffer2_ratio": "2",
                        "buffer3_ratio": "3",
                        "name_ref_used": True,
                        "name_ref_context": "RefA",
                    },
                )
            ],
        )
    ]
    state.import_state.provenance = {"dilutions.name": [{"source": "excel", "location": "x"}]}
    return state


def test_dilution_vm_mutations_and_validation() -> None:
    state = _state()
    vm = DilutionScreenViewModel(state, MergeServiceAdapter())

    assert len(vm.dilutions) == 1
    first = vm.dilutions[0]
    assert first.fields["name"].has_reference is True
    assert first.fields["name"].reference_context == "RefA"

    first_id = first.dilution_id
    vm.update_field(first_id, "buffer1_ratio", "abc")
    assert vm.selected_dilution() is not None
    assert vm.selected_dilution().fields["buffer1_ratio"].status == "invalid-ratio"

    added_id = vm.add_dilution()
    vm.update_field(added_id, "name", "Custom")
    vm.update_field(added_id, "buffer1_ratio", "4")
    vm.update_field(added_id, "buffer2_ratio", "5")
    vm.update_field(added_id, "buffer3_ratio", "6")

    clone_id = vm.duplicate_dilution(added_id)
    assert clone_id is not None
    vm.reset_field(clone_id, "buffer2_ratio")
    assert vm.selected_dilution() is not None
    assert vm.selected_dilution().fields["buffer2_ratio"].status == "required"

    vm.delete_dilution(clone_id)
    assert len(vm.dilutions) == 2
    assert "dilution_schemes" in state.editor_state.manual_overrides
    assert state.validation_state.stale is True
    assert state.preview_state.stale is True

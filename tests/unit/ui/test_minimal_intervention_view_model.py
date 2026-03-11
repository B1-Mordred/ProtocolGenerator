from protocol_generator_gui.schema_utils import load_schema
from protocol_generator_gui.wizard_logic import (
    apply_checklist_action,
    build_required_by_schema_checklist,
    minimal_intervention_items,
)


def test_minimal_intervention_filters_out_auto_resolved_items() -> None:
    schema = load_schema()
    payload = {
        "MethodInformation": {"Id": "M-1", "DisplayName": "GUI Name"},
        "AssayInformation": [{"Type": "A"}],
        "LoadingWorkflowSteps": [],
    }
    imported_payload = {
        "MethodInformation": {"Version": "1.0"},
    }
    merge_report = {
        "required_fields": {"conflicting": []},
        "field_provenance": [
            {"path": "MethodInformation.Version", "source": "imported", "conflict": False, "conflict_sources": []},
        ],
    }

    checklist = build_required_by_schema_checklist(schema, payload, imported_payload, merge_report)
    visible = minimal_intervention_items(checklist, enabled=True)

    assert all(item.classification in {"user-required", "conflict-required"} for item in visible)
    assert any(item.path == "LoadingWorkflowSteps" for item in visible)
    assert all(item.path != "MethodInformation.Version" for item in visible)


def test_conflict_required_items_are_visible_in_minimal_mode() -> None:
    schema = load_schema()
    payload = {
        "MethodInformation": {"Id": "GUI-ID", "Version": "1.0"},
        "AssayInformation": [{"Type": "A"}],
        "LoadingWorkflowSteps": [{"StepType": "LoadMfxCarriers", "StepParameters": {}}],
    }
    imported_payload = {
        "MethodInformation": {"Id": "IMPORTED-ID"},
    }
    merge_report = {
        "required_fields": {"conflicting": ["MethodInformation.Id"]},
        "field_provenance": [
            {"path": "MethodInformation.Id", "source": "gui", "conflict": True, "conflict_sources": ["imported"]},
        ],
    }

    checklist = build_required_by_schema_checklist(schema, payload, imported_payload, merge_report)
    item = {entry.path: entry for entry in checklist}["MethodInformation.Id"]

    assert item.classification == "conflict-required"
    visible = minimal_intervention_items(checklist, enabled=True)
    assert any(entry.path == "MethodInformation.Id" for entry in visible)


def test_apply_checklist_action_prefers_import_then_default_then_builtin() -> None:
    schema = load_schema()
    payload = {
        "MethodInformation": {},
        "AssayInformation": [{}],
        "LoadingWorkflowSteps": [],
    }
    imported_payload = {
        "MethodInformation": {"Version": "2.0"},
    }

    checklist = build_required_by_schema_checklist(schema, payload, imported_payload, merge_report={})
    by_path = {item.path: item for item in checklist}

    imported_ok, imported_value = apply_checklist_action(by_path["MethodInformation.Version"], "accept_imported")
    default_ok, default_value = apply_checklist_action(by_path["ProcessingWorkflowSteps"], "accept_default")

    assert imported_ok is True
    assert imported_value == "2.0"
    assert default_ok is True
    assert isinstance(default_value, list)

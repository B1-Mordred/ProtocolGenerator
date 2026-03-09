from protocol_generator_gui.wizard_logic import (
    WizardState,
    assay_analyte_integrity_warnings,
    build_field_tooltip,
    build_import_conflicts,
    build_output_preview,
    can_progress,
    categorize_schema_fields,
    make_step_help,
    resolve_conflict,
    summarize_progress,
    validate_method_editor,
)


class DummyVar:
    def __init__(self, value: str):
        self.value = value

    def get(self) -> str:
        return self.value


def test_build_field_tooltip_prefers_schema_description():
    assert build_field_tooltip("Any", {"description": "From schema"}) == "From schema"


def test_build_field_tooltip_falls_back_to_metadata():
    assert "operators" in build_field_tooltip("DisplayName", {})


def test_categorize_schema_fields_required_and_advanced():
    required, advanced = categorize_schema_fields(
        {
            "required": ["A", "C"],
            "properties": {
                "A": {"type": "string"},
                "B": {"type": "string"},
                "C": {"type": "integer"},
            },
        }
    )
    assert required == ["A", "C"]
    assert advanced == ["B"]


def test_method_editor_validation_flags_missing_and_format_errors():
    issues = validate_method_editor({"Id": "bad id", "Version": "alpha", "DisplayName": ""})
    assert any("Id" in issue for issue in issues)
    assert any("Version" in issue for issue in issues)
    assert any("DisplayName" in issue for issue in issues)


def test_assay_analyte_integrity_reports_orphan_duplicate_and_ambiguous_mapping():
    warnings = assay_analyte_integrity_warnings(
        [{"Type": "A1"}, {"Type": "A2"}],
        [
            {"name": "x", "assay_key": "missing"},
            {"name": "x", "assay_key": "A1"},
            {"name": "x", "assay_key": "A1"},
            {"name": "x", "assay_key": "A2"},
        ],
    )
    assert any("orphan" in w for w in warnings)
    assert any("duplicate" in w for w in warnings)
    assert any("ambiguous" in w for w in warnings)


def test_import_conflicts_required_field_blocks_progress_until_resolved():
    conflicts = build_import_conflicts(
        {"MethodInformation": {"Id": "m1"}},
        {"MethodInformation": {"Id": "m2"}},
        required_fields={"MethodInformation"},
    )
    allowed, reason = can_progress("output_preview_export", conflicts)
    assert allowed is False
    assert "MethodInformation" in reason
    resolve_conflict(conflicts, "MethodInformation", "use_imported")
    allowed_after, _ = can_progress("output_preview_export", conflicts)
    assert allowed_after is True


def test_wizard_state_draft_roundtrip_preserves_conflicts_and_target():
    state = WizardState(
        method_information={"Id": "m1"},
        assays=[{"Type": "A"}],
        conflicts=build_import_conflicts({"A": 1}, {"A": 2}, {"A"}),
        export_target="/tmp/out",
    )
    restored = WizardState.from_draft(state.to_draft())
    assert restored.method_information["Id"] == "m1"
    assert restored.conflicts[0].field == "A"
    assert restored.export_target == "/tmp/out"


def test_make_step_help_contains_sections():
    help_text = make_step_help("loading")
    assert "Purpose" in help_text
    assert "Required fields" in help_text
    assert "Examples" in help_text


def test_output_preview_messages_include_blocker_and_target_prompt():
    preview = build_output_preview({"a": 1}, "<xml />", None, ["MethodInformation"])
    assert preview["can_export"] is False
    assert any("Blocked" in m for m in preview["messages"])


def test_summarize_progress_counts_completion_and_errors():
    state = {
        "general": DummyVar("✓"),
        "loading": DummyVar("✗ (2)"),
        "processing": DummyVar("✗ (1)"),
    }
    assert summarize_progress(2, state, "Errors: 3 (...) ").endswith("Unresolved errors: 3")

from protocol_generator_gui.wizard_logic import (
    build_field_tooltip,
    categorize_schema_fields,
    make_step_help,
    summarize_progress,
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


def test_make_step_help_contains_sections():
    help_text = make_step_help("loading")
    assert "Purpose" in help_text
    assert "Required fields" in help_text
    assert "Examples" in help_text


def test_summarize_progress_counts_completion_and_errors():
    state = {
        "general": DummyVar("✓"),
        "loading": DummyVar("✗ (2)"),
        "processing": DummyVar("✗ (1)"),
    }
    assert summarize_progress(2, state, "Errors: 3 (...) ").endswith("Unresolved errors: 3")

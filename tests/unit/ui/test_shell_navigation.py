from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication, QComboBox
except Exception as exc:  # pragma: no cover - environment/runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.__about__ import __app_name__
from addon_generator.input_models.dtos import (
    AnalyteInputDTO,
    AssayInputDTO,
    DilutionSchemeInputDTO,
    InputDTOBundle,
    MethodInputDTO,
    SamplePrepStepInputDTO,
    UnitInputDTO,
)
from addon_generator.ui.shell import MainShell


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_shell_navigation_switches_sections(qapp) -> None:
    shell = MainShell()
    shell.sidebar.setCurrentRow(3)
    assert shell.stack.currentIndex() == 3
    assert shell.app_state.editor_state.selected_section_index == 3
    shell.sidebar.setCurrentRow(9)
    assert shell.stack.currentIndex() == 9
    assert shell.app_state.editor_state.selected_section_index == 9


def test_shell_sidebar_badges_refresh_when_counts_change(qapp) -> None:
    shell = MainShell()

    shell.app_state.editor_state.effective_values = {
        "hidden_vocab": {"SamplePrepAction": ["Mix"]},
        "method": {"method_id": "", "method_version": "1"},
    }
    shell.app_state.editor_state.sample_prep_overrides = [
        {
            "order": "",
            "action": "Bad",
            "source": "A",
            "destination": "",
            "volume": "1",
            "duration": "1",
            "force": "1",
        }
    ]
    shell.app_state.editor_state.dilution_overrides = [
        {"name": "D1", "buffer1_ratio": "x", "buffer2_ratio": "", "buffer3_ratio": "3"}
    ]
    shell.app_state.editor_state.unresolved_conflicts = {
        "sample_prep.steps.0.action": [{}],
        "dilution_schemes.0.buffer1_ratio": [{}],
        "method.method_id": [{}],
    }

    shell._refresh_status()
    assert shell.sidebar.item(3).text().endswith("(4)")
    assert shell.sidebar.item(4).text().endswith("(3)")
    assert shell.sidebar.item(5).text().endswith("(4)")

    shell.app_state.editor_state.sample_prep_overrides = []
    shell.app_state.editor_state.dilution_overrides = []
    shell.app_state.editor_state.unresolved_conflicts = {}
    shell._refresh_status()

    assert shell.sidebar.item(3).text() == "Sample Prep"
    assert shell.sidebar.item(4).text() == "Dilutions"
    assert shell.sidebar.item(5).text().endswith("(2)")


def test_shell_window_title_uses_about_metadata(qapp) -> None:
    shell = MainShell()

    assert shell.windowTitle() == __app_name__


def test_shell_data_entry_and_review_views(qapp) -> None:
    shell = MainShell()

    shell.show_manual_entry()
    assert shell.main_stack.currentIndex() == 1

    shell.show_data_entry_home()
    assert shell.main_stack.currentIndex() == 0

    shell.show_data_review()
    assert shell.main_stack.currentIndex() == 2
    assert shell.stack.currentIndex() == 5



def test_shell_populates_manual_kit_components_from_imported_bundle(qapp) -> None:
    shell = MainShell()

    bundle = InputDTOBundle(
        source_type="excel",
        method=MethodInputDTO(
            key="method:M-1",
            method_id="M-1",
            method_version="1.0",
            display_name="Kit One",
            series_name="Series-1",
            order_number="KIT-001",
        ),
        assays=[
            AssayInputDTO(
                key="PS-1",
                protocol_type="CHEM",
                protocol_display_name="Component A",
                xml_name="Basic Kit",
                metadata={
                    "product_number": "PN-1",
                    "component_name": "Component A",
                    "parameter_set_number": "PS-1",
                    "assay_abbreviation": "ABB",
                    "parameter_set_name": "Basic Kit",
                    "type": "CHEM",
                    "container_type": "Tube",
                },
            )
        ],
        analytes=[AnalyteInputDTO(key="analyte:1", name="Glucose", assay_key="Basic Kit")],
        units=[UnitInputDTO(key="unit:1", name="mg/dL", analyte_key="analyte:1")],
        sample_prep_steps=[
            SamplePrepStepInputDTO(
                key="sample-prep-1",
                label="Mix",
                metadata={"source": "Component A", "destination": "Component A", "duration": "00:30"},
            )
        ],
        dilution_schemes=[
            DilutionSchemeInputDTO(key="dilution:1+4", label="1+4", metadata={"buffer1_ratio": "50", "buffer2_ratio": "50"})
        ],
    )

    shell._populate_manual_entry_from_bundle(bundle)

    assert shell.manual_entry_view.assays_table.item(0, 0).text() == "PN-1"
    assert shell.manual_entry_view.assays_table.item(0, 1).text() == "Component A"
    assert shell.manual_entry_view.assays_table.item(0, 2).text() == "PS-1"
    assert shell.manual_entry_view.basics_fields["kit_series"].text() == "Series-1"
    assert shell.manual_entry_view.basics_fields["kit_product_number"].text() == "KIT-001"
    assert shell.manual_entry_view.basics_fields["addon_version"].text() == "1.0"

    container_combo = shell.manual_entry_view.assays_table.cellWidget(0, 6)
    assert isinstance(container_combo, QComboBox)
    assert container_combo.currentText() == "Tube"

    assay_combo = shell.manual_entry_view.analytes_table.cellWidget(0, 1)
    assert isinstance(assay_combo, QComboBox)
    assert assay_combo.currentText() == "Basic Kit"

    assert shell.manual_entry_view.sample_prep_table.cellWidget(0, 0).currentText() == "Mix"
    assert shell.manual_entry_view.sample_prep_table.cellWidget(0, 1).currentText() == "Component A"
    assert shell.manual_entry_view.sample_prep_table.item(0, 4).text() == "00:30"
    assert shell.manual_entry_view.dilutions_table.item(0, 0).text() == "1+4"
    assert shell.manual_entry_view.dilutions_table.item(0, 1).text() == "50"


def test_shell_does_not_backfill_parameter_set_number_from_internal_assay_key(qapp) -> None:
    shell = MainShell()

    bundle = InputDTOBundle(
        source_type="excel",
        assays=[
            AssayInputDTO(
                key="dilution-buffer-1",
                protocol_type="Reagent",
                protocol_display_name="Dilution Buffer 1",
                xml_name="BASIC Kit",
                metadata={
                    "product_number": "92007",
                    "component_name": "Dilution Buffer 1",
                    "parameter_set_name": "BASIC Kit",
                    "type": "Reagent",
                    "container_type": "BG 50mL",
                },
            )
        ],
    )

    shell._populate_manual_entry_from_bundle(bundle)

    assert shell.manual_entry_view.assays_table.item(0, 1).text() == "Dilution Buffer 1"
    assert shell.manual_entry_view.assays_table.item(0, 2).text() == ""


def test_shell_admin_menu_has_dedicated_dropdown_configuration_actions(qapp) -> None:
    shell = MainShell()

    admin_menu = None
    for action in shell.menuBar().actions():
        if action.text() == "Admin":
            admin_menu = action.menu()
            break

    assert admin_menu is not None
    labels = [action.text() for action in admin_menu.actions()]
    assert labels == [
        "Configure Kit Type Values",
        "Configure Container Type Values",
        "Configure Unit of Measurement Values",
        "Configure Sample Prep Action Values",
        "Field Mapping",
    ]

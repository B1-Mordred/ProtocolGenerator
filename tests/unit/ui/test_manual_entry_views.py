from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication, QComboBox, QPushButton, QTableWidgetItem
except Exception as exc:  # pragma: no cover - runtime dependent
    pytest.skip(f"PySide6 Qt runtime unavailable: {exc}", allow_module_level=True)

from addon_generator.ui.views.data_entry_home_view import DataEntryHomeView
from addon_generator.ui.views.manual_entry_view import ManualEntryView


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_data_entry_home_buttons_trigger_callbacks(qapp) -> None:
    calls: list[str] = []
    view = DataEntryHomeView(on_manual_selected=lambda: calls.append("manual"), on_excel_selected=lambda: calls.append("excel"))

    for button in view.findChildren(QPushButton):
        if button.text() == "Enter Data Manually":
            button.click()
        if button.text() == "Import Excel File":
            button.click()

    assert calls == ["manual", "excel"]


def test_manual_entry_view_initial_rows_and_payload(qapp) -> None:
    called = {"count": 0}
    view = ManualEntryView(on_data_changed=lambda: called.__setitem__("count", called["count"] + 1))

    assert view.assays_table.rowCount() == 1
    assert view.analytes_table.rowCount() == 1
    assert view.sample_prep_table.rowCount() == 1
    assert view.dilutions_table.rowCount() == 1

    view.basics_fields["kit_series"].setText("KIT")
    view.basics_fields["kit_name"].setText("KIT-NAME")

    view.assays_table.setItem(0, 0, QTableWidgetItem("PN-1"))
    view.assays_table.setItem(0, 1, QTableWidgetItem("Component A"))
    view.assays_table.setItem(0, 2, QTableWidgetItem("PS-1"))

    view.sample_prep_table.cellWidget(0, 0).setCurrentText("Mix")
    view.sample_prep_table.cellWidget(0, 1).setCurrentText("Component A")
    view.sample_prep_table.cellWidget(0, 2).setCurrentText("Component A")

    payload = view.payload()
    assert "method_id" not in payload["method"]
    assert "method_version" not in payload["method"]
    assert "display_name" not in payload["method"]
    assert payload["method"]["kit_series"] == "KIT"
    assert payload["method"]["kit_name"] == "KIT-NAME"
    assert payload["assays"][0]["product_number"] == "PN-1"
    assert payload["assays"][0]["component_name"] == "Component A"
    assert payload["assays"][0]["parameter_set_number"] == "PS-1"
    assert payload["sample_prep"][0]["action"] == "Mix"
    assert called["count"] >= 2


def test_manual_entry_basics_fields_hide_method_identity_and_add_kit_name(qapp) -> None:
    view = ManualEntryView()

    assert "method_id" not in view.basics_fields
    assert "method_version" not in view.basics_fields
    assert "display_name" not in view.basics_fields
    assert "kit_name" in view.basics_fields


def test_manual_entry_tab_order_and_kit_component_headers(qapp) -> None:
    view = ManualEntryView()

    tab_names = [view.tabs.tabText(i) for i in range(view.tabs.count())]
    assert tab_names[:4] == ["Basics", "Kit Components", "Dilutions", "Analytes"]

    headers = [view.assays_table.horizontalHeaderItem(i).text() for i in range(view.assays_table.columnCount())]
    assert headers == [
        "Product Number",
        "Component Name",
        "Parameter Set Number",
        "Assay Abbreviation",
        'Parameter Set Name (or "BASIC Kit")',
        "Type",
        "Container Type (if Liquid)",
    ]

    analyte_headers = [view.analytes_table.horizontalHeaderItem(i).text() for i in range(view.analytes_table.columnCount())]
    assert analyte_headers == ["Analyte Name", "Assay", "Unit of Measurement"]

    sample_prep_headers = [view.sample_prep_table.horizontalHeaderItem(i).text() for i in range(view.sample_prep_table.columnCount())]
    assert sample_prep_headers == ["Action", "Source", "Destination", "Volume", "Duration", "Force"]


def test_manual_entry_dropdown_cells_and_assay_options(qapp) -> None:
    view = ManualEntryView()

    view.assays_table.setItem(0, 1, QTableWidgetItem("Component A"))
    view.assays_table.setItem(0, 4, QTableWidgetItem("Basic Kit"))
    view.set_assays_rows([{"component_name": "Component A", "parameter_set_name": "Basic Kit", "type": "Liquid", "container_type": "Bottle"}])
    view.set_analytes_rows([{"name": "Glucose", "assay_key": "Basic Kit", "unit_names": "mg/dL"}])

    assay_type_combo = view.assays_table.cellWidget(0, 5)
    container_combo = view.assays_table.cellWidget(0, 6)
    analyte_assay_combo = view.analytes_table.cellWidget(0, 1)
    analyte_unit_combo = view.analytes_table.cellWidget(0, 2)
    sample_action_combo = view.sample_prep_table.cellWidget(0, 0)
    sample_source_combo = view.sample_prep_table.cellWidget(0, 1)
    sample_destination_combo = view.sample_prep_table.cellWidget(0, 2)

    assert isinstance(assay_type_combo, QComboBox)
    assert isinstance(container_combo, QComboBox)
    assert isinstance(analyte_assay_combo, QComboBox)
    assert isinstance(analyte_unit_combo, QComboBox)
    assert isinstance(sample_action_combo, QComboBox)
    assert isinstance(sample_source_combo, QComboBox)
    assert isinstance(sample_destination_combo, QComboBox)
    assert analyte_assay_combo.findText("Basic Kit") >= 0
    assert sample_source_combo.findText("Component A") >= 0
    assert sample_destination_combo.findText("Component A") >= 0

    sample_action_combo.setCurrentText("Mix")
    sample_source_combo.setCurrentText("Component A")
    sample_destination_combo.setCurrentText("Component A")

    payload = view.payload()
    assert payload["analytes"][0] == {"name": "Glucose", "assay_key": "Basic Kit", "unit_names": "mg/dL"}
    assert payload["sample_prep"][0]["action"] == "Mix"
    assert payload["sample_prep"][0]["source"] == "Component A"
    assert payload["sample_prep"][0]["destination"] == "Component A"


def test_manual_entry_dropdown_cells_clear_underlying_table_items(qapp) -> None:
    view = ManualEntryView()

    view.set_assays_rows([
        {
            "component_name": "Component A",
            "parameter_set_name": "Assay A",
            "type": "Liquid",
            "container_type": "Bottle",
        }
    ])

    assert view.assays_table.item(0, 5) is None
    assert view.assays_table.item(0, 6) is None

    view.set_analytes_rows([{"name": "Analyte 1", "assay_key": "Assay A", "unit_names": "mg/dL"}])
    assert view.analytes_table.item(0, 1) is None
    assert view.analytes_table.item(0, 2) is None

    view.set_sample_prep_rows([{"action": "Mix", "source": "Component A", "destination": "Component A"}])
    assert view.sample_prep_table.item(0, 0) is None
    assert view.sample_prep_table.item(0, 1) is None
    assert view.sample_prep_table.item(0, 2) is None


def test_manual_entry_set_rows_replaces_existing_combo_values_without_carryover(qapp) -> None:
    view = ManualEntryView()

    view.set_assays_rows([{"component_name": "Component A", "parameter_set_name": "Assay A", "type": "Liquid", "container_type": "Bottle"}])
    view.set_analytes_rows([{"name": "Analyte 1", "assay_key": "Assay A", "unit_names": "mg/dL"}])

    view.set_assays_rows([{"component_name": "Component B", "parameter_set_name": "Assay B", "type": "Solid", "container_type": "Tube"}])
    view.set_analytes_rows([{"name": "Analyte 2", "assay_key": "Assay B", "unit_names": "ng/mL"}])

    payload = view.payload()
    assert payload["assays"][0]["component_name"] == "Component B"
    assert payload["assays"][0]["parameter_set_name"] == "Assay B"
    assert payload["assays"][0]["type"] == "Solid"
    assert payload["assays"][0]["container_type"] == "Tube"
    assert payload["analytes"][0] == {"name": "Analyte 2", "assay_key": "Assay B", "unit_names": "ng/mL"}


def test_manual_entry_setters_restore_sample_prep_and_dilutions_rows(qapp) -> None:
    view = ManualEntryView()

    view.set_sample_prep_rows(
        [
            {
                "action": "Mix",
                "source": "Component A",
                "destination": "Component B",
                "volume": "50 uL",
                "duration": "00:30",
                "force": "Low",
            }
        ]
    )
    view.set_dilutions_rows(
        [
            {
                "key": "1+4",
                "buffer1_ratio": "50",
                "buffer2_ratio": "50",
                "buffer3_ratio": "",
            }
        ]
    )

    payload = view.payload()
    assert payload["sample_prep"][0]["action"] == "Mix"
    assert payload["sample_prep"][0]["source"] == "Component A"
    assert payload["sample_prep"][0]["destination"] == "Component B"
    assert payload["sample_prep"][0]["duration"] == "00:30"
    assert payload["dilutions"][0]["key"] == "1+4"
    assert payload["dilutions"][0]["buffer1_ratio"] == "50"


def test_manual_entry_applies_content_width_hints(qapp) -> None:
    view = ManualEntryView()

    for field in view.basics_fields.values():
        assert field.minimumWidth() > 250

    kit_components_widths = [view.assays_table.columnWidth(i) for i in range(view.assays_table.columnCount())]
    assert kit_components_widths[1] > kit_components_widths[0]
    assert kit_components_widths[4] > kit_components_widths[3]

    analytes_widths = [view.analytes_table.columnWidth(i) for i in range(view.analytes_table.columnCount())]
    assert analytes_widths[0] > analytes_widths[2]


def test_manual_entry_dropdowns_expand_for_long_option_values(qapp) -> None:
    view = ManualEntryView()

    long_action = "Very Long Sample Preparation Action Label"
    view.set_dropdown_options(
        kit_types=["Solid"],
        container_types=["Tube"],
        analyte_units=["mg/dL"],
        sample_prep_actions=[long_action],
    )

    action_combo = view.sample_prep_table.cellWidget(0, 0)
    assert isinstance(action_combo, QComboBox)
    assert action_combo.minimumContentsLength() >= len(long_action)

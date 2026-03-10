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

    payload = view.payload()
    assert "method_id" not in payload["method"]
    assert "method_version" not in payload["method"]
    assert "display_name" not in payload["method"]
    assert payload["method"]["kit_series"] == "KIT"
    assert payload["method"]["kit_name"] == "KIT-NAME"
    assert payload["assays"][0]["product_number"] == "PN-1"
    assert payload["assays"][0]["component_name"] == "Component A"
    assert payload["assays"][0]["parameter_set_number"] == "PS-1"
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


def test_manual_entry_dropdown_cells_and_assay_options(qapp) -> None:
    view = ManualEntryView()

    view.assays_table.setItem(0, 4, QTableWidgetItem("Basic Kit"))
    view.set_assays_rows([{"parameter_set_name": "Basic Kit", "type": "Liquid", "container_type": "Bottle"}])
    view.set_analytes_rows([{"name": "Glucose", "assay_key": "Basic Kit", "unit_names": "mg/dL"}])

    assay_type_combo = view.assays_table.cellWidget(0, 5)
    container_combo = view.assays_table.cellWidget(0, 6)
    analyte_assay_combo = view.analytes_table.cellWidget(0, 1)
    analyte_unit_combo = view.analytes_table.cellWidget(0, 2)

    assert isinstance(assay_type_combo, QComboBox)
    assert isinstance(container_combo, QComboBox)
    assert isinstance(analyte_assay_combo, QComboBox)
    assert isinstance(analyte_unit_combo, QComboBox)
    assert analyte_assay_combo.findText("Basic Kit") >= 0

    payload = view.payload()
    assert payload["analytes"][0] == {"name": "Glucose", "assay_key": "Basic Kit", "unit_names": "mg/dL"}

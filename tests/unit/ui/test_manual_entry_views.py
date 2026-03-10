from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication, QPushButton, QTableWidgetItem
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

    view.assays_table.setItem(0, 0, QTableWidgetItem("A1"))
    view.assays_table.setItem(0, 1, QTableWidgetItem("P"))

    payload = view.payload()
    assert "method_id" not in payload["method"]
    assert "method_version" not in payload["method"]
    assert "display_name" not in payload["method"]
    assert payload["method"]["kit_series"] == "KIT"
    assert payload["method"]["kit_name"] == "KIT-NAME"
    assert payload["assays"][0]["key"] == "A1"
    assert called["count"] >= 2


def test_manual_entry_basics_fields_hide_method_identity_and_add_kit_name(qapp) -> None:
    view = ManualEntryView()

    assert "method_id" not in view.basics_fields
    assert "method_version" not in view.basics_fields
    assert "display_name" not in view.basics_fields
    assert "kit_name" in view.basics_fields

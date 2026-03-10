from __future__ import annotations

import sys

from addon_generator.ui import app


def test_pyside6_availability_helper_reflects_find_spec(monkeypatch) -> None:
    monkeypatch.setattr(app, "find_spec", lambda name: object() if name == "PySide6" else None)

    assert app._pyside6_available() is True


def test_run_returns_error_with_clear_message_when_pyside6_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr(app, "initialize_logging", lambda: "test.log")
    monkeypatch.setattr(app, "_pyside6_available", lambda: False)

    exit_code = app.run()

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "PySide6 is not installed" in err
    assert "python -m pip install -e ." in err


def test_run_starts_shell_when_pyside6_available(monkeypatch) -> None:
    monkeypatch.setattr(app, "initialize_logging", lambda: "test.log")
    monkeypatch.setattr(app, "_pyside6_available", lambda: True)

    calls: dict[str, object] = {}

    class FakeApplication:
        @staticmethod
        def instance():
            return None

        def __init__(self, argv):
            calls["argv"] = argv

        def exec(self) -> int:
            calls["exec"] = True
            return 99

    class FakeShell:
        def resize(self, width: int, height: int) -> None:
            calls["resize"] = (width, height)

        def show(self) -> None:
            calls["show"] = True

    class FakeQtWidgets:
        QApplication = FakeApplication

    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", FakeQtWidgets)
    monkeypatch.setitem(sys.modules, "addon_generator.ui.shell", type("ShellModule", (), {"MainShell": FakeShell}))

    exit_code = app.run()

    assert exit_code == 99
    assert calls["argv"] == sys.argv
    assert calls["resize"] == (1400, 900)
    assert calls["show"] is True
    assert calls["exec"] is True

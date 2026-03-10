from __future__ import annotations

from importlib.util import find_spec
import logging
import sys

from addon_generator.runtime.logging import initialize_logging


def _pyside6_available() -> bool:
    return find_spec("PySide6") is not None


def run() -> int:
    log_file = initialize_logging()
    logging.getLogger(__name__).info("Logging initialized at %s", log_file)
    if not _pyside6_available():
        print(
            "PySide6 is not installed. Install desktop dependencies with `python -m pip install -e .`.",
            file=sys.stderr,
        )
        return 2

    from PySide6.QtWidgets import QApplication

    from addon_generator.ui.shell import MainShell

    app = QApplication.instance() or QApplication(sys.argv)
    shell = MainShell()
    shell.resize(1400, 900)
    shell.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

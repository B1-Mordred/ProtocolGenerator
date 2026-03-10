from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from addon_generator.runtime.logging import initialize_logging
from addon_generator.ui.shell import MainShell


def run() -> int:
    log_file = initialize_logging()
    logging.getLogger(__name__).info("Logging initialized at %s", log_file)
    app = QApplication.instance() or QApplication(sys.argv)
    shell = MainShell()
    shell.resize(1400, 900)
    shell.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())

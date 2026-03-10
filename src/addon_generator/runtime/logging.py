from __future__ import annotations

import logging
from pathlib import Path

from addon_generator.runtime.paths import get_runtime_paths


def initialize_logging(level: int = logging.INFO) -> Path:
    paths = get_runtime_paths()
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = paths.logs_dir / "addon_authoring_studio.log"

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_file:
            return log_file

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)

    return log_file

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

APP_DIR_NAME = "AddOnAuthoringStudio"


@dataclass(frozen=True)
class RuntimePaths:
    runtime_support_dir: Path
    config_dir: Path
    drafts_dir: Path
    logs_dir: Path


@lru_cache(maxsize=1)
def get_runtime_paths() -> RuntimePaths:
    system_name = platform.system().lower()
    home = Path.home()

    if system_name == "windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        config_dir = appdata / APP_DIR_NAME
        logs_dir = local_appdata / APP_DIR_NAME / "logs"
    elif system_name == "darwin":
        config_dir = home / "Library" / "Application Support" / APP_DIR_NAME
        logs_dir = home / "Library" / "Logs" / APP_DIR_NAME
    else:
        config_dir = home / ".config" / APP_DIR_NAME
        logs_dir = home / ".local" / "state" / APP_DIR_NAME / "logs"

    return RuntimePaths(
        runtime_support_dir=config_dir,
        config_dir=config_dir,
        drafts_dir=config_dir / "drafts",
        logs_dir=logs_dir,
    )

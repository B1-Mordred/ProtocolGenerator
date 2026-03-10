from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import platform
import subprocess


@dataclass(frozen=True)
class RestartHandoff:
    command: list[str]
    cwd: str
    created_at: str



def write_restart_handoff(path: Path, command: list[str], *, cwd: str | None = None) -> Path:
    payload = RestartHandoff(
        command=command,
        cwd=cwd or str(Path.cwd()),
        created_at=datetime.now(tz=timezone.utc).isoformat(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.__dict__, indent=2), encoding="utf-8")
    return path



def launch_installer(installer_path: Path, *, handoff_path: Path | None = None) -> None:
    system = platform.system().lower()
    if handoff_path:
        # installers/updaters can use this env var to relaunch the app once install finishes
        env = {"PROTOCOL_GENERATOR_RESTART_HANDOFF": str(handoff_path)}
    else:
        env = {}

    if system == "windows":
        command = ["cmd", "/c", "start", "", str(installer_path)]
    elif system == "darwin":
        command = ["open", str(installer_path)]
    else:
        installer_path.chmod(installer_path.stat().st_mode | 0o111)
        command = [str(installer_path)]

    subprocess.Popen(command, env={**os.environ, **env})  # noqa: S603 - local installer execution is required

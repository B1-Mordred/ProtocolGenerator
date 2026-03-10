from __future__ import annotations

import logging
from pathlib import Path

from addon_generator.runtime.logging import initialize_logging
from addon_generator.runtime.paths import APP_DIR_NAME, RuntimePaths, get_runtime_paths


def _reset_runtime_paths_cache() -> None:
    get_runtime_paths.cache_clear()


def test_runtime_paths_windows(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", "/tmp/roaming")
    monkeypatch.setenv("LOCALAPPDATA", "/tmp/local")
    _reset_runtime_paths_cache()

    paths = get_runtime_paths()

    assert paths.config_dir == Path("/tmp/roaming") / APP_DIR_NAME
    assert paths.drafts_dir == Path("/tmp/roaming") / APP_DIR_NAME / "drafts"
    assert paths.logs_dir == Path("/tmp/local") / APP_DIR_NAME / "logs"


def test_runtime_paths_macos(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/Users/tester")))
    _reset_runtime_paths_cache()

    paths = get_runtime_paths()

    assert paths.config_dir == Path("/Users/tester/Library/Application Support") / APP_DIR_NAME
    assert paths.logs_dir == Path("/Users/tester/Library/Logs") / APP_DIR_NAME


def test_runtime_paths_linux(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/tester")))
    _reset_runtime_paths_cache()

    paths = get_runtime_paths()

    assert paths.config_dir == Path("/home/tester/.config") / APP_DIR_NAME
    assert paths.logs_dir == Path("/home/tester/.local/state") / APP_DIR_NAME / "logs"


def test_initialize_logging_writes_to_runtime_logs_dir(monkeypatch, tmp_path: Path) -> None:
    runtime_paths = RuntimePaths(
        runtime_support_dir=tmp_path / "support",
        config_dir=tmp_path / "config",
        drafts_dir=tmp_path / "config" / "drafts",
        logs_dir=tmp_path / "logs",
    )
    monkeypatch.setattr("addon_generator.runtime.logging.get_runtime_paths", lambda: runtime_paths)

    log_file = initialize_logging(level=logging.INFO)
    logger = logging.getLogger("tests.runtime")
    logger.info("runtime-log-check")

    assert log_file == tmp_path / "logs" / "addon_authoring_studio.log"
    assert log_file.exists()
    assert "runtime-log-check" in log_file.read_text(encoding="utf-8")

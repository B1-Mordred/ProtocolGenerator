from __future__ import annotations

from pathlib import Path

from addon_generator.runtime.resources import get_resource_path


def test_get_resource_path_prefers_meipass(monkeypatch, tmp_path: Path) -> None:
    bundled = tmp_path / "protocol.schema.json"
    bundled.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    resolved = get_resource_path("protocol.schema.json", anchor_file=__file__)

    assert resolved == bundled


def test_get_resource_path_finds_repo_root_from_anchor() -> None:
    resolved = get_resource_path("protocol.schema.json", anchor_file=__file__)

    assert resolved.name == "protocol.schema.json"
    assert resolved.exists()

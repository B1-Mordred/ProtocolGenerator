from __future__ import annotations

from pathlib import Path

from protocol_generator_gui import schema_utils


def test_default_schema_path_prefers_meipass_when_available(monkeypatch, tmp_path: Path) -> None:
    bundled = tmp_path / "protocol.schema.json"
    bundled.write_text('{"type": "object"}', encoding="utf-8")

    monkeypatch.setattr(schema_utils.sys, "_MEIPASS", str(tmp_path), raising=False)

    resolved = schema_utils.default_schema_path()

    assert resolved == bundled


def test_load_schema_without_argument_reads_repo_schema() -> None:
    schema = schema_utils.load_schema()

    assert schema["title"] == "Protocol"

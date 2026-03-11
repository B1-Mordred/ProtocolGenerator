from __future__ import annotations

from pathlib import Path

from addon_generator.config.rule_pack_loader import list_rule_packs, load_rule_pack


def test_load_rule_pack_resolves_default_relative_directory_from_meipass(monkeypatch, tmp_path: Path) -> None:
    pack_dir = tmp_path / "config" / "rule_packs"
    pack_dir.mkdir(parents=True)
    (pack_dir / "default.json").write_text(
        "{\"profile_marker\": \"bundled\", \"mapping_path\": \"config/mapping.v1.yaml\", \"method_defaults\": {\"DisplayName\": \"Bundled Method\"}}",
        encoding="utf-8",
    )

    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    isolated_cwd = tmp_path / "isolated"
    isolated_cwd.mkdir()
    monkeypatch.chdir(isolated_cwd)

    pack = load_rule_pack("default", rule_packs_dir=Path("config/rule_packs"))

    assert pack.profile_marker == "bundled"
    assert pack.method_defaults["DisplayName"] == "Bundled Method"


def test_list_rule_packs_resolves_relative_directory_with_windows_separators(monkeypatch, tmp_path: Path) -> None:
    pack_dir = tmp_path / "config" / "rule_packs"
    pack_dir.mkdir(parents=True)
    (pack_dir / "default.json").write_text("{}", encoding="utf-8")
    (pack_dir / "high_throughput.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    packs = list_rule_packs(rule_packs_dir=Path(r"config\rule_packs"))

    assert packs == ["default", "high_throughput"]

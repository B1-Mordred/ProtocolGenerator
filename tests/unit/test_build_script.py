from pathlib import Path


def test_windows_build_script_uses_module_invocation_for_pyinstaller() -> None:
    content = Path("build_windows_exe.ps1").read_text(encoding="utf-8")

    assert "python -m pip install -U pyinstaller" in content
    assert "python -m PyInstaller" in content
    assert "\npyinstaller " not in content.lower()


def test_windows_build_script_embeds_protocol_schema_resource() -> None:
    content = Path("build_windows_exe.ps1").read_text(encoding="utf-8")

    assert "--add-data \"protocol.schema.json;.\"" in content

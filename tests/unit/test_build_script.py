from pathlib import Path


SPEC_PATH = Path("build/pyinstaller/addon_authoring.spec")
WINDOWS_SCRIPT = Path("scripts/build_windows.ps1")
MACOS_SCRIPT = Path("scripts/build_macos.sh")
LINUX_SCRIPT = Path("scripts/build_linux.sh")


def test_pyinstaller_spec_uses_addon_authoring_entrypoint() -> None:
    content = SPEC_PATH.read_text(encoding="utf-8")

    assert "src/addon_generator/ui/app.py" in content
    assert "COLLECT(" in content
    assert "--onefile" not in content


def test_pyinstaller_spec_bundles_required_resources() -> None:
    content = SPEC_PATH.read_text(encoding="utf-8")

    assert "protocol.schema.json" in content
    assert "AddOn.xsd" in content
    assert "config/mapping.v1.yaml" in content
    assert "src/addon_generator/fragments" in content
    assert "src/addon_generator/resources" in content
    assert "deploy/manifests" in content
    assert "deploy/icons" in content


def test_platform_build_scripts_use_spec_driven_pyinstaller_invocation() -> None:
    for script in (WINDOWS_SCRIPT, MACOS_SCRIPT, LINUX_SCRIPT):
        content = script.read_text(encoding="utf-8")
        assert "python -m pip install -U pyinstaller" in content
        assert "python -m PyInstaller" in content
        assert "build/pyinstaller/addon_authoring.spec" in content
        assert "--onefile" not in content

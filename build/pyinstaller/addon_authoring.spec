# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


def _resolve_spec_dir() -> Path:
    spec_file = globals().get('__file__')
    if spec_file:
        return Path(spec_file).resolve().parent

    spec_path = globals().get('SPECPATH')
    if spec_path:
        return Path(spec_path).resolve()

    default_spec_dir = Path.cwd() / 'build' / 'pyinstaller'
    if default_spec_dir.exists():
        return default_spec_dir.resolve()

    return Path.cwd().resolve()


REPO_ROOT = _resolve_spec_dir().parent.parent


def _data(path: str, target: str) -> tuple[str, str]:
    return (str(REPO_ROOT / path), target)


SRC_ROOT = REPO_ROOT / 'src'
APP_ENTRYPOINT = SRC_ROOT / 'addon_generator' / 'ui' / 'app.py'


a = Analysis(
    [str(APP_ENTRYPOINT)],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=[
        _data('protocol.schema.json', '.'),
        _data('AddOn.xsd', '.'),
        _data('config/mapping.v1.yaml', 'config'),
        _data('src/addon_generator/fragments', 'addon_generator/fragments'),
        _data('src/addon_generator/resources', 'addon_generator/resources'),
        _data('deploy/manifests', 'deploy/manifests'),
        _data('deploy/icons', 'deploy/icons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProtocolGeneratorAddonAuthoring',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProtocolGeneratorAddonAuthoring',
)

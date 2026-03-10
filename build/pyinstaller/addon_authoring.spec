# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_ROOT = Path.cwd()


def _data(path: str, target: str) -> tuple[str, str]:
    return (str(PROJECT_ROOT / path), target)


a = Analysis(
    ['src/addon_generator/ui/app.py'],
    pathex=['src'],
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

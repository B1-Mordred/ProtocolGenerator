#!/usr/bin/env bash
set -euo pipefail

python -m pip install -U pyinstaller
python -m PyInstaller --noconfirm --clean --distpath "dist/macos" --workpath "build/pyinstaller/work/macos" "build/pyinstaller/addon_authoring.spec"

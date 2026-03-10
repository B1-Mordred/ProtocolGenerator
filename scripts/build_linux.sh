#!/usr/bin/env bash
set -euo pipefail

python -m pip install -U pyinstaller
python -m PyInstaller --noconfirm --clean --distpath "dist/linux" --workpath "build/pyinstaller/work/linux" "build/pyinstaller/addon_authoring.spec"

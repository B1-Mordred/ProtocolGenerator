python -m pip install -e .
python -m pip install -U pyinstaller
python -m PyInstaller --noconfirm --clean --distpath "dist/windows" --workpath "build/pyinstaller/work/windows" "build/pyinstaller/addon_authoring.spec"

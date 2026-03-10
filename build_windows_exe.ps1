python -m pip install -U pyinstaller
$version = python -c "from addon_generator.__about__ import __version__; print(__version__)"
python -m PyInstaller --noconfirm --name "ProtocolGeneratorGUI-$version" --onefile --windowed --paths src --add-data "protocol.schema.json;." src/protocol_generator_gui/main.py

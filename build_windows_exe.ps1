python -m pip install -U pyinstaller
python -m PyInstaller --noconfirm --name ProtocolGeneratorGUI --onefile --windowed --paths src --add-data "protocol.schema.json;." src/protocol_generator_gui/main.py

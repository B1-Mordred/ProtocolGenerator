import ast
from pathlib import Path


def test_main_uses_absolute_imports_for_packaged_execution() -> None:
    source = Path("src/protocol_generator_gui/main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    relative_imports = [
        node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level > 0
    ]

    assert relative_imports == []

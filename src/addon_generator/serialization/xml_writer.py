from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


def serialize_xml_document(root: ET.Element) -> str:
    """Serialize an XML tree with stable indentation and UTF-8 declaration."""

    root_copy = ET.fromstring(ET.tostring(root, encoding="utf-8"))
    ET.indent(root_copy, space="  ")
    return ET.tostring(root_copy, encoding="unicode", xml_declaration=True)


def write_xml_document(xml_content: str, output_path: Path | str) -> Path:
    """Write XML to disk using UTF-8 encoding and normalized newlines."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(xml_content.rstrip() + "\n", encoding="utf-8", newline="\n")
    return destination

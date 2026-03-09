"""XML and protocol generators for addon payloads."""

from .analytes_xml_generator import AddonXmlGenerationResult, generate_analytes_addon_xml
from .protocol_generator import ProtocolJsonGenerationResult, build_canonical_protocol_fragments, generate_protocol_json

__all__ = [
    "AddonXmlGenerationResult",
    "ProtocolJsonGenerationResult",
    "build_canonical_protocol_fragments",
    "generate_analytes_addon_xml",
    "generate_protocol_json",
]

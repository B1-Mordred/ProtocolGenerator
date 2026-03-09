"""Validation helpers for addon and protocol generation."""

from .cross_file_validator import CrossFileValidationResult, validate_cross_file_consistency
from .domain_validator import DomainValidationResult, validate_domain_context
from .protocol_schema_validator import ProtocolSchemaValidationResult, validate_protocol_schema
from .xsd_validator import XsdValidationResult, validate_xml_against_xsd

__all__ = [
    "CrossFileValidationResult",
    "DomainValidationResult",
    "ProtocolSchemaValidationResult",
    "XsdValidationResult",
    "validate_cross_file_consistency",
    "validate_domain_context",
    "validate_protocol_schema",
    "validate_xml_against_xsd",
]

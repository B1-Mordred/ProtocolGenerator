"""Validation helpers for addon XML generation."""

from .xsd_validator import XsdValidationResult, validate_xml_against_xsd

__all__ = ["XsdValidationResult", "validate_xml_against_xsd"]

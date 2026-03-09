from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from addon_generator.domain.models import AddonModel

_ASSAY_LABEL_FIELDS = frozenset({"protocol_type", "protocol_display_name", "xml_name", "assay_information_type", "label"})


_OPTIONAL_TEXT_FIELDS = {
    "display_name",
    "main_title",
    "sub_title",
    "order_number",
    "series_name",
    "product_name",
    "product_number",
    "legacy_protocol_id",
    "protocol_type",
    "protocol_display_name",
    "xml_name",
    "assay_information_type",
    "label",
}


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_text(value: Any) -> str:
    return str(value).strip()


def normalize_empty_container(value: Any) -> Any:
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return None
    return value


def normalize_value(value: Any, *, field_name: str | None = None) -> Any:
    if isinstance(value, str):
        if field_name in _ASSAY_LABEL_FIELDS:
            normalized = normalize_text(value)
            return normalized.casefold() or None
        if field_name in _OPTIONAL_TEXT_FIELDS:
            return normalize_optional_text(value)
        normalized = normalize_text(value)
        return normalized or None

    if isinstance(value, list):
        normalized = [normalize_value(item) for item in value]
        return normalize_empty_container(normalized)
    if isinstance(value, tuple):
        normalized = tuple(normalize_value(item) for item in value)
        return normalize_empty_container(normalized)
    if isinstance(value, set):
        normalized = sorted(normalize_value(item) for item in value)
        return normalize_empty_container(normalized)
    if isinstance(value, dict):
        normalized_items: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = str(raw_key).strip()
            normalized_item = normalize_value(raw_item, field_name=key)
            if normalized_item is not None:
                normalized_items[key] = normalized_item
        normalized = normalized_items
        return normalize_empty_container(normalized)
    if is_dataclass(value):
        return normalize_value(asdict(value))
    return value


def normalize_addon_for_comparison(addon: AddonModel) -> dict[str, Any]:
    canonical = normalize_value(asdict(addon))
    if not isinstance(canonical, dict):
        return {}

    canonical.pop("source_metadata", None)
    return canonical


def canonical_addons_equal(left: AddonModel, right: AddonModel) -> bool:
    return normalize_addon_for_comparison(left) == normalize_addon_for_comparison(right)

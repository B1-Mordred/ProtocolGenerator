from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .config_loader import ProjectionConfig
from .field_path import get_field_value
from .normalizers import normalize_for_matching


@dataclass(slots=True)
class LinkageIssue:
    entity: str
    reference: str
    reason: str


def _stringify(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def assign_ids(
    records: list[dict[str, Any]],
    *,
    id_field: str = "id",
    strategy: str = "sequential",
    start: int = 1,
    explicit_key_field: str | None = None,
) -> list[dict[str, Any]]:
    next_id = start
    key_to_id: dict[str, int] = {}
    for record in records:
        if strategy == "explicit_key":
            if not explicit_key_field:
                raise ValueError("explicit_key_field is required for explicit_key strategy")
            explicit_value = _stringify(get_field_value(record, explicit_key_field))
            if not explicit_value:
                raise ValueError("Missing explicit key value")
            if explicit_value not in key_to_id:
                key_to_id[explicit_value] = next_id
                next_id += 1
            record[id_field] = key_to_id[explicit_value]
            continue

        if strategy != "sequential":
            raise ValueError(f"Unsupported id strategy: {strategy}")
        if id_field not in record or not isinstance(record[id_field], int):
            record[id_field] = next_id
            next_id += 1
    return records


def _candidate_match(
    source_value: str,
    candidate_value: str,
    mode: str,
    alias_map: Mapping[str, str] | None,
) -> bool:
    if mode == "exact":
        return source_value == candidate_value
    if mode == "normalized":
        return normalize_for_matching(source_value) == normalize_for_matching(candidate_value)
    if mode == "alias_map":
        if alias_map is None:
            return False
        normalized_alias_map = {normalize_for_matching(k): v for k, v in alias_map.items()}
        source_canonical = normalized_alias_map.get(normalize_for_matching(source_value), source_value)
        candidate_canonical = normalized_alias_map.get(normalize_for_matching(candidate_value), candidate_value)
        return normalize_for_matching(source_canonical) == normalize_for_matching(candidate_canonical)

    raise ValueError(f"Unsupported matching mode: {mode}")


def _resolve_projection(
    source: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    projection: ProjectionConfig,
) -> Mapping[str, Any] | None:
    if projection.mode == "explicit_key":
        if not projection.explicit_key_path:
            raise ValueError("explicit_key mode requires explicit_key_path")
        source_key = _stringify(get_field_value(source, projection.explicit_key_path))
        if not source_key:
            return None
        for candidate in candidates:
            candidate_key = _stringify(get_field_value(candidate, projection.explicit_key_path))
            if source_key == candidate_key:
                return candidate
        return None

    source_value = _stringify(get_field_value(source, projection.source_path))
    if not source_value:
        return None

    matches = [
        candidate
        for candidate in candidates
        if _candidate_match(
            source_value=source_value,
            candidate_value=_stringify(get_field_value(candidate, projection.target_path)),
            mode=projection.mode,
            alias_map=projection.alias_map,
        )
    ]
    if len(matches) > 1:
        raise ValueError("Ambiguous projection: more than one candidate matched")
    return matches[0] if matches else None


def resolve_method_projection(
    source: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    projection: ProjectionConfig,
) -> Mapping[str, Any] | None:
    return _resolve_projection(source, candidates, projection)


def resolve_assay_projection(
    source: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    projection: ProjectionConfig,
) -> Mapping[str, Any] | None:
    return _resolve_projection(source, candidates, projection)


def resolve_analyte_projection(
    source: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    projection: ProjectionConfig,
) -> Mapping[str, Any] | None:
    return _resolve_projection(source, candidates, projection)


def validate_cross_file_linkage(
    *,
    methods: Iterable[Mapping[str, Any]],
    assays: Iterable[Mapping[str, Any]],
    analytes: Iterable[Mapping[str, Any]],
    method_projection: ProjectionConfig,
    assay_projection: ProjectionConfig,
    analyte_projection: ProjectionConfig,
) -> list[LinkageIssue]:
    issues: list[LinkageIssue] = []

    for method in methods:
        if resolve_method_projection(method, assays, method_projection) is None:
            issues.append(LinkageIssue(entity="method", reference=str(method), reason="No assay linkage found"))

    for assay in assays:
        if resolve_assay_projection(assay, analytes, assay_projection) is None:
            issues.append(LinkageIssue(entity="assay", reference=str(assay), reason="No analyte linkage found"))

    for analyte in analytes:
        if resolve_analyte_projection(analyte, methods, analyte_projection) is None:
            issues.append(LinkageIssue(entity="analyte", reference=str(analyte), reason="No method linkage found"))

    return issues

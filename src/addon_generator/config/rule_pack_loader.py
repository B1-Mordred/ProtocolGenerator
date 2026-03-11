from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class RulePack:
    name: str
    profile_marker: str | None
    mapping_path: str
    method_defaults: dict[str, Any]
    assay_defaults: list[dict[str, Any]]
    loading_processing_templates: dict[str, list[dict[str, Any]]]
    high_risk_fields: list[dict[str, Any]]


RULE_PACKS_DIR = Path("config/rule_packs")
DEFAULT_PACK_NAME = "default"


def list_rule_packs(rule_packs_dir: Path = RULE_PACKS_DIR) -> list[str]:
    if not rule_packs_dir.exists():
        return []
    names: list[str] = []
    for path in sorted(rule_packs_dir.iterdir()):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        names.append(path.stem)
    return names


def load_rule_pack(name: str | None = None, *, rule_packs_dir: Path = RULE_PACKS_DIR) -> RulePack:
    pack_name = (name or DEFAULT_PACK_NAME).strip() or DEFAULT_PACK_NAME
    path = _resolve_pack_path(pack_name, rule_packs_dir)
    payload = _load_structured_file(path)
    if not isinstance(payload, dict):
        payload = {}

    templates_raw = payload.get("loading_processing_templates")
    templates = templates_raw if isinstance(templates_raw, dict) else {}
    loading = templates.get("LoadingWorkflowSteps") if isinstance(templates.get("LoadingWorkflowSteps"), list) else []
    processing = templates.get("ProcessingWorkflowSteps") if isinstance(templates.get("ProcessingWorkflowSteps"), list) else []

    method_defaults = payload.get("method_defaults") if isinstance(payload.get("method_defaults"), dict) else {}
    assay_defaults = payload.get("assay_defaults") if isinstance(payload.get("assay_defaults"), list) else []
    high_risk_fields = payload.get("high_risk_fields") if isinstance(payload.get("high_risk_fields"), list) else []

    return RulePack(
        name=pack_name,
        profile_marker=str(payload.get("profile_marker") or "").strip() or None,
        mapping_path=str(payload.get("mapping_path") or "config/mapping.v1.yaml"),
        method_defaults=dict(method_defaults),
        assay_defaults=[dict(item) for item in assay_defaults if isinstance(item, dict)],
        loading_processing_templates={"LoadingWorkflowSteps": loading, "ProcessingWorkflowSteps": processing},
        high_risk_fields=[dict(item) for item in high_risk_fields if isinstance(item, dict)],
    )


def _resolve_pack_path(name: str, rule_packs_dir: Path) -> Path:
    for suffix in (".json", ".yaml", ".yml"):
        candidate = rule_packs_dir / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    fallback_json = rule_packs_dir / f"{DEFAULT_PACK_NAME}.json"
    if fallback_json.exists():
        return fallback_json
    return rule_packs_dir / f"{DEFAULT_PACK_NAME}.yaml"


def _load_structured_file(path: Path) -> Any:
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(content)

    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependent
        raise RuntimeError("YAML support unavailable for rule pack loading") from exc
    return yaml.safe_load(content)


def mapping_path_for_rule_pack(name: str | None) -> str:
    return load_rule_pack(name).mapping_path

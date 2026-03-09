from __future__ import annotations

from dataclasses import asdict
from typing import Any

from addon_generator.input_models.dtos import (
    AnalyteInputDTO,
    AssayInputDTO,
    InputDTOBundle,
    MethodInputDTO,
    UnitInputDTO,
)


class InputMergeService:
    def __init__(self, precedence: list[str] | None = None):
        self.precedence = precedence or ["default", "xml", "excel", "gui"]

    def merge(self, bundles: list[InputDTOBundle]) -> tuple[InputDTOBundle, dict[str, Any]]:
        by_priority = sorted(
            bundles,
            key=lambda b: self.precedence.index(b.source_type) if b.source_type in self.precedence else len(self.precedence),
        )
        conflicts: list[dict[str, Any]] = []

        method: MethodInputDTO | None = None
        method_source: str | None = None
        for bundle in by_priority:
            if bundle.method is None:
                continue
            if method is None:
                method = bundle.method
                method_source = bundle.source_type
                continue
            previous = asdict(method)
            incoming = asdict(bundle.method)
            for key, old in previous.items():
                new = incoming.get(key)
                if new not in (None, "") and old not in (None, "") and new != old:
                    conflicts.append({"path": f"method.{key}", "winner": new, "loser": old, "winner_source": bundle.source_type, "loser_source": method_source})
            method = bundle.method
            method_source = bundle.source_type

        assays = self._merge_keyed(by_priority, "assays", conflicts)
        analytes = self._merge_keyed(by_priority, "analytes", conflicts)
        units = self._merge_keyed(by_priority, "units", conflicts)

        merged = InputDTOBundle(
            source_type="default",
            source_name="merged",
            method=method,
            assays=assays,
            analytes=analytes,
            units=units,
            method_information_overrides=self._merge_dicts(by_priority, "method_information_overrides", conflicts, "method_information"),
            assay_fragments=self._concat(by_priority, "assay_fragments"),
            loading_fragments=self._concat(by_priority, "loading_fragments"),
            processing_fragments=self._concat(by_priority, "processing_fragments"),
            hidden_vocab=self._merge_hidden_vocab(by_priority),
            provenance=self._merge_provenance(by_priority),
        )
        return merged, {"precedence": self.precedence, "conflicts": sorted(conflicts, key=lambda i: i["path"]) }

    def _merge_keyed(self, bundles: list[InputDTOBundle], attr: str, conflicts: list[dict[str, Any]]) -> list[Any]:
        merged: dict[str, Any] = {}
        owners: dict[str, str] = {}
        for bundle in bundles:
            for item in getattr(bundle, attr):
                key = item.key
                if key in merged and merged[key] != item:
                    conflicts.append({"path": f"{attr}.{key}", "winner": asdict(item), "loser": asdict(merged[key]), "winner_source": bundle.source_type, "loser_source": owners[key]})
                merged[key] = item
                owners[key] = bundle.source_type
        return [merged[key] for key in sorted(merged)]

    def _merge_dicts(self, bundles: list[InputDTOBundle], attr: str, conflicts: list[dict[str, Any]], path_root: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        owners: dict[str, str] = {}
        for bundle in bundles:
            for key, value in getattr(bundle, attr).items():
                if key in merged and merged[key] != value:
                    conflicts.append({"path": f"{path_root}.{key}", "winner": value, "loser": merged[key], "winner_source": bundle.source_type, "loser_source": owners[key]})
                merged[key] = value
                owners[key] = bundle.source_type
        return merged

    def _concat(self, bundles: list[InputDTOBundle], attr: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for bundle in bundles:
            out.extend(getattr(bundle, attr))
        return out


    def _merge_hidden_vocab(self, bundles: list[InputDTOBundle]) -> dict[str, list[str]]:
        merged: dict[str, set[str]] = {}
        for bundle in bundles:
            for key, values in bundle.hidden_vocab.items():
                merged.setdefault(key, set()).update(str(value) for value in values if str(value).strip())
        return {key: sorted(values) for key, values in sorted(merged.items())}

    def _merge_provenance(self, bundles: list[InputDTOBundle]) -> dict[str, list[Any]]:
        merged: dict[str, list[Any]] = {}
        for bundle in bundles:
            for key, records in bundle.provenance.items():
                merged.setdefault(key, []).extend(records)
        return {key: merged[key] for key in sorted(merged)}

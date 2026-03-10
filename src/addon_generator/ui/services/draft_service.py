from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from addon_generator.importers.gui_mapper import map_gui_payload_to_bundle
from addon_generator.runtime.paths import get_runtime_paths
from typing import Any

from addon_generator.input_models.dtos import (
    AnalyteInputDTO,
    AssayInputDTO,
    DilutionSchemeInputDTO,
    InputDTOBundle,
    MethodInputDTO,
    SamplePrepStepInputDTO,
    UnitInputDTO,
)
from addon_generator.input_models.provenance import FieldProvenance
from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.state.draft_state import DraftState
from addon_generator.ui.state.editor_state import EditorState
from addon_generator.ui.state.import_state import ImportState
from addon_generator.ui.state.preview_state import PreviewState
from addon_generator.ui.state.validation_state import ValidationState


class DraftService:
    def save(self, app_state: AppState, drafts_dir: str | Path | None = None, draft_path: str | Path | None = None) -> Path:
        if draft_path is not None:
            path = Path(draft_path)
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            root = Path(drafts_dir) if drafts_dir is not None else get_runtime_paths().drafts_dir
            root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            path = root / f"addon_draft_{stamp}.json"

        sanitized_draft_state = asdict(app_state.draft_state)
        sanitized_draft_state["payload"] = {}
        payload = {
            "import_state": asdict(app_state.import_state),
            "editor_state": asdict(app_state.editor_state),
            "validation_state": asdict(app_state.validation_state),
            "preview_state": asdict(app_state.preview_state),
            "draft_state": sanitized_draft_state,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        app_state.draft_state.path = str(path)
        app_state.draft_state.payload = payload
        app_state.draft_state.dirty = False
        app_state.draft_state.last_saved_at = datetime.now(tz=timezone.utc)
        return path

    def load(self, path: str | Path) -> dict[str, Any]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return self._normalize_recovery_payload(raw)

    def restore(self, app_state: AppState, payload: dict[str, Any], *, source_path: str | None = None) -> None:
        import_payload = payload.get("import_state", {})
        editor_payload = payload.get("editor_state", {})
        validation_payload = payload.get("validation_state", {})
        preview_payload = payload.get("preview_state", {})
        draft_payload = payload.get("draft_state", {})

        bundles = [self._bundle_from_dict(item) for item in import_payload.get("bundles", [])]
        app_state.import_state = ImportState(
            bundles=bundles,
            provenance=import_payload.get("provenance", {}),
            imported_sample_prep_dtos=import_payload.get("imported_sample_prep_dtos", []),
            imported_dilution_dtos=import_payload.get("imported_dilution_dtos", []),
            conflict_summary=import_payload.get("conflict_summary", {}),
            provenance_lookup=import_payload.get("provenance_lookup", {}),
            issues=[],
            review_resolutions=import_payload.get("review_resolutions", {}),
        )
        app_state.editor_state = EditorState(**editor_payload)
        app_state.validation_state = ValidationState(**validation_payload)
        app_state.preview_state = PreviewState(**preview_payload)
        restored_path = source_path or draft_payload.get("path")
        app_state.draft_state = DraftState(
            path=restored_path,
            payload=payload,
            dirty=False,
            last_saved_at=self._coerce_datetime(draft_payload.get("last_saved_at")),
            restore_metadata={
                "restored_at": datetime.now(tz=timezone.utc).isoformat(),
                "source_path": restored_path,
                "previous_path": draft_payload.get("path"),
            },
        )

    @staticmethod
    def _normalize_recovery_payload(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return DraftService._empty_recovery_payload()

        draft_candidate = raw.get("draft") if isinstance(raw.get("draft"), dict) else raw
        if DraftService._is_manual_entry_snapshot(draft_candidate):
            return DraftService._build_payload_from_manual_snapshot(draft_candidate)

        payload = draft_candidate if DraftService._is_draft_payload(draft_candidate) else DraftService._empty_recovery_payload()
        manual_snapshot = raw.get("manual_entry_snapshot")
        if DraftService._is_manual_entry_snapshot(manual_snapshot):
            payload = DraftService._merge_manual_snapshot(payload, manual_snapshot)
        return payload

    @staticmethod
    def _is_draft_payload(candidate: Any) -> bool:
        if not isinstance(candidate, dict):
            return False
        required = {"import_state", "editor_state", "validation_state", "preview_state", "draft_state"}
        return required.issubset(candidate.keys())

    @staticmethod
    def _is_manual_entry_snapshot(candidate: Any) -> bool:
        if not isinstance(candidate, dict):
            return False
        required = {"method", "assays", "analytes", "dilutions", "sample_prep"}
        return required.issubset(candidate.keys())

    @staticmethod
    def _empty_recovery_payload() -> dict[str, Any]:
        return {
            "import_state": asdict(ImportState()),
            "editor_state": asdict(EditorState()),
            "validation_state": asdict(ValidationState()),
            "preview_state": asdict(PreviewState()),
            "draft_state": asdict(DraftState()),
        }

    @staticmethod
    def _build_payload_from_manual_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return DraftService._merge_manual_snapshot(DraftService._empty_recovery_payload(), snapshot)

    @staticmethod
    def _merge_manual_snapshot(payload: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        merged = {
            "import_state": dict(payload.get("import_state", {})),
            "editor_state": dict(payload.get("editor_state", {})),
            "validation_state": dict(payload.get("validation_state", {})),
            "preview_state": dict(payload.get("preview_state", {})),
            "draft_state": dict(payload.get("draft_state", {})),
        }
        bundle = DraftService._manual_snapshot_to_bundle(snapshot)
        import_state = merged["import_state"]
        import_state["bundles"] = [asdict(bundle)]
        import_state["issues"] = []
        import_state["provenance"] = {}
        import_state["review_resolutions"] = {}
        import_state["provenance_lookup"] = {}

        editor_state = merged["editor_state"]
        editor_state.setdefault("sample_prep_overrides", [])
        editor_state.setdefault("dilution_overrides", [])
        return merged

    @staticmethod
    def _manual_snapshot_to_bundle(snapshot: dict[str, Any]) -> InputDTOBundle:
        method_payload = snapshot.get("method", {}) if isinstance(snapshot.get("method"), dict) else {}
        gui_payload = {
            "method_id": "",
            "method_version": "",
            "MethodInformation": {
                "DisplayName": method_payload.get("kit_name", ""),
                "SeriesName": method_payload.get("kit_series", ""),
                "OrderNumber": method_payload.get("kit_product_number", ""),
                "MainTitle": method_payload.get("addon_series", ""),
                "SubTitle": method_payload.get("addon_product_name", ""),
                "ProductNumber": method_payload.get("addon_product_number", ""),
            },
            "assays": snapshot.get("assays", []),
            "analytes": snapshot.get("analytes", []),
        }
        bundle = map_gui_payload_to_bundle(gui_payload)
        bundle.sample_prep_steps = [
            SamplePrepStepInputDTO(
                key=row.get("key") or f"sample-prep-{index + 1}",
                label=row.get("action") or row.get("key") or f"sample-prep-{index + 1}",
                metadata={k: v for k, v in row.items() if k not in {"key"}},
            )
            for index, row in enumerate(snapshot.get("sample_prep", []))
            if isinstance(row, dict)
            and (row.get("action") or row.get("source") or row.get("destination") or row.get("volume") or row.get("duration") or row.get("force"))
        ]
        bundle.dilution_schemes = [
            DilutionSchemeInputDTO(
                key=str(row.get("key") or ""),
                label=str(row.get("key") or ""),
                metadata={k: v for k, v in row.items() if k not in {"key"}},
            )
            for row in snapshot.get("dilutions", [])
            if isinstance(row, dict) and row.get("key")
        ]
        return bundle

    @staticmethod
    def _bundle_from_dict(raw: dict[str, Any]) -> InputDTOBundle:
        method = raw.get("method")
        method_dto = MethodInputDTO(**method) if isinstance(method, dict) else None
        return InputDTOBundle(
            source_type=raw.get("source_type", "default"),
            source_name=raw.get("source_name"),
            method=method_dto,
            assays=DraftService._dto_list(raw.get("assays", []), AssayInputDTO),
            analytes=DraftService._dto_list(raw.get("analytes", []), AnalyteInputDTO),
            units=DraftService._dto_list(raw.get("units", []), UnitInputDTO),
            sample_prep_steps=DraftService._dto_list(raw.get("sample_prep_steps", []), SamplePrepStepInputDTO),
            dilution_schemes=DraftService._dto_list(raw.get("dilution_schemes", []), DilutionSchemeInputDTO),
            method_information_overrides=DraftService._dict_copy(raw.get("method_information_overrides", {})),
            assay_fragments=DraftService._list_of_dicts(raw.get("assay_fragments", [])),
            loading_fragments=DraftService._list_of_dicts(raw.get("loading_fragments", [])),
            processing_fragments=DraftService._list_of_dicts(raw.get("processing_fragments", [])),
            hidden_vocab=DraftService._hidden_vocab(raw.get("hidden_vocab", {})),
            provenance=DraftService._provenance(raw.get("provenance", {})),
        )

    @staticmethod
    def _dto_list(items: Any, dto_type: type[Any]) -> list[Any]:
        if not isinstance(items, list):
            return []
        output: list[Any] = []
        for item in items:
            if isinstance(item, dict):
                output.append(dto_type(**item))
        return output

    @staticmethod
    def _list_of_dicts(items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [dict(item) for item in items if isinstance(item, dict)]

    @staticmethod
    def _dict_copy(raw: Any) -> dict[str, Any]:
        return dict(raw) if isinstance(raw, dict) else {}

    @staticmethod
    def _hidden_vocab(raw: Any) -> dict[str, list[str]]:
        if not isinstance(raw, dict):
            return {}
        out: dict[str, list[str]] = {}
        for key, values in raw.items():
            if isinstance(values, list):
                out[str(key)] = [str(v) for v in values]
        return out

    @staticmethod
    def _provenance(raw: Any) -> dict[str, list[FieldProvenance]]:
        if not isinstance(raw, dict):
            return {}
        out: dict[str, list[FieldProvenance]] = {}
        for key, values in raw.items():
            if not isinstance(values, list):
                continue
            entries: list[FieldProvenance] = []
            for value in values:
                if isinstance(value, dict):
                    entries.append(FieldProvenance(**value))
            out[str(key)] = entries
        return out

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

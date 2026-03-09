from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from addon_generator.ui.state.app_state import AppState
from addon_generator.ui.state.draft_state import DraftState
from addon_generator.ui.state.editor_state import EditorState
from addon_generator.ui.state.import_state import ImportState
from addon_generator.ui.state.preview_state import PreviewState
from addon_generator.ui.state.validation_state import ValidationState
from addon_generator.input_models.dtos import InputDTOBundle, MethodInputDTO


class DraftService:
    def save(self, app_state: AppState, drafts_dir: str = "drafts") -> Path:
        root = Path(drafts_dir)
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = root / f"addon_draft_{stamp}.json"
        payload = {
            "import_state": asdict(app_state.import_state),
            "editor_state": asdict(app_state.editor_state),
            "validation_state": asdict(app_state.validation_state),
            "preview_state": asdict(app_state.preview_state),
            "draft_state": asdict(app_state.draft_state),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        app_state.draft_state.path = str(path)
        app_state.draft_state.payload = payload
        return path

    def load(self, path: str | Path) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

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
            issues=[],
        )
        app_state.editor_state = EditorState(**editor_payload)
        app_state.validation_state = ValidationState(**validation_payload)
        app_state.preview_state = PreviewState(**preview_payload)
        app_state.draft_state = DraftState(
            path=source_path or draft_payload.get("path"),
            payload=payload,
        )

    @staticmethod
    def _bundle_from_dict(raw: dict[str, Any]) -> InputDTOBundle:
        method = raw.get("method")
        method_dto = MethodInputDTO(**method) if isinstance(method, dict) else None
        return InputDTOBundle(
            source_type=raw.get("source_type", "default"),
            source_name=raw.get("source_name"),
            method=method_dto,
        )

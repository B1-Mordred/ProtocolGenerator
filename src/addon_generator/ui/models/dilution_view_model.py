from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Any

from addon_generator.input_models.dtos import DilutionSchemeInputDTO
from addon_generator.ui.services.merge_service_adapter import MergeServiceAdapter
from addon_generator.ui.state.app_state import AppState

DILUTION_FIELDS = ["name", "buffer1_ratio", "buffer2_ratio", "buffer3_ratio"]
RATIO_FIELDS = DILUTION_FIELDS[1:]


@dataclass(slots=True)
class DilutionFieldState:
    value: str = ""
    effective_value: str = ""
    provenance: str = ""
    status: str = "ok"
    is_valid: bool = True
    has_reference: bool = False
    reference_context: str = ""


@dataclass(slots=True)
class DilutionSchemeState:
    dilution_id: str
    fields: dict[str, DilutionFieldState] = field(default_factory=dict)
    row_status: str = "ok"
    provenance_summary: str = "manual"
    is_ratio_valid: bool = True
    is_complete: bool = True
    is_valid: bool = True

    def to_table_row(self) -> list[str]:
        return [
            self.fields["name"].value,
            self.fields["buffer1_ratio"].value,
            self.fields["buffer2_ratio"].value,
            self.fields["buffer3_ratio"].value,
            self.provenance_summary,
            self.row_status,
        ]


class DilutionScreenViewModel:
    def __init__(self, app_state: AppState, merge_adapter: MergeServiceAdapter) -> None:
        self._app_state = app_state
        self._merge_adapter = merge_adapter
        self.dilutions: list[DilutionSchemeState] = []
        self.selected_dilution_id: str | None = None
        self._counter = count(1)
        self.load_from_state()

    def load_from_state(self) -> None:
        merged = self._merge_adapter.recompute(self._app_state) if self._app_state.import_state.bundles else None
        overrides = self._app_state.editor_state.manual_overrides.get("dilution_schemes")
        if isinstance(overrides, list):
            source = overrides
            default_provenance = "manual"
        elif merged is not None:
            source = [self._dto_to_payload(scheme) for scheme in merged.dilution_schemes]
            if not source and self._app_state.import_state.bundles:
                source = [
                    self._dto_to_payload(scheme)
                    for bundle in self._app_state.import_state.bundles
                    for scheme in bundle.dilution_schemes
                ]
            default_provenance = "import"
        else:
            source = []
            default_provenance = ""

        effective_payloads = self._effective_payloads(merged)
        self.dilutions = []
        for index, payload in enumerate(source):
            effective = effective_payloads[index] if index < len(effective_payloads) else payload
            self.dilutions.append(
                self._make_scheme(payload, effective, default_provenance=default_provenance)
            )

        self.selected_dilution_id = self.dilutions[0].dilution_id if self.dilutions else None
        self._validate()

    def add_dilution(self) -> str:
        scheme = self._make_scheme({}, {}, default_provenance="manual")
        self.dilutions.append(scheme)
        self.selected_dilution_id = scheme.dilution_id
        self._commit()
        return scheme.dilution_id

    def delete_dilution(self, dilution_id: str) -> None:
        self.dilutions = [scheme for scheme in self.dilutions if scheme.dilution_id != dilution_id]
        if self.selected_dilution_id == dilution_id:
            self.selected_dilution_id = self.dilutions[0].dilution_id if self.dilutions else None
        self._commit()

    def duplicate_dilution(self, dilution_id: str) -> str | None:
        idx = self._index_of(dilution_id)
        if idx < 0:
            return None
        clone_payload = {name: self.dilutions[idx].fields[name].value for name in DILUTION_FIELDS}
        clone = self._make_scheme(clone_payload, clone_payload, default_provenance="manual")
        self.dilutions.insert(idx + 1, clone)
        self.selected_dilution_id = clone.dilution_id
        self._commit()
        return clone.dilution_id

    def update_field(self, dilution_id: str, field: str, value: str) -> None:
        scheme = self._get_scheme(dilution_id)
        if scheme is None or field not in DILUTION_FIELDS:
            return
        state = scheme.fields[field]
        state.value = value
        state.provenance = "manual"
        self._commit()

    def reset_field(self, dilution_id: str, field: str) -> None:
        scheme = self._get_scheme(dilution_id)
        if scheme is None or field not in DILUTION_FIELDS:
            return
        scheme.fields[field].value = ""
        scheme.fields[field].provenance = ""
        scheme.fields[field].status = "ok"
        scheme.fields[field].is_valid = True
        self._commit()

    def select_dilution(self, dilution_id: str | None) -> None:
        self.selected_dilution_id = dilution_id if dilution_id and self._index_of(dilution_id) >= 0 else None

    def selected_dilution(self) -> DilutionSchemeState | None:
        return self._get_scheme(self.selected_dilution_id) if self.selected_dilution_id else None

    def _commit(self) -> None:
        self._validate()
        self._app_state.editor_state.manual_overrides["dilution_schemes"] = [
            {name: scheme.fields[name].value for name in DILUTION_FIELDS} for scheme in self.dilutions
        ]
        merged = self._merge_adapter.recompute(self._app_state)
        effective_payloads = self._effective_payloads(merged)
        for idx, scheme in enumerate(self.dilutions):
            payload = effective_payloads[idx] if idx < len(effective_payloads) else {}
            for name in DILUTION_FIELDS:
                scheme.fields[name].effective_value = str(payload.get(name, scheme.fields[name].value) or "")

    def _validate(self) -> None:
        for scheme in self.dilutions:
            missing = [name for name in DILUTION_FIELDS if not scheme.fields[name].value.strip()]
            ratio_invalid = any(
                field.value.strip() and (not field.value.strip().isdigit() or int(field.value.strip()) <= 0)
                for field in (scheme.fields[name] for name in RATIO_FIELDS)
            )
            for name, field in scheme.fields.items():
                is_missing = name in missing
                is_ratio_invalid = name in RATIO_FIELDS and field.value.strip() and (
                    not field.value.strip().isdigit() or int(field.value.strip()) <= 0
                )
                field.is_valid = not (is_missing or is_ratio_invalid)
                if is_missing:
                    field.status = "required"
                elif is_ratio_invalid:
                    field.status = "invalid-ratio"
                else:
                    field.status = "ok"

            scheme.is_complete = not missing
            scheme.is_ratio_valid = not ratio_invalid
            scheme.is_valid = scheme.is_complete and scheme.is_ratio_valid
            messages: list[str] = []
            if not scheme.is_complete:
                messages.append("incomplete")
            if not scheme.is_ratio_valid:
                messages.append("invalid ratio")
            scheme.row_status = "ok" if scheme.is_valid else "; ".join(messages)
            scheme.provenance_summary = ", ".join(
                sorted({field.provenance for field in scheme.fields.values() if field.provenance})
            ) or "manual"

    def _make_scheme(
        self,
        payload: dict[str, Any],
        effective_payload: dict[str, Any],
        *,
        default_provenance: str,
    ) -> DilutionSchemeState:
        dilution_id = str(payload.get("dilution_id") or f"dilution-{next(self._counter)}")
        scheme = DilutionSchemeState(
            dilution_id=dilution_id,
            fields={
                name: DilutionFieldState(
                    value=str(payload.get(name, "") or ""),
                    effective_value=str(effective_payload.get(name, payload.get(name, "")) or ""),
                    provenance=default_provenance,
                )
                for name in DILUTION_FIELDS
            },
        )
        metadata = payload.get("_metadata", {}) if isinstance(payload.get("_metadata"), dict) else {}
        for name in DILUTION_FIELDS:
            fstate = scheme.fields[name]
            used_key = f"{name}_ref_used"
            context_key = f"{name}_ref_context"
            fstate.has_reference = bool(metadata.get(used_key) or metadata.get("reference_used"))
            fstate.reference_context = str(metadata.get(context_key) or metadata.get("reference_context") or "")
        provenance_map = self._app_state.import_state.provenance
        for name in DILUTION_FIELDS:
            p_key = f"dilutions.{name}"
            if p_key in provenance_map and provenance_map[p_key]:
                scheme.fields[name].provenance = provenance_map[p_key][0].get("source", default_provenance)
        return scheme

    def _dto_to_payload(self, scheme: DilutionSchemeInputDTO) -> dict[str, Any]:
        metadata = scheme.metadata or {}
        parts = [str(p).strip() for p in str(metadata.get("ratio", "") or "").split(":") if str(p).strip()]
        return {
            "name": str(scheme.label or metadata.get("name", "") or ""),
            "buffer1_ratio": str(metadata.get("buffer1_ratio") or (parts[0] if len(parts) >= 1 else "") or ""),
            "buffer2_ratio": str(metadata.get("buffer2_ratio") or (parts[1] if len(parts) >= 2 else "") or ""),
            "buffer3_ratio": str(metadata.get("buffer3_ratio") or (parts[2] if len(parts) >= 3 else "") or ""),
            "_metadata": metadata,
        }

    def _effective_payloads(self, merged) -> list[dict[str, Any]]:
        if merged is not None:
            return [self._dto_to_payload(scheme) for scheme in merged.dilution_schemes]
        values = self._app_state.editor_state.effective_values.get("dilution_schemes")
        if not isinstance(values, list):
            return []
        payloads: list[dict[str, Any]] = []
        for entry in values:
            if not isinstance(entry, dict):
                continue
            metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
            payloads.append(
                {
                    "name": str(entry.get("label") or metadata.get("name") or ""),
                    "buffer1_ratio": str(metadata.get("buffer1_ratio") or ""),
                    "buffer2_ratio": str(metadata.get("buffer2_ratio") or ""),
                    "buffer3_ratio": str(metadata.get("buffer3_ratio") or ""),
                    "_metadata": metadata,
                }
            )
        return payloads

    def _index_of(self, dilution_id: str | None) -> int:
        if not dilution_id:
            return -1
        for idx, scheme in enumerate(self.dilutions):
            if scheme.dilution_id == dilution_id:
                return idx
        return -1

    def _get_scheme(self, dilution_id: str | None) -> DilutionSchemeState | None:
        idx = self._index_of(dilution_id)
        return self.dilutions[idx] if idx >= 0 else None

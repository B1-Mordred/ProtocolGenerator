from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from addon_generator.domain.fragments import FragmentResolver, FragmentSelectionContext
from addon_generator.domain.models import AddonModel
from addon_generator.mapping.link_resolver import LinkResolver
from addon_generator.mapping.normalizers import normalize_for_matching


@dataclass(slots=True)
class ProtocolJsonGenerationResult:
    payload: dict[str, Any]
    merge_report: dict[str, Any]


class ProtocolJsonGenerator:
    REQUIRED_METHOD_FIELDS = ("Id", "DisplayName", "Version", "MainTitle", "SubTitle", "OrderNumber")

    def __init__(self, resolver: LinkResolver):
        self.resolver = resolver
        self.fragment_resolver = FragmentResolver()

    def generate(self, addon: AddonModel, protocol_fragments: dict[str, Any] | None = None) -> ProtocolJsonGenerationResult:
        defaults = self.resolver.config.raw.get("protocol_defaults", {})
        builtin_method_defaults = {
            "DisplayName": "Method",
            "MainTitle": "Main",
            "SubTitle": "Sub",
            "OrderNumber": "O-1",
            "MaximumNumberOfSamples": 1,
            "MaximumNumberOfProcessingCycles": 1,
            "MaximumNumberOfAssays": max(1, len(addon.assays) if addon.assays else 1),
            "SamplesLayoutType": "SAMPLES_LAYOUT_COMBINED",
            "MethodInformationType": "REGULAR",
        }
        built_method = self._build_method_information(addon, defaults.get("method_information", {}))
        built_assay = self._build_assay_information(addon, defaults.get("assay_information", {}))

        context = addon.protocol_context
        gui_method = dict(context.method_information_overrides) if context else {}
        selection_context = self._build_fragment_selection_context(addon)
        gui_assay = self._resolve_context_fragments("AssayInformation", list(context.assay_fragments) if context and context.assay_fragments else None, selection_context)
        gui_loading = self._resolve_context_fragments("LoadingWorkflowSteps", list(context.loading_fragments) if context and context.loading_fragments else None, selection_context)
        gui_processing = self._resolve_context_fragments("ProcessingWorkflowSteps", list(context.processing_fragments) if context and context.processing_fragments else None, selection_context)

        imported_method = dict(protocol_fragments.get("MethodInformation", {})) if protocol_fragments and isinstance(protocol_fragments.get("MethodInformation"), dict) else {}
        imported_assay = list(protocol_fragments.get("AssayInformation", [])) if protocol_fragments and isinstance(protocol_fragments.get("AssayInformation"), list) and protocol_fragments.get("AssayInformation") else None
        imported_loading = list(protocol_fragments.get("LoadingWorkflowSteps", [])) if protocol_fragments and isinstance(protocol_fragments.get("LoadingWorkflowSteps"), list) and protocol_fragments.get("LoadingWorkflowSteps") else None
        imported_processing = list(protocol_fragments.get("ProcessingWorkflowSteps", [])) if protocol_fragments and isinstance(protocol_fragments.get("ProcessingWorkflowSteps"), list) and protocol_fragments.get("ProcessingWorkflowSteps") else None

        method, method_merge = self._merge_method_information(built_method, gui_method, imported_method, defaults.get("method_information", {}), builtin_method_defaults)
        assay_info, assay_merge = self._resolve_section("AssayInformation", gui_assay, imported_assay, built_assay, [{"Type": "A", "DisplayName": "Assay"}])
        loading, loading_merge = self._resolve_section("LoadingWorkflowSteps", gui_loading, imported_loading, self._build_loading_workflow_steps(addon, defaults.get("loading_workflow_steps", [])), [], allow_empty=False)
        processing, processing_merge = self._resolve_section("ProcessingWorkflowSteps", gui_processing, imported_processing, self._build_processing_workflow_steps(addon, defaults.get("processing_workflow_steps", [])), [], allow_empty=False)

        payload = {
            "MethodInformation": method,
            "AssayInformation": assay_info,
            "LoadingWorkflowSteps": loading,
            "ProcessingWorkflowSteps": processing,
        }
        merge_report = self._build_merge_report(method, [*method_merge, assay_merge, loading_merge, processing_merge])
        return ProtocolJsonGenerationResult(payload=payload, merge_report=merge_report)

    def _build_method_information(self, addon: AddonModel, defaults: dict[str, Any]) -> dict[str, Any]:
        projection = self.resolver.resolve_method_projection(addon)
        method = addon.method
        return {
            "Id": projection.protocol_id,
            "DisplayName": self._resolve_required_default(method.display_name if method else None, defaults.get("DisplayName"), "Method"),
            "Version": projection.protocol_version,
            "MainTitle": self._resolve_required_default(method.main_title if method else None, defaults.get("MainTitle"), "Main"),
            "SubTitle": self._resolve_required_default(method.sub_title if method else None, defaults.get("SubTitle"), "Sub"),
            "OrderNumber": self._resolve_required_default(method.order_number if method else None, defaults.get("OrderNumber"), "O-1"),
            "MaximumNumberOfSamples": int(defaults.get("MaximumNumberOfSamples", 1)),
            "MaximumNumberOfProcessingCycles": int(defaults.get("MaximumNumberOfProcessingCycles", 1)),
            "MaximumNumberOfAssays": max(1, int(defaults.get("MaximumNumberOfAssays", len(addon.assays) if addon.assays else 1))),
            "SamplesLayoutType": "SAMPLES_LAYOUT_SEPARATE" if len(addon.assays) > 1 else defaults.get("SamplesLayoutType", "SAMPLES_LAYOUT_COMBINED"),
            "MethodInformationType": defaults.get("MethodInformationType", "REGULAR"),
        }

    def _build_assay_information(self, addon: AddonModel, defaults: dict[str, Any]) -> list[dict[str, Any]]:
        assays: list[dict[str, Any]] = []
        normalized_types: dict[str, str] = {}
        for assay in sorted(addon.assays, key=lambda a: a.key):
            projection = self.resolver.resolve_assay_projection(assay)
            assay_type = projection.protocol_type or projection.xml_name
            assay_record = dict(defaults)
            assay_record.update({
                "Type": assay_type,
                "DisplayName": projection.protocol_display_name or projection.xml_name or defaults.get("DisplayName", "Assay"),
            })
            canonical_type = normalize_for_matching(assay_type)
            existing = normalized_types.get(canonical_type)
            if canonical_type and existing and existing != assay.key:
                raise ValueError(f"Ambiguous assay projection: '{assay.key}' and '{existing}' normalize to the same Type '{assay_type}'")
            if canonical_type:
                normalized_types[canonical_type] = assay.key
            assays.append(assay_record)
        if not assays:
            assay_record = dict(defaults)
            assay_record.update({"Type": "A", "DisplayName": defaults.get("DisplayName", "Assay")})
            assays.append(assay_record)
        return assays

    def _build_loading_workflow_steps(self, addon: AddonModel, defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not defaults:
            return []
        return [dict(step) for step in defaults]

    def _build_processing_workflow_steps(self, addon: AddonModel, defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not defaults:
            return []
        if len(addon.assays) <= 1:
            return [dict(step) for step in defaults]
        per_assay_steps: list[dict[str, Any]] = []
        template = defaults[0]
        for idx, assay in enumerate(sorted(addon.assays, key=lambda a: a.key)):
            projection = self.resolver.resolve_assay_projection(assay)
            assay_group = dict(template)
            assay_group["GroupIndex"] = idx
            assay_group["GroupDisplayName"] = projection.protocol_display_name or projection.protocol_type or assay.key
            per_assay_steps.append(assay_group)
        return per_assay_steps

    def _build_fragment_selection_context(self, addon: AddonModel) -> FragmentSelectionContext:
        metadata = addon.source_metadata if isinstance(addon.source_metadata, dict) else {}
        return FragmentSelectionContext(
            assay_family=metadata.get("assay_family"),
            reagent=metadata.get("reagent"),
            dilution=metadata.get("dilution"),
            instrument=metadata.get("instrument"),
            config=metadata.get("config"),
        )

    def _resolve_context_fragments(self, section: str, raw_fragments: list[dict[str, Any]] | None, context: FragmentSelectionContext) -> Any:
        if not raw_fragments:
            return None
        resolved = self.fragment_resolver.resolve(section=section, raw_fragments=raw_fragments, context=context)
        if section == "AssayInformation" and resolved is not None and not isinstance(resolved, list):
            return [resolved]
        return resolved

    def _merge_method_information(
        self,
        generated: dict[str, Any],
        gui_overrides: dict[str, Any],
        imported_overrides: dict[str, Any],
        config_defaults: dict[str, Any],
        builtin_defaults: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        merged = dict(generated)
        records: list[dict[str, Any]] = []
        candidate_keys = sorted(set(generated) | set(gui_overrides) | set(imported_overrides) | set(config_defaults) | set(builtin_defaults))
        for key in candidate_keys:
            values = {
                "gui": gui_overrides.get(key),
                "imported": imported_overrides.get(key),
                "generated": generated.get(key),
                "config_default": config_defaults.get(key),
                "built_in_default": builtin_defaults.get(key),
            }
            selected_source = "generated"
            selected_value = values["generated"]
            for source in ("gui", "imported", "generated", "config_default", "built_in_default"):
                if self._has_value(values[source]):
                    selected_source = source
                    selected_value = values[source]
                    break
            merged[key] = selected_value

            present = {source: value for source, value in values.items() if self._has_value(value)}
            conflict_sources = sorted([source for source, value in present.items() if value != selected_value])
            records.append({
                "path": f"MethodInformation.{key}",
                "source": selected_source,
                "value": selected_value,
                "conflict": bool(conflict_sources),
                "conflict_sources": conflict_sources,
            })
        return merged, records

    def _resolve_section(self, section: str, gui: Any, imported: Any, config_default: Any, built_in_default: Any, *, allow_empty: bool = True) -> tuple[Any, dict[str, Any]]:
        values = {
            "gui": gui,
            "imported": imported,
            "config_default": config_default,
            "built_in_default": built_in_default,
        }
        selected_source = "built_in_default"
        selected_value = values["built_in_default"]
        for source in ("gui", "imported", "config_default", "built_in_default"):
            if self._has_value(values[source]):
                selected_source = source
                selected_value = values[source]
                break
        if not allow_empty and not self._has_value(selected_value):
            selected_source = "built_in_default"
            selected_value = []
        present = {source: value for source, value in values.items() if self._has_value(value)}
        conflict_sources = sorted([source for source, value in present.items() if value != selected_value])
        return selected_value, {
            "path": section,
            "source": selected_source,
            "value": selected_value,
            "conflict": bool(conflict_sources),
            "conflict_sources": conflict_sources,
        }

    def _build_merge_report(self, method_information: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        unresolved_required = sorted(
            [
                f"MethodInformation.{field}"
                for field in self.REQUIRED_METHOD_FIELDS
                if not self._has_value(method_information.get(field))
            ]
        )
        conflicting_required = sorted(
            [
                record["path"]
                for record in records
                if record["path"] in {f"MethodInformation.{field}" for field in self.REQUIRED_METHOD_FIELDS} and record["conflict"]
            ]
        )
        return {
            "field_provenance": sorted(records, key=lambda item: item["path"]),
            "required_fields": {
                "unresolved": unresolved_required,
                "conflicting": conflicting_required,
            },
        }

    @staticmethod
    def _has_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True

    @staticmethod
    def _resolve_required_default(primary: Any, fallback: Any, hard_default: Any) -> Any:
        if primary is not None and str(primary).strip() != "":
            return primary
        if fallback is not None and str(fallback).strip() != "":
            return fallback
        return hard_default


def generate_protocol_json(addon: AddonModel, resolver: LinkResolver, protocol_fragments: dict[str, Any] | None = None) -> ProtocolJsonGenerationResult:
    return ProtocolJsonGenerator(resolver).generate(addon, protocol_fragments)

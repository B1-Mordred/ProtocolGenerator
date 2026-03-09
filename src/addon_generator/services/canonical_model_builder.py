from __future__ import annotations

from dataclasses import asdict

from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.input_models.dtos import InputDTOBundle
from addon_generator.services.canonical_normalizer import normalize_empty_container, normalize_optional_text, normalize_text, normalize_value


class CanonicalModelBuilder:
    def build(self, bundle: InputDTOBundle) -> AddonModel:
        method = None
        if bundle.method is not None:
            method = MethodModel(
                key=normalize_text(bundle.method.key),
                method_id=normalize_text(bundle.method.method_id),
                method_version=normalize_text(bundle.method.method_version),
                display_name=normalize_optional_text(bundle.method.display_name),
                main_title=normalize_optional_text(bundle.method.main_title),
                sub_title=normalize_optional_text(bundle.method.sub_title),
                order_number=normalize_optional_text(bundle.method.order_number),
                series_name=normalize_optional_text(bundle.method.series_name),
                product_name=normalize_optional_text(bundle.method.product_name),
                product_number=normalize_optional_text(bundle.method.product_number),
                legacy_protocol_id=normalize_optional_text(bundle.method.legacy_protocol_id),
            )

        assays = [
            AssayModel(
                key=normalize_text(item.key),
                protocol_type=normalize_optional_text(item.protocol_type),
                protocol_display_name=normalize_optional_text(item.protocol_display_name),
                xml_name=normalize_optional_text(item.xml_name),
                aliases=normalize_value(item.aliases) or [],
                metadata=normalize_value(item.metadata) or {},
            )
            for item in bundle.assays
        ]
        analytes = [
            AnalyteModel(
                key=normalize_text(item.key),
                name=normalize_text(item.name),
                assay_key=normalize_text(item.assay_key),
                assay_information_type=normalize_optional_text(item.assay_information_type),
                metadata=normalize_value(item.metadata) or {},
            )
            for item in bundle.analytes
        ]
        units = [
            AnalyteUnitModel(
                key=normalize_text(item.key),
                name=normalize_text(item.name),
                analyte_key=normalize_text(item.analyte_key),
                metadata=normalize_value(item.metadata) or {},
            )
            for item in bundle.units
        ]

        units_by_analyte: dict[str, list[str]] = {}
        for unit in units:
            units_by_analyte.setdefault(unit.analyte_key, []).append(unit.key)
        for analyte in analytes:
            analyte.unit_keys = sorted(set(units_by_analyte.get(analyte.key, [])))

        protocol_context = ProtocolContextModel(
            method_information_overrides=normalize_value(bundle.method_information_overrides) or {},
            assay_fragments=normalize_value(bundle.assay_fragments) or [],
            loading_fragments=normalize_value(bundle.loading_fragments) or [],
            processing_fragments=normalize_value(bundle.processing_fragments) or [],
        )

        return AddonModel(
            addon_id=0,
            method=method,
            assays=assays,
            analytes=analytes,
            units=units,
            protocol_context=protocol_context,
            source_metadata={
                "source": normalize_optional_text(bundle.source_type),
                "source_name": normalize_optional_text(bundle.source_name),
                "provenance": normalize_empty_container({k: [asdict(item) for item in v] for k, v in bundle.provenance.items()}),
                "hidden_vocab": normalize_value(bundle.hidden_vocab),
                "sample_prep_steps": normalize_value([asdict(step) for step in bundle.sample_prep_steps]),
                "dilution_schemes": normalize_value([asdict(scheme) for scheme in bundle.dilution_schemes]),
            },
        )

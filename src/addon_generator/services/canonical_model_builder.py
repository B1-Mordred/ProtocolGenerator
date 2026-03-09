from __future__ import annotations

from dataclasses import asdict

from addon_generator.domain.models import AddonModel, AnalyteModel, AnalyteUnitModel, AssayModel, MethodModel, ProtocolContextModel
from addon_generator.input_models.dtos import InputDTOBundle


class CanonicalModelBuilder:
    def build(self, bundle: InputDTOBundle) -> AddonModel:
        method = None
        if bundle.method is not None:
            method = MethodModel(
                key=bundle.method.key,
                method_id=bundle.method.method_id,
                method_version=bundle.method.method_version,
                display_name=bundle.method.display_name,
                main_title=bundle.method.main_title,
                sub_title=bundle.method.sub_title,
                order_number=bundle.method.order_number,
                series_name=bundle.method.series_name,
                product_name=bundle.method.product_name,
                product_number=bundle.method.product_number,
                legacy_protocol_id=bundle.method.legacy_protocol_id,
            )

        assays = [
            AssayModel(
                key=item.key,
                protocol_type=item.protocol_type,
                protocol_display_name=item.protocol_display_name,
                xml_name=item.xml_name,
                aliases=list(item.aliases),
                metadata=dict(item.metadata),
            )
            for item in bundle.assays
        ]
        analytes = [
            AnalyteModel(
                key=item.key,
                name=item.name,
                assay_key=item.assay_key,
                assay_information_type=item.assay_information_type,
                metadata=dict(item.metadata),
            )
            for item in bundle.analytes
        ]
        units = [
            AnalyteUnitModel(
                key=item.key,
                name=item.name,
                analyte_key=item.analyte_key,
                metadata=dict(item.metadata),
            )
            for item in bundle.units
        ]

        units_by_analyte: dict[str, list[str]] = {}
        for unit in units:
            units_by_analyte.setdefault(unit.analyte_key, []).append(unit.key)
        for analyte in analytes:
            analyte.unit_keys = sorted(set(units_by_analyte.get(analyte.key, [])))

        protocol_context = ProtocolContextModel(
            method_information_overrides=dict(bundle.method_information_overrides),
            assay_fragments=list(bundle.assay_fragments),
            loading_fragments=list(bundle.loading_fragments),
            processing_fragments=list(bundle.processing_fragments),
        )

        return AddonModel(
            addon_id=0,
            method=method,
            assays=assays,
            analytes=analytes,
            units=units,
            protocol_context=protocol_context,
            source_metadata={
                "source": bundle.source_type,
                "source_name": bundle.source_name,
                "provenance": {k: [asdict(item) for item in v] for k, v in bundle.provenance.items()},
            },
        )

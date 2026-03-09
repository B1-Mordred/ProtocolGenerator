from __future__ import annotations

from addon_generator.domain.models import AddonModel


def assign_deterministic_ids(addon: AddonModel, *, assay_start: int = 0, analyte_start: int = 0, unit_start: int = 0) -> AddonModel:
    addon.addon_id = 0

    assay_id = assay_start
    for assay in sorted(addon.assays, key=lambda a: a.key):
        assay.xml_id = assay_id
        assay.addon_ref = addon.addon_id
        assay_id += 1

    assay_id_by_key = {assay.key: assay.xml_id for assay in addon.assays}

    analyte_id = analyte_start
    for analyte in sorted(addon.analytes, key=lambda a: (a.assay_key, a.name, a.key)):
        analyte.xml_id = analyte_id
        analyte.assay_ref = assay_id_by_key.get(analyte.assay_key)
        analyte_id += 1

    analyte_id_by_key = {analyte.key: analyte.xml_id for analyte in addon.analytes}

    unit_id = unit_start
    for unit in sorted(addon.units, key=lambda u: (u.analyte_key, u.name, u.key)):
        unit.xml_id = unit_id
        unit.analyte_ref = analyte_id_by_key.get(unit.analyte_key)
        unit_id += 1

    return addon

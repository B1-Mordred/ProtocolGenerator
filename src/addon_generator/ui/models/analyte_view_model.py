from dataclasses import dataclass


@dataclass(slots=True)
class AnalyteViewModel:
    analyte_name: str
    unit: str = ""
    linked_assay: str = ""
    parameter_set: str = ""
    source: str = ""
    status: str = ""

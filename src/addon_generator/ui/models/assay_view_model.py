from dataclasses import dataclass


@dataclass(slots=True)
class AssayViewModel:
    internal_key: str
    protocol_type: str = ""
    protocol_display_name: str = ""
    xml_assay_name: str = ""
    parameter_set_number: str = ""
    assay_abbreviation: str = ""
    source: str = ""

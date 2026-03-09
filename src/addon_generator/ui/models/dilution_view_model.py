from dataclasses import dataclass


@dataclass(slots=True)
class DilutionViewModel:
    dilution_name: str
    buffer1_ratio: str = ""
    buffer2_ratio: str = ""
    buffer3_ratio: str = ""
    status: str = ""

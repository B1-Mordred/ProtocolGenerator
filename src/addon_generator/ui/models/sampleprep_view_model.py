from dataclasses import dataclass


@dataclass(slots=True)
class SamplePrepViewModel:
    order: int
    action: str = ""
    source: str = ""
    destination: str = ""
    volume: str = ""
    duration: str = ""
    force: str = ""

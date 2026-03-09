from dataclasses import dataclass


@dataclass(slots=True)
class MethodViewModel:
    method_id: str = ""
    method_version: str = ""
    display_name: str = ""
    kit_series: str = ""
    kit_product_number: str = ""
    addon_series: str = ""
    addon_product_name: str = ""
    addon_product_number: str = ""

from __future__ import annotations

import json
from pathlib import Path

from addon_generator.services.generation_service import GenerationService


SCENARIOS: dict[str, dict] = {
    "basic-gui": {
        "method_id": "M-1",
        "method_version": "1.0",
        "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
        "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
        "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
    },
    "multi-assay-groups": {
        "method_id": "M-2A",
        "method_version": "2.0",
        "assays": [
            {"key": "assay:chem", "protocol_type": "CHEM", "xml_name": "CHEM", "protocol_display_name": "Chem"},
            {"key": "assay:immuno", "protocol_type": "IMM", "xml_name": "IMM", "protocol_display_name": "Immuno"},
        ],
        "analytes": [
            {"key": "a1", "name": "GLU", "assay_key": "assay:chem"},
            {"key": "a2", "name": "TSH", "assay_key": "assay:immuno"},
        ],
        "units": [
            {"key": "u1", "name": "mg/dL", "analyte_key": "a1"},
            {"key": "u2", "name": "uIU/mL", "analyte_key": "a2"},
        ],
    },
    "gui-fragments-deterministic": {
        "method_id": "M-R",
        "method_version": "3.0",
        "MethodInformation": {"DisplayName": "GUI Preferred"},
        "assays": [{"key": "assay:1", "protocol_type": "A", "xml_name": "A"}],
        "analytes": [{"key": "analyte:1", "name": "GLU", "assay_key": "assay:1"}],
        "units": [{"key": "unit:1", "name": "mg/dL", "analyte_key": "analyte:1"}],
    },
}


if __name__ == "__main__":
    service = GenerationService()
    golden_root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden" / "addon-generation"

    for scenario, payload in SCENARIOS.items():
        result = service.generate_all(service.import_from_gui_payload(payload))
        out_dir = golden_root / scenario
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ProtocolFile.json").write_text(
            json.dumps(result.protocol_json, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "Analytes.xml").write_text(result.analytes_xml_string, encoding="utf-8")
        print(f"updated {scenario}")

from __future__ import annotations

import json
from pathlib import Path

from addon_generator.importers.xml_importer import XmlImporter
from addon_generator.services.generation_service import GenerationService, fragments_from_protocol_payload
from addon_generator.validation.cross_file_validator import validate_cross_file_consistency


def _sample_gui_payload() -> dict[str, object]:
    return {
        "MethodInformation": {"Id": 1, "DisplayName": "Chemistry Method", "Version": "1.0"},
        "AssayInformation": [{"Type": "Panel B"}, {"Type": "Panel A"}],
        "rows": [
            {
                "MethodDisplayName": "Chemistry Method",
                "AssayDisplayName": "Panel B",
                "AnalyteName": "Glucose",
                "UnitName": "mg/dL",
            },
            {
                "MethodDisplayName": "Chemistry Method",
                "AssayDisplayName": "Panel A",
                "AnalyteName": "Sodium",
                "UnitName": "mmol/L",
            },
            {
                "MethodDisplayName": "Chemistry Method",
                "AssayDisplayName": "Panel B",
                "AnalyteName": "Glucose",
                "UnitName": "g/L",
            },
        ],
    }


def test_import_xml_to_canonical_then_generates_deterministic_analytes_xml(tmp_path: Path) -> None:
    source_xml = tmp_path / "input.xml"
    source_xml.write_text(
        """
<AddOn Name="Imported Method" Id="9">
  <Assays>
    <Assay Name="Panel Z">
      <Analytes>
        <Analyte Name="Lactate">
          <AnalyteUnits>
            <AnalyteUnit Name="mmol/L" />
            <AnalyteUnit Name="mg/dL" />
          </AnalyteUnits>
        </Analyte>
      </Analytes>
    </Assay>
  </Assays>
</AddOn>
""".strip(),
        encoding="utf-8",
    )

    context = XmlImporter().import_xml(source_xml)
    xml_result = GenerationService().generate_analytes_xml(context, xsd_path=tmp_path / "missing.AddOn.xsd")

    assert "<AssayRef>1</AssayRef>" in xml_result.xml_content
    assert xml_result.xml_content.index("<UnitRef>1</UnitRef>") < xml_result.xml_content.index("<UnitRef>2</UnitRef>")


def test_canonical_to_protocol_file_json_and_cross_file_validation() -> None:
    service = GenerationService()
    payload = _sample_gui_payload()

    context = service.import_from_gui_payload(payload)
    fragments = fragments_from_protocol_payload(payload)
    protocol_result = service.generate_protocol_json(context, fragments)
    cross_file = validate_cross_file_consistency(context, protocol_result.payload)

    assert protocol_result.payload["MethodInformation"]["Id"] == 1
    assert [record["Type"] for record in protocol_result.payload["AssayInformation"]] == ["Panel B", "Panel A"]
    assert cross_file.is_valid is True


def test_golden_fixtures_for_protocol_json_and_analytes_xml_are_stable() -> None:
    service = GenerationService()
    payload = _sample_gui_payload()
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

    context = service.import_from_gui_payload(payload)
    fragments = fragments_from_protocol_payload(payload)

    protocol_payload = service.generate_protocol_json(context, fragments).payload
    protocol_rendered = json.dumps(protocol_payload, indent=2, sort_keys=True) + "\n"
    expected_protocol = (fixtures_dir / "protocol_file.expected.json").read_text(encoding="utf-8")
    assert protocol_rendered == expected_protocol

    xml_rendered = service.generate_analytes_xml(context, xsd_path=fixtures_dir / "missing.AddOn.xsd").xml_content.rstrip() + "\n"
    expected_xml = (fixtures_dir / "analytes.expected.xml").read_text(encoding="utf-8")
    assert xml_rendered == expected_xml

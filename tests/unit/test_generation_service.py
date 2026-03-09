from addon_generator.services.generation_service import GenerationService


def test_generation_service_import_and_domain_validation() -> None:
    service = GenerationService()
    addon = service.import_from_gui_payload({"method_id": "M", "method_version": "1", "assays": [], "analytes": [], "units": []})
    issues = service.validate_domain(addon)
    assert issues.has_errors() is False

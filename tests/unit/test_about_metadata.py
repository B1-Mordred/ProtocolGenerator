from __future__ import annotations

from pathlib import Path

from addon_generator.__about__ import (
    __app_name__,
    __company__,
    __config_schema_version__,
    __draft_format_version__,
    __version__,
    about_payload,
)


def test_about_constants_are_defined() -> None:
    assert __app_name__
    assert __company__
    assert __version__
    assert __draft_format_version__
    assert __config_schema_version__


def test_about_payload_contains_expected_metadata() -> None:
    assert about_payload() == {
        "app_name": __app_name__,
        "version": __version__,
        "company": __company__,
        "draft_format_version": __draft_format_version__,
        "config_schema_version": __config_schema_version__,
    }


def test_pyproject_uses_dynamic_version_from_about_module() -> None:
    content = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'dynamic = ["version"]' in content
    assert 'version = {attr = "addon_generator.__about__.__version__"}' in content

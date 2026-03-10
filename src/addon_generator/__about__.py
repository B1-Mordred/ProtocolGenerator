"""Canonical application/build metadata for addon_generator."""

__app_name__ = "AddOn Authoring"
__version__ = "0.1.0"
__company__ = "Protocol Generator"
__draft_format_version__ = "1"
__config_schema_version__ = "1"


def about_payload() -> dict[str, str]:
    """Return a stable metadata payload for UI/build artifacts."""

    return {
        "app_name": __app_name__,
        "version": __version__,
        "company": __company__,
        "draft_format_version": __draft_format_version__,
        "config_schema_version": __config_schema_version__,
    }

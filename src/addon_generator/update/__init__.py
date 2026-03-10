from addon_generator.update.artifact import compute_sha256, download_artifact, verify_sha256
from addon_generator.update.installer import launch_installer, write_restart_handoff
from addon_generator.update.manifest import (
    ArtifactManifest,
    ReleaseManifest,
    current_platform_key,
    fetch_manifest,
    parse_manifest,
    select_artifact_for_platform,
)
from addon_generator.update.versioning import compare_versions, is_update_available, local_version

__all__ = [
    "ArtifactManifest",
    "ReleaseManifest",
    "compare_versions",
    "compute_sha256",
    "current_platform_key",
    "download_artifact",
    "fetch_manifest",
    "is_update_available",
    "launch_installer",
    "local_version",
    "parse_manifest",
    "select_artifact_for_platform",
    "verify_sha256",
    "write_restart_handoff",
]

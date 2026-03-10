from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from addon_generator.update.artifact import download_artifact, verify_sha256
from addon_generator.update.installer import launch_installer, write_restart_handoff
from addon_generator.update.manifest import fetch_manifest, parse_manifest, select_artifact_for_platform
from addon_generator.update.versioning import is_update_available, local_version

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpdateResult:
    status: str
    current_version: str
    available_version: str | None = None
    artifact_path: str | None = None
    details: str | None = None


class UpdateService:
    def check(self, *, manifest_url: str) -> tuple[UpdateResult, dict[str, str] | None]:
        try:
            current = local_version()
            manifest_payload = fetch_manifest(manifest_url)
            manifest = parse_manifest(manifest_payload)
            if not is_update_available(current, manifest.version):
                return (
                    UpdateResult(status="up-to-date", current_version=current, available_version=manifest.version, details="No update available."),
                    None,
                )
            return (
                UpdateResult(
                    status="available",
                    current_version=current,
                    available_version=manifest.version,
                    details="An update is available.",
                ),
                None,
            )
        except Exception as exc:  # pragma: no cover - runtime path depends on external systems
            LOGGER.exception("Update check failed")
            return (
                UpdateResult(status="failed", current_version=local_version(), details=str(exc)),
                {
                    "code": "update-check-failed",
                    "message": f"Update check failed: {exc}",
                },
            )

    def stage_update(self, *, manifest_url: str, download_dir: Path, restart_command: list[str]) -> tuple[UpdateResult, dict[str, str] | None]:
        try:
            current = local_version()
            manifest_payload = fetch_manifest(manifest_url)
            manifest = parse_manifest(manifest_payload)
            if not is_update_available(current, manifest.version):
                return (
                    UpdateResult(status="up-to-date", current_version=current, available_version=manifest.version, details="No update available."),
                    None,
                )

            artifact = select_artifact_for_platform(manifest)
            artifact_name = Path(artifact.url).name or f"addon-generator-{manifest.version}"
            artifact_path = download_artifact(artifact.url, download_dir / artifact_name)

            if not verify_sha256(artifact_path, artifact.sha256):
                artifact_path.unlink(missing_ok=True)
                raise RuntimeError("Downloaded installer hash did not match manifest SHA256")

            handoff_path = write_restart_handoff(download_dir / "restart-handoff.json", restart_command)
            launch_installer(artifact_path, handoff_path=handoff_path)
            return (
                UpdateResult(
                    status="staged",
                    current_version=current,
                    available_version=manifest.version,
                    artifact_path=str(artifact_path),
                    details="Installer launched. Application restart handoff written.",
                ),
                None,
            )
        except Exception as exc:  # pragma: no cover - runtime path depends on external systems
            LOGGER.exception("Update stage failed")
            return (
                UpdateResult(status="failed", current_version=local_version(), details=str(exc)),
                {
                    "code": "update-flow-failed",
                    "message": f"Update failed: {exc}",
                },
            )

    def check_and_stage(self, *, manifest_url: str, download_dir: Path, restart_command: list[str]) -> tuple[UpdateResult, dict[str, str] | None]:
        return self.stage_update(manifest_url=manifest_url, download_dir=download_dir, restart_command=restart_command)

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen
import platform


@dataclass(frozen=True)
class ArtifactManifest:
    platform: str
    url: str
    sha256: str
    installer_type: str


@dataclass(frozen=True)
class ReleaseManifest:
    version: str
    channel: str
    published_at: str
    release_notes: str
    artifacts: dict[str, ArtifactManifest]



def fetch_manifest(manifest_url: str, *, timeout_seconds: float = 10.0) -> dict[str, object]:
    req = Request(manifest_url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310 - trusted endpoint supplied by app config
        payload = response.read().decode("utf-8")
    return json.loads(payload)



def parse_manifest(payload: dict[str, object]) -> ReleaseManifest:
    version = str(payload["version"])
    channel = str(payload["channel"])
    published_at = str(payload["published_at"])
    release_notes = str(payload.get("release_notes", ""))
    artifacts_node = payload["artifacts"]
    if not isinstance(artifacts_node, dict):
        raise ValueError("Manifest artifacts must be an object keyed by platform")
    artifacts: dict[str, ArtifactManifest] = {}
    for key, value in artifacts_node.items():
        if not isinstance(value, dict):
            raise ValueError(f"Artifact {key!r} must be an object")
        artifacts[str(key)] = ArtifactManifest(
            platform=str(value.get("platform", key)),
            url=str(value["url"]),
            sha256=str(value["sha256"]).lower(),
            installer_type=str(value.get("installer_type", "binary")),
        )
    return ReleaseManifest(
        version=version,
        channel=channel,
        published_at=published_at,
        release_notes=release_notes,
        artifacts=artifacts,
    )



def current_platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "arm64": "aarch64",
    }
    return f"{system}-{aliases.get(machine, machine)}"



def select_artifact_for_platform(manifest: ReleaseManifest, *, platform_key: str | None = None) -> ArtifactManifest:
    key = platform_key or current_platform_key()
    artifact = manifest.artifacts.get(key)
    if artifact is None:
        raise KeyError(f"No artifact available for platform {key!r}")
    return artifact

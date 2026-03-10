from __future__ import annotations

import hashlib

import pytest

from addon_generator.update.artifact import verify_sha256
from addon_generator.update.manifest import parse_manifest, select_artifact_for_platform
from addon_generator.update.versioning import compare_versions, is_update_available


@pytest.mark.parametrize(
    ("current", "available", "expected"),
    [
        ("1.0.0", "1.0.1", -1),
        ("1.2.0", "1.1.9", 1),
        ("1.2.3", "1.2.3", 0),
        ("1.2.3-alpha.1", "1.2.3", -1),
        ("1.2.3", "1.2.3-alpha.1", 1),
    ],
)
def test_compare_versions(current: str, available: str, expected: int) -> None:
    assert compare_versions(current, available) == expected


def test_is_update_available_true_only_for_newer_version() -> None:
    assert is_update_available("0.1.0", "0.1.1")
    assert not is_update_available("0.1.1", "0.1.1")


def test_manifest_parse_and_platform_selection() -> None:
    manifest = parse_manifest(
        {
            "channel": "stable",
            "version": "2.0.0",
            "published_at": "2026-03-10T00:00:00Z",
            "artifacts": {
                "linux-x86_64": {
                    "platform": "linux-x86_64",
                    "url": "https://example.invalid/linux.AppImage",
                    "sha256": "a" * 64,
                    "installer_type": "appimage",
                }
            },
        }
    )

    artifact = select_artifact_for_platform(manifest, platform_key="linux-x86_64")
    assert artifact.url.endswith("linux.AppImage")
    assert artifact.sha256 == "a" * 64



def test_select_artifact_for_missing_platform_raises() -> None:
    manifest = parse_manifest(
        {
            "channel": "stable",
            "version": "2.0.0",
            "published_at": "2026-03-10T00:00:00Z",
            "artifacts": {
                "windows-x86_64": {
                    "platform": "windows-x86_64",
                    "url": "https://example.invalid/windows.exe",
                    "sha256": "b" * 64,
                }
            },
        }
    )

    with pytest.raises(KeyError):
        select_artifact_for_platform(manifest, platform_key="linux-x86_64")



def test_verify_sha256(tmp_path) -> None:
    payload = b"release-binary"
    artifact_path = tmp_path / "artifact.bin"
    artifact_path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    assert verify_sha256(artifact_path, expected)
    assert not verify_sha256(artifact_path, "0" * 64)

#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from addon_generator.update.artifact import compute_sha256

_PLATFORM_PATTERN = re.compile(r"-(windows|linux|darwin)-(x86_64|aarch64)")


def infer_platform(path: Path) -> str:
    match = _PLATFORM_PATTERN.search(path.stem)
    if not match:
        raise ValueError(f"Unable to infer platform from artifact name: {path.name}")
    return f"{match.group(1)}-{match.group(2)}"


def infer_installer_type(path: Path) -> str:
    return path.suffix.lstrip(".").lower() or "binary"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deploy/manifests/update.json from release artifacts")
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", default="stable")
    parser.add_argument("--base-url", required=True, help="Base HTTPS URL where artifacts are published")
    parser.add_argument("--release-notes", default="")
    parser.add_argument("--published-at", default=datetime.now(tz=timezone.utc).isoformat())
    parser.add_argument("--output", default="deploy/manifests/update.json")
    parser.add_argument("artifacts", nargs="+", help="Artifact files to include")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    artifacts: dict[str, dict[str, str]] = {}
    for artifact_arg in args.artifacts:
        artifact_path = Path(artifact_arg)
        platform_key = infer_platform(artifact_path)
        artifacts[platform_key] = {
            "platform": platform_key,
            "installer_type": infer_installer_type(artifact_path),
            "url": f"{base_url}/{artifact_path.name}",
            "sha256": compute_sha256(artifact_path),
        }

    manifest = {
        "channel": args.channel,
        "version": args.version,
        "published_at": args.published_at,
        "release_notes": args.release_notes,
        "artifacts": artifacts,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output_path} with {len(artifacts)} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

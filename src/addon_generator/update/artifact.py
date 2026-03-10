from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import urlopen



def download_artifact(url: str, destination: Path, *, timeout_seconds: float = 30.0) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - trusted URL provided by release manifest
        destination.write_bytes(response.read())
    return destination



def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            digest.update(chunk)
    return digest.hexdigest()



def verify_sha256(path: Path, expected_sha256: str) -> bool:
    return compute_sha256(path) == expected_sha256.lower()

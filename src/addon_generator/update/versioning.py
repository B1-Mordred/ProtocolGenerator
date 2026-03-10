from __future__ import annotations

from dataclasses import dataclass
import re

from addon_generator.__about__ import __version__

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, raw: str) -> "SemanticVersion":
        match = _SEMVER_RE.match(raw.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {raw!r}")
        prerelease_raw = match.group("prerelease")
        prerelease = tuple(prerelease_raw.split(".")) if prerelease_raw else ()
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=prerelease,
        )



def local_version() -> str:
    return __version__



def compare_versions(current: str, available: str) -> int:
    current_v = SemanticVersion.parse(current)
    available_v = SemanticVersion.parse(available)
    core_cmp = _compare_core(current_v, available_v)
    if core_cmp != 0:
        return core_cmp
    return _compare_prerelease(current_v.prerelease, available_v.prerelease)



def is_update_available(current: str, available: str) -> bool:
    return compare_versions(current, available) < 0



def _compare_core(left: SemanticVersion, right: SemanticVersion) -> int:
    left_tuple = (left.major, left.minor, left.patch)
    right_tuple = (right.major, right.minor, right.patch)
    if left_tuple < right_tuple:
        return -1
    if left_tuple > right_tuple:
        return 1
    return 0



def _compare_prerelease(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1
    for left_id, right_id in zip(left, right):
        if left_id == right_id:
            continue
        left_num = left_id.isdigit()
        right_num = right_id.isdigit()
        if left_num and right_num:
            return -1 if int(left_id) < int(right_id) else 1
        if left_num != right_num:
            return -1 if left_num else 1
        return -1 if left_id < right_id else 1
    if len(left) < len(right):
        return -1
    if len(left) > len(right):
        return 1
    return 0

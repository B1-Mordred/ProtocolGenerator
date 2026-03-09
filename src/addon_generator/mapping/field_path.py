from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(slots=True)
class PathToken:
    key: str | None = None
    index: int | None = None


def parse_field_path(path: str) -> list[PathToken]:
    if not path or path.strip() != path:
        raise ValueError("Field path must be a non-empty trimmed string.")

    tokens: list[PathToken] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == '.':
            i += 1
            continue

        if ch == '[':
            end = path.find(']', i)
            if end == -1:
                raise ValueError(f"Invalid field path syntax: {path}")
            idx = path[i + 1 : end]
            if not idx.isdigit():
                raise ValueError(f"Invalid field path syntax: {path}")
            tokens.append(PathToken(index=int(idx)))
            i = end + 1
            continue

        start = i
        while i < len(path) and path[i] not in '.[':
            i += 1
        key = path[start:i]
        if not key:
            raise ValueError(f"Invalid field path syntax: {path}")
        tokens.append(PathToken(key=key))

    if not tokens:
        raise ValueError(f"Invalid field path syntax: {path}")
    return tokens


def get_field_value(payload: object, path: str, default: object = None) -> object:
    current = payload
    for token in parse_field_path(path):
        if token.key is not None:
            if not isinstance(current, Mapping) or token.key not in current:
                return default
            current = current[token.key]
            continue

        if not isinstance(current, Sequence) or isinstance(current, (str, bytes, bytearray)):
            return default
        assert token.index is not None
        if token.index < 0 or token.index >= len(current):
            return default
        current = current[token.index]

    return current

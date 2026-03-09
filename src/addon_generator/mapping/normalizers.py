from __future__ import annotations


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def trim(value: str) -> str:
    return value.strip()


def case_fold(value: str) -> str:
    return value.casefold()


def normalize_for_matching(value: str) -> str:
    return case_fold(collapse_whitespace(trim(value)))

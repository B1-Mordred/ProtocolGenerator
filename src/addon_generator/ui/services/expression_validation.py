from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpressionValidationResult:
    is_valid: bool
    error: str = ""


def validate_mapping_expression(expression: str) -> ExpressionValidationResult:
    expr = expression.strip()
    if not expr:
        return ExpressionValidationResult(False, "Expression is required")
    if not _has_balanced_parentheses(expr):
        return ExpressionValidationResult(False, "Unbalanced parentheses")

    if expr.startswith("concat("):
        return _validate_concat_expression(expr)

    if "," in expr:
        return ExpressionValidationResult(False, "Multiple tokens must be wrapped in concat(...)")

    return _validate_token(expr)


def _validate_concat_expression(expr: str) -> ExpressionValidationResult:
    if not expr.endswith(")"):
        return ExpressionValidationResult(False, "concat(...) must end with ')'")
    content = expr[len("concat(") : -1].strip()
    if not content:
        return ExpressionValidationResult(False, "concat(...) requires at least one token")

    parts = _split_arguments(content)
    if not parts:
        return ExpressionValidationResult(False, "concat(...) requires at least one token")

    token_start = 0
    if parts[0].startswith("delimiter"):
        delimiter_result = _validate_delimiter_argument(parts[0])
        if not delimiter_result.is_valid:
            return delimiter_result
        token_start = 1
    elif any(part.startswith("delimiter") for part in parts[1:]):
        return ExpressionValidationResult(False, "delimiter=... must be the first concat argument")

    if token_start >= len(parts):
        return ExpressionValidationResult(False, "concat(...) requires at least one token")

    for token in parts[token_start:]:
        token_result = _validate_token(token)
        if not token_result.is_valid:
            return token_result
    return ExpressionValidationResult(True)


def _validate_delimiter_argument(value: str) -> ExpressionValidationResult:
    key, _, raw_value = value.partition("=")
    if key.strip() != "delimiter" or not _:
        return ExpressionValidationResult(False, "Delimiter argument must use delimiter='<value>'")
    cleaned = raw_value.strip()
    if len(cleaned) < 2 or cleaned[0] not in ("'", '"') or cleaned[-1] != cleaned[0]:
        return ExpressionValidationResult(False, "Delimiter argument must use quoted text")
    return ExpressionValidationResult(True)


def _validate_token(token: str) -> ExpressionValidationResult:
    value = token.strip()
    if value.startswith("input:"):
        if value == "input:":
            return ExpressionValidationResult(False, "input: token requires a path")
        return ExpressionValidationResult(True)
    if value.startswith("default:"):
        return ExpressionValidationResult(True)
    if value.startswith("custom:"):
        return ExpressionValidationResult(True)
    return ExpressionValidationResult(False, "Unsupported token; use input:, default:, or custom:")


def _has_balanced_parentheses(value: str) -> bool:
    depth = 0
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _split_arguments(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    for char in value:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            continue
        if char == "(":
            depth += 1
            current.append(char)
            continue
        if char == ")":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts

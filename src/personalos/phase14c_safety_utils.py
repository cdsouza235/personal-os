"""Pure helper utilities for Phase 14-C no-leak reports."""

from __future__ import annotations

import re
import urllib.error
from collections.abc import Iterable, Mapping
from typing import Any


PHASE14C_REDACTION_MAX_DEPTH = 32
PHASE14C_REDACTION_MAX_NODES = 5000

PHASE14C_FORBIDDEN_RAW_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "app_password",
        "authorization",
        "configured_model_ids",
        "full_prompt",
        "oauth_token",
        "password",
        "prompt",
        "raw_provider_response",
        "response_text",
        "smtp_password",
        "token",
    }
)
PHASE14C_SECRET_VALUE_PATTERNS: tuple[str, ...] = (
    "api_key=",
    "app_password=",
    "bearer ",
    "oauth",
    "password=",
    "secret-",
    "sk-",
    "token=",
    "ya29.",
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_UNMASKED_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def config_names_only(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> tuple[str, ...]:
    """Return config entry names without reading or reporting values."""

    if isinstance(available_config_names, Mapping):
        names = available_config_names.keys()
    else:
        names = available_config_names
    return tuple(str(name) for name in names)


def optional_string(value: object) -> str | None:
    """Return a stripped non-empty string or None."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def optional_email(value: object) -> str | None:
    """Return a simple email-shaped string or None."""

    text = optional_string(value)
    if text is None or _EMAIL_RE.match(text) is None:
        return None
    return text


def safe_error_kind(error: BaseException) -> str:
    """Return an exception class name without host, address, or message text."""

    if isinstance(error, urllib.error.URLError):
        reason = getattr(error, "reason", None)
        if isinstance(reason, BaseException):
            return reason.__class__.__name__
    return error.__class__.__name__


def redaction_failure_reasons(
    value: object,
    *,
    max_depth: int = PHASE14C_REDACTION_MAX_DEPTH,
    max_nodes: int = PHASE14C_REDACTION_MAX_NODES,
) -> list[str]:
    """Return leak reason codes without returning the offending values."""

    reasons: list[str] = []
    nodes_visited = 0
    limit_hit = False

    def visit(item: object, *, depth: int) -> None:
        nonlocal nodes_visited, limit_hit
        if limit_hit:
            return
        nodes_visited += 1
        if nodes_visited > max_nodes:
            reasons.append("redaction_scan_node_limit_exceeded")
            limit_hit = True
            return
        if depth > max_depth:
            reasons.append("redaction_scan_depth_limit_exceeded")
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                if (
                    isinstance(key, str)
                    and key.lower() in PHASE14C_FORBIDDEN_RAW_KEYS
                ):
                    reasons.append("forbidden_raw_field_present")
                visit(child, depth=depth + 1)
            return
        if isinstance(item, list | tuple):
            for child in item:
                visit(child, depth=depth + 1)
            return
        if isinstance(item, str):
            lowered = item.lower()
            if _UNMASKED_EMAIL_RE.search(item):
                reasons.append("unmasked_email_value_present")
            if any(pattern in lowered for pattern in PHASE14C_SECRET_VALUE_PATTERNS):
                reasons.append("secret_like_value_present")

    visit(value, depth=0)
    return unique_reason_codes(reasons)


def unique_reason_codes(values: Iterable[str]) -> list[str]:
    """Return reason codes in first-seen order."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

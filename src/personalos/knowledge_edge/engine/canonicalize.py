"""Canonicalization (amendment §11.2): normalize URLs, identifiers, aliases, and
timestamps into stable, comparable forms.

Pure functions only: no I/O, no clock reads (mirrors ``docs/ARCHITECTURE.md``
invariant #2, applied to Knowledge Edge by AD-1). Every timestamp function takes the
relevant timezone/instant as an explicit argument; nothing here calls
``datetime.now()``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

TRACKING_QUERY_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "si",
        "feature",
        "fbclid",
        "gclid",
        "ref",
        "ref_src",
    }
)


def normalize_url(url: str) -> str:
    """Strip tracking query parameters and normalize scheme/host case and trailing slash.

    Deterministic and idempotent: normalizing an already-normalized URL is a no-op.
    """
    if not url:
        return url
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    kept_query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS
    )
    query = urlencode(kept_query)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_identifier(value: str) -> str:
    """Strip surrounding/internal whitespace; case is preserved (IDs are often
    case-sensitive, e.g. YouTube video IDs)."""
    return " ".join(value.strip().split())


def resolve_alias(name: str, alias_map: Mapping[str, str]) -> str | None:
    """Resolve ``name`` to a canonical ID via a case-insensitive alias lookup.

    ``alias_map`` maps a literal alternate spelling/name to its canonical ID.
    Returns ``None`` when no alias matches (caller decides whether that is an
    error or an acceptable miss).
    """
    normalized_name = " ".join(name.strip().lower().split())
    for alias, canonical_id in alias_map.items():
        if " ".join(alias.strip().lower().split()) == normalized_name:
            return canonical_id
    return None


def normalize_timestamp_to_utc(value: str, *, source_timezone: str) -> str:
    """Parse an ISO-8601 timestamp and return its UTC equivalent as ISO-8601.

    If ``value`` has no UTC offset, ``source_timezone`` (an IANA zone name) is
    applied before conversion. Never reads the wall clock; ``value`` is the only
    time input.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
    return parsed.astimezone(ZoneInfo("UTC")).isoformat()


def to_display_timezone(value_utc: str, *, display_timezone: str = "America/Chicago") -> str:
    """Convert a UTC ISO-8601 timestamp to the given display timezone's ISO-8601 form."""
    parsed = datetime.fromisoformat(value_utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(ZoneInfo(display_timezone)).isoformat()


def build_dedupe_key(*, source_id: str, stable_id: str) -> str:
    """Build the deterministic ``media_item.dedupe_key`` for one adapter-reported item.

    Two calls with the same ``source_id``/``stable_id`` always produce the same key,
    which is what lets the scan orchestrator recognize a re-processed occurrence as
    the same occurrence rather than a duplicate (amendment §11.1 idempotency).
    """
    normalized_source = normalize_identifier(source_id)
    normalized_stable = normalize_identifier(stable_id)
    return f"{normalized_source}:{normalized_stable}"


def normalize_duration_seconds(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("duration_seconds must be >= 0")
    return int(value)


def normalize_fiscal_period(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None

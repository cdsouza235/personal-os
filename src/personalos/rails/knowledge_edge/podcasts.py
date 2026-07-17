"""Live podcast RSS/Atom rail adapter (P-KE-2A) -- inert until a later, G5-gated
packet admits `shadow_live` for Lane A (amendment Sec14.4; Session 2).

This module is the ONE place in the codebase allowed to make a genuine HTTPS GET
against a Lane A (curated podcast) feed. `LivePodcastFeedAdapter` implements the same
`PodcastFeedAdapter` Protocol (`personalos.knowledge_edge.adapters.contracts`) the
Packet 1B fixture (`FixturePodcastFeedAdapter`) satisfies, so `scan_orchestrator.py`
never has to change when this adapter replaces the fixture -- it depends on the
Protocol, not on either concrete class.

Per PHASE0_ARCHITECTURE_DECISIONS AD-3, a read-only discovery adapter does not get the
full four-gate write pattern (that pattern gates *writes to Chris's real accounts*;
there is no external account mutation here to gate). What AD-3 says IS real for this
adapter, enforced in `LivePodcastFeedAdapter._evaluate_gates`, in this fixed order:

    feature_mode admission -> credentials-present -> source/endpoint verification

Any gate left unsatisfied is a hard stop: `fetch_episodes` returns
`AdapterFetchResult(healthy=False, error_summary=<honest reason>)` -- the exact shape
the contract already defines for "do not advance this source's cursor, record this as
a failed/degraded source" -- never a silent no-op, never an unhandled exception, and
the live HTTP client is never constructed until every gate passes.

`LANE_A_FEATURE_MODES` adds `shadow_live` (and the two Session-3 rungs) to Lane A's own
config vocabulary, per amendment Sec14.4 -- but this is vocabulary only. Nothing in this
repo constructs `LivePodcastFeedAdapter(feature_mode="shadow_live")` outside this
module's own tests: no caller passes anything but the `disabled` default, and the
Session 2 shadow-scheduler gate is what will eventually let a real caller do so.
Structurally reachable, not actually reached -- exactly the "G5-flagged reachability"
posture this packet is built to.

Independently of feature_mode, migration 00023 seeds all 9 launch-roster feed
endpoints with `ke_sources.status='trial'` and `ke_source_endpoints.endpoint_verified_at
IS NULL` (nothing has been Conductor-verified yet -- see
docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md). The source/endpoint
verification gate below refuses every one of them today regardless of feature_mode, so
even a future caller that legitimately reaches `shadow_live` still cannot fetch from any
of these 9 feeds until that supervised smoke records a per-feed verification.

Network stack is stdlib-only (`urllib.request`/`urllib.error`, `xml.etree.ElementTree`)
-- no third-party HTTP or feed-parsing library, matching `rails/todoist.py`'s existing
convention and this repo's zero-dependency posture. `urllib.parse` is not imported here
(that carve-out is scoped to `engine/canonicalize.py` only); host extraction for the
redirect-confinement check below uses the same plain-string technique
`personalos.knowledge_edge.dashboard._url_host` already uses.
"""

from __future__ import annotations

import os
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from xml.etree import ElementTree

import personalos.knowledge_edge.state as ke
from personalos.knowledge_edge.adapters.contracts import AdapterFetchResult, DiscoveredMediaItem

# Phase 2 rail credential: a descriptive identifying User-Agent string for public RSS/
# Atom GETs (there is no API key for public podcast feeds -- this is the one
# credential-shaped thing a polite, identifiable fetch actually needs, the same
# rationale SEC's own fair-access User-Agent requirement already established for the
# EDGAR rail). Read via os.environ only; never hardcoded/logged.
PODCAST_RAIL_CREDENTIAL_ENV_VAR = "PERSONALOS_RAIL_KE_PODCAST_USER_AGENT"

# Amendment Sec14.4's own feature-mode ladder, scoped to Lane A by this packet.
# `shadow_live` is added here as config vocabulary only -- see module docstring.
LANE_A_FEATURE_MODES = (
    "disabled",
    "fixture",
    "shadow_live",
    "active_read_only",
    "active_with_obsidian_handoff",
)
DEFAULT_LANE_A_FEATURE_MODE = "disabled"
# Only these rungs admit a live fetch attempt at all; `disabled`/`fixture` never do,
# structurally, regardless of any other gate.
_LANE_A_LIVE_ADMITTING_MODES = frozenset(
    {"shadow_live", "active_read_only", "active_with_obsidian_handoff"}
)

REQUEST_TIMEOUT_SECONDS = 10.0
# 64 MB ceiling. The 2026-07-17 live shadow run (scan_run_id
# shadow-scan-2026-07-17-92d26c4b...) showed the prior 2 MB cap refusing 6 of 9
# verified feeds with STATUS_FETCH_RESPONSE_TOO_LARGE; smoke evidence (see
# audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md session #2)
# is that real verified feeds parse fine up to ~20 MB (Bankless=1342 items, Odd
# Lots=1242, Unchained=1210). 64 MB is ~3x that measured high-water mark: enough
# headroom for legitimate feeds while still bounding a hostile/runaway response.
MAX_RESPONSE_BYTES = 64_000_000
MAX_ITEMS_PER_FETCH = 200
_EXCERPT_MAX_CHARS = 500

STATUS_BLOCKED_FEATURE_MODE = "podcast_rail_live_fetch_blocked_feature_mode_not_live"
STATUS_BLOCKED_CREDENTIAL_MISSING = "podcast_rail_live_fetch_blocked_credential_env_var_missing"
STATUS_BLOCKED_CREDENTIAL_EMPTY = "podcast_rail_live_fetch_blocked_credential_env_var_empty"
STATUS_BLOCKED_SOURCE_NOT_FOUND = "podcast_rail_live_fetch_blocked_source_not_found"
STATUS_BLOCKED_NO_ENDPOINT = "podcast_rail_live_fetch_blocked_no_active_endpoint"
STATUS_BLOCKED_SOURCE_NOT_VERIFIED = "podcast_rail_live_fetch_blocked_source_not_verified"
STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME = "podcast_rail_live_fetch_blocked_endpoint_insecure_scheme"
STATUS_FETCH_TRANSPORT_FAILED = "podcast_rail_live_fetch_transport_failed"
STATUS_FETCH_REDIRECT_QUARANTINED = "podcast_rail_live_fetch_redirect_quarantined"
STATUS_FETCH_RESPONSE_TOO_LARGE = "podcast_rail_live_fetch_response_too_large"
STATUS_FETCH_MALFORMED_FEED = "podcast_rail_live_fetch_malformed_feed"

# Dropped-item reasons (F1): a per-item field that fails a structural requirement is
# counted by one of these keys rather than being silently filtered. Keys are
# machine-readable and stable -- callers key coverage/health reporting off them.
DROP_REASON_MISSING_GUID = "missing_guid"
DROP_REASON_MISSING_TITLE = "missing_title"
DROP_REASON_MISSING_OR_UNPARSEABLE_PUBDATE = "missing_or_unparseable_pubdate"
DROP_REASON_MISSING_CANONICAL_URL = "missing_canonical_url"
DROP_REASON_DUPLICATE_GUID_IN_BATCH = "duplicate_guid_in_batch"


def _merge_counts(*counters: Mapping[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counter in counters:
        for reason, count in counter.items():
            merged[reason] = merged.get(reason, 0) + count
    return merged


def validate_lane_a_feature_mode(value: str) -> str:
    if value not in LANE_A_FEATURE_MODES:
        allowed = ", ".join(LANE_A_FEATURE_MODES)
        raise ValueError(f"Lane A feature mode must be one of: {allowed}")
    return value


class PodcastFeedFetchError(Exception):
    """Base class for adapter-raised (non-transport) fetch failures."""


class PodcastFeedRedirectQuarantined(PodcastFeedFetchError):
    """A feed's HTTP redirect pointed at a different host than the request's own -- refused."""


class PodcastFeedResponseTooLarge(PodcastFeedFetchError):
    """The feed response exceeded MAX_RESPONSE_BYTES -- refused before fully buffering it."""


class MalformedFeedError(Exception):
    """The fetched document could not be parsed as a well-formed RSS/Atom feed."""


def _extract_host(url: str) -> str:
    """Lowercased host, extracted with plain string ops -- no `urllib.parse` import
    (that carve-out is scoped to `engine/canonicalize.py` only); mirrors
    `personalos.knowledge_edge.dashboard._url_host`'s identical technique."""
    remainder = url.split("://", 1)[-1]
    host = remainder.split("/", 1)[0]
    return host.rsplit("@", 1)[-1].split(":", 1)[0].lower()


class _HostConfinedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only when it stays on the request's own host; any redirect
    to a different host is quarantined (raised, never silently followed) -- amendment
    Sec16.2's network-controls intent, applied to the one live fetch this rail makes."""

    def __init__(self, allowed_host: str) -> None:
        super().__init__()
        self._allowed_host = allowed_host

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        # HTTPS->HTTP downgrade is refused unconditionally, same-host or not: a
        # same-host match on `_extract_host` says nothing about scheme, and this rail
        # never constructs an insecure request regardless of what host it lands on.
        if not newurl.startswith("https://"):
            raise PodcastFeedRedirectQuarantined(
                f"refusing redirect from {req.full_url!r} to a non-https:// target "
                f"({newurl!r}): HTTPS->HTTP downgrade is never followed"
            )
        redirect_host = _extract_host(newurl)
        if redirect_host != self._allowed_host:
            raise PodcastFeedRedirectQuarantined(
                f"refusing redirect from host {self._allowed_host!r} to a different "
                f"host {redirect_host!r} ({newurl!r})"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PodcastFeedHttpClientProtocol(Protocol):
    def fetch(self, url: str, *, user_agent: str) -> bytes: ...


class PodcastFeedHttpClient:
    """Thin stdlib-only HTTPS client for fetching one podcast RSS/Atom document.

    Mirrors `rails/todoist.py`'s `TodoistRailClient`: `urllib.request`/`urllib.error`
    only, injectable `opener` so tests can exercise the real request-construction path
    without ever touching the network. Bounded: fixed timeout, a hard response-size
    cap enforced before the body is handed back, and same-host-only redirects.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        opener: Any | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._opener = opener

    def fetch(self, url: str, *, user_agent: str) -> bytes:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": user_agent})
        opener = self._opener
        if opener is None:
            redirect_handler = _HostConfinedRedirectHandler(_extract_host(url))
            opener = urllib.request.build_opener(redirect_handler).open
        with opener(request, timeout=self._timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_bytes = int(content_length)
                except ValueError:
                    declared_bytes = None
                # A declared Content-Length over the cap is refused before the body is
                # ever read -- cheap preflight, same refusal as the bounded-read check
                # below for feeds that omit or lie about Content-Length.
                if declared_bytes is not None and declared_bytes > self._max_response_bytes:
                    raise PodcastFeedResponseTooLarge(
                        f"feed response at {url!r} declared Content-Length "
                        f"{declared_bytes} bytes, exceeding the {self._max_response_bytes}-byte "
                        "cap; refusing before reading the body"
                    )
            raw = response.read(self._max_response_bytes + 1)
        if len(raw) > self._max_response_bytes:
            raise PodcastFeedResponseTooLarge(
                f"feed response at {url!r} exceeded the {self._max_response_bytes}-byte cap"
            )
        return raw


@dataclass(frozen=True)
class _ParsedEpisode:
    guid: str
    title: str
    canonical_url: str
    description_excerpt: str
    published_at: str
    duration_seconds: int | None
    media_type: str
    underlying_id: str
    alternate_urls: tuple[str, ...]
    raw_payload_summary: Mapping[str, Any] = field(default_factory=dict)


class LivePodcastFeedAdapter:
    """Live implementation of `PodcastFeedAdapter`
    (`personalos.knowledge_edge.adapters.contracts`). Same shape as
    `FixturePodcastFeedAdapter` from the caller's point of view: construct once per
    scan, call `fetch_episodes(source_id=..., cursor=..., now=...)` per source.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        feature_mode: str = DEFAULT_LANE_A_FEATURE_MODE,
        credential_env_var: str = PODCAST_RAIL_CREDENTIAL_ENV_VAR,
        client: PodcastFeedHttpClientProtocol | None = None,
        max_items_per_fetch: int = MAX_ITEMS_PER_FETCH,
    ) -> None:
        self._connection = connection
        self._feature_mode = validate_lane_a_feature_mode(feature_mode)
        self._credential_env_var = credential_env_var
        self._client = client if client is not None else PodcastFeedHttpClient()
        self._max_items_per_fetch = max_items_per_fetch

    def fetch_episodes(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now  # every field this adapter reports comes from the feed's own declared
        # pubDate/guid, never the wall clock (contracts.py: "time is an input").

        error, endpoint_url, user_agent = self._evaluate_gates(source_id=source_id)
        if error is not None:
            return _unhealthy(source_id, cursor, error)

        try:
            raw = self._client.fetch(endpoint_url, user_agent=user_agent)
        except PodcastFeedRedirectQuarantined as fetch_error:
            reason = f"{STATUS_FETCH_REDIRECT_QUARANTINED}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)
        except PodcastFeedResponseTooLarge as fetch_error:
            reason = f"{STATUS_FETCH_RESPONSE_TOO_LARGE}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)
        except (OSError, urllib.error.URLError) as fetch_error:
            reason = f"{STATUS_FETCH_TRANSPORT_FAILED}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)

        try:
            episodes, parse_dropped = _parse_feed_document(raw)
        except MalformedFeedError as parse_error:
            return _unhealthy(source_id, cursor, f"{STATUS_FETCH_MALFORMED_FEED}: {parse_error}")

        discovered, batch_dropped = _build_discovered_items(source_id=source_id, episodes=episodes)
        due = tuple(item for item in discovered if cursor is None or item.cursor_value > cursor)
        due_sorted = tuple(sorted(due, key=lambda item: item.cursor_value))
        due_sorted = due_sorted[: self._max_items_per_fetch]
        next_cursor = due_sorted[-1].cursor_value if due_sorted else cursor
        return AdapterFetchResult(
            source_id=source_id,
            items=due_sorted,
            next_cursor_value=next_cursor,
            healthy=True,
            dropped_items=_merge_counts(parse_dropped, batch_dropped),
        )

    def _evaluate_gates(
        self, *, source_id: str
    ) -> tuple[str | None, str | None, str | None]:
        """Returns `(error, endpoint_url, user_agent)`. `error` is `None` only once
        every gate has passed, in the fixed order feature_mode -> credentials ->
        source/endpoint verification (AD-3 plus this packet's own read-adapter
        requirement)."""
        if self._feature_mode not in _LANE_A_LIVE_ADMITTING_MODES:
            return (
                f"{STATUS_BLOCKED_FEATURE_MODE}: feature_mode {self._feature_mode!r} does not "
                "admit a live Lane A fetch ('disabled'/'fixture' never fetch live)",
                None,
                None,
            )

        if self._credential_env_var not in os.environ:
            return (
                f"{STATUS_BLOCKED_CREDENTIAL_MISSING}: credential env var is not set: "
                f"{self._credential_env_var}",
                None,
                None,
            )
        user_agent = os.environ[self._credential_env_var]
        if not user_agent.strip():
            return (
                f"{STATUS_BLOCKED_CREDENTIAL_EMPTY}: credential env var is set but empty: "
                f"{self._credential_env_var}",
                None,
                None,
            )

        source = ke.get_source(self._connection, source_id)
        if source is None:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_FOUND}: no ke_sources row for {source_id!r}",
                None,
                None,
            )

        endpoint = _resolve_primary_endpoint(self._connection, source_id=source_id)
        if endpoint is None:
            return (
                f"{STATUS_BLOCKED_NO_ENDPOINT}: no active rss/atom endpoint on file for "
                f"{source_id!r}",
                None,
                None,
            )

        # "Verified" requires BOTH a recorded verifier identity AND a parseable
        # verification timestamp -- Codex iteration-3 audit condition 2. A timestamp
        # with no verifier, or a verifier with a malformed/unparseable timestamp, is
        # not a completed supervised-smoke record and must refuse exactly like the
        # both-NULL case does.
        verified_at = endpoint["endpoint_verified_at"]
        verified_by = endpoint["verified_by"]
        verified_by_present = verified_by is not None and str(verified_by).strip() != ""
        if source["status"] != "active" or verified_at is None or not verified_by_present:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_VERIFIED}: source status is {source['status']!r} "
                f"(endpoint_verified_at={verified_at!r}, verified_by={verified_by!r}); refusing "
                "until the Conductor-supervised smoke records a verification (see "
                "docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md)",
                None,
                None,
            )
        if _parse_iso8601_to_iso_utc(str(verified_at)) is None:
            return (
                f"{STATUS_BLOCKED_SOURCE_NOT_VERIFIED}: endpoint_verified_at={verified_at!r} is "
                "not a parseable timestamp; refusing rather than trusting a malformed "
                "verification record (see docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md)",
                None,
                None,
            )

        # Enforced independently of verification state: even a fully-verified endpoint
        # never gets a live request constructed against a non-https URL.
        endpoint_url = endpoint["url"]
        if not endpoint_url.startswith("https://"):
            return (
                f"{STATUS_BLOCKED_ENDPOINT_INSECURE_SCHEME}: endpoint url {endpoint_url!r} is "
                "not https://; refusing to construct a live request over an insecure scheme",
                None,
                None,
            )

        return (None, endpoint_url, user_agent)


def _unhealthy(source_id: str, cursor: str | None, error_summary: str) -> AdapterFetchResult:
    return AdapterFetchResult(
        source_id=source_id,
        items=(),
        next_cursor_value=cursor,
        healthy=False,
        error_summary=error_summary,
    )


def _resolve_primary_endpoint(
    connection: sqlite3.Connection, *, source_id: str
) -> dict[str, Any] | None:
    endpoints = [
        endpoint
        for endpoint in ke.list_source_endpoints(connection, source_id=source_id)
        if endpoint["endpoint_type"] in ("rss", "atom") and endpoint["status"] == "active"
    ]
    if not endpoints:
        return None
    primary = [endpoint for endpoint in endpoints if endpoint["is_primary"]]
    return primary[0] if primary else endpoints[0]


def _build_discovered_items(
    *, source_id: str, episodes: Sequence[_ParsedEpisode]
) -> tuple[tuple[DiscoveredMediaItem, ...], dict[str, int]]:
    seen_guids: set[str] = set()
    items: list[DiscoveredMediaItem] = []
    dropped: dict[str, int] = {}
    for episode in episodes:
        # Defensive de-duplication within a single fetch batch: two items sharing a
        # guid would build the same dedupe_key/media_item_id downstream and the
        # second `create_media_item` call would collide on the primary key. A
        # well-formed feed never does this; keep the first-seen occurrence only,
        # but count the rest instead of dropping them silently (F2).
        if episode.guid in seen_guids:
            dropped[DROP_REASON_DUPLICATE_GUID_IN_BATCH] = (
                dropped.get(DROP_REASON_DUPLICATE_GUID_IN_BATCH, 0) + 1
            )
            continue
        seen_guids.add(episode.guid)
        items.append(
            DiscoveredMediaItem(
                source_id=source_id,
                source_specific_id=episode.guid,
                canonical_url=episode.canonical_url,
                title=episode.title,
                media_type=episode.media_type,
                source_precedence="official",
                format_hint="original_podcast_guest",
                alternate_urls=episode.alternate_urls,
                description_excerpt=episode.description_excerpt,
                published_at=episode.published_at,
                duration_seconds=episode.duration_seconds,
                feed_guid=episode.guid,
                underlying_id=episode.underlying_id,
                cursor_value=f"{episode.published_at}|{episode.guid}",
                raw_payload_summary=episode.raw_payload_summary,
            )
        )
    return tuple(items), dropped


# --------------------------------------------------------------------- feed parsing


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_local(elem: ElementTree.Element, name: str) -> ElementTree.Element | None:
    for child in elem:
        if _local_name(child.tag) == name:
            return child
    return None


def _findall_local(elem: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in elem if _local_name(child.tag) == name]


def _text(elem: ElementTree.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


_DOCTYPE_MARKER = b"<!DOCTYPE"


def _parse_feed_document(raw: bytes) -> tuple[list[_ParsedEpisode], dict[str, int]]:
    # Cheap XXE/entity-expansion guard: a legitimate public podcast RSS/Atom document
    # never declares a DOCTYPE. Checked before handing anything to ElementTree.
    if _DOCTYPE_MARKER in raw:
        raise MalformedFeedError(
            "feed document declares a DOCTYPE; refusing to parse untrusted external entities"
        )
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as parse_error:
        raise MalformedFeedError(
            f"feed document is not well-formed XML: {parse_error}"
        ) from parse_error

    root_name = _local_name(root.tag)
    if root_name == "rss":
        channel = _find_local(root, "channel")
        if channel is None:
            raise MalformedFeedError("rss root element has no <channel>")
        parsed = [_parse_rss_item(item) for item in _findall_local(channel, "item")]
    elif root_name == "feed":
        parsed = [_parse_atom_entry(entry) for entry in _findall_local(root, "entry")]
    else:
        raise MalformedFeedError(
            f"unsupported feed root element <{root_name}>; expected an RSS <rss> or Atom <feed>"
        )

    # Every dropped item is counted by its reason (F1) rather than being filtered
    # out indistinguishably from "the feed simply had nothing here."
    episodes: list[_ParsedEpisode] = []
    dropped: dict[str, int] = {}
    for episode, reason in parsed:
        if episode is not None:
            episodes.append(episode)
        else:
            dropped[reason] = dropped.get(reason, 0) + 1
    return episodes, dropped


def _parse_rfc822_to_iso_utc(text: str) -> str | None:
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _parse_iso8601_to_iso_utc(text: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _parse_itunes_duration(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if not (1 <= len(parts) <= 3) or not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _parse_rss_item(
    item: ElementTree.Element,
) -> tuple[_ParsedEpisode | None, str | None]:
    guid = _text(_find_local(item, "guid"))
    if not guid:
        return None, DROP_REASON_MISSING_GUID
    title = _text(_find_local(item, "title"))
    if not title:
        return None, DROP_REASON_MISSING_TITLE

    pub_date_raw = _text(_find_local(item, "pubDate"))
    published_at = _parse_rfc822_to_iso_utc(pub_date_raw) if pub_date_raw else None
    if published_at is None:
        # Cannot be cursored reliably without a parseable publish time; skip this
        # item rather than fail the whole feed (a single malformed item is not the
        # same failure as a malformed document).
        return None, DROP_REASON_MISSING_OR_UNPARSEABLE_PUBDATE

    link = _text(_find_local(item, "link"))
    enclosure = _find_local(item, "enclosure")
    enclosure_url = enclosure.get("url") if enclosure is not None else None
    enclosure_type = (enclosure.get("type") or "") if enclosure is not None else ""

    canonical_url = link or enclosure_url
    if not canonical_url:
        return None, DROP_REASON_MISSING_CANONICAL_URL

    alternate_urls = tuple(url for url in (enclosure_url,) if url and url != canonical_url)
    media_type = "video_interview" if enclosure_type.startswith("video/") else "podcast_episode"

    duration_raw = _text(_find_local(item, "duration"))
    duration_seconds = _parse_itunes_duration(duration_raw) if duration_raw else None

    episode_number = _text(_find_local(item, "episode"))
    underlying_id = episode_number if episode_number else guid

    description = _text(_find_local(item, "description"))[:_EXCERPT_MAX_CHARS]

    return (
        _ParsedEpisode(
            guid=guid,
            title=title,
            canonical_url=canonical_url,
            description_excerpt=description,
            published_at=published_at,
            duration_seconds=duration_seconds,
            media_type=media_type,
            underlying_id=underlying_id,
            alternate_urls=alternate_urls,
            raw_payload_summary={
                "guid": guid,
                "pub_date": pub_date_raw,
                "duration_raw": duration_raw,
                "enclosure_type": enclosure_type,
            },
        ),
        None,
    )


def _parse_atom_entry(
    entry: ElementTree.Element,
) -> tuple[_ParsedEpisode | None, str | None]:
    guid = _text(_find_local(entry, "id"))
    if not guid:
        return None, DROP_REASON_MISSING_GUID
    title = _text(_find_local(entry, "title"))
    if not title:
        return None, DROP_REASON_MISSING_TITLE

    link_elem = _find_local(entry, "link")
    canonical_url = link_elem.get("href") if link_elem is not None else None
    if not canonical_url:
        return None, DROP_REASON_MISSING_CANONICAL_URL

    timestamp_raw = _text(_find_local(entry, "published")) or _text(_find_local(entry, "updated"))
    published_at = _parse_iso8601_to_iso_utc(timestamp_raw) if timestamp_raw else None
    if published_at is None:
        return None, DROP_REASON_MISSING_OR_UNPARSEABLE_PUBDATE

    description = (_text(_find_local(entry, "summary")) or _text(_find_local(entry, "content")))[
        :_EXCERPT_MAX_CHARS
    ]

    return (
        _ParsedEpisode(
            guid=guid,
            title=title,
            canonical_url=canonical_url,
            description_excerpt=description,
            published_at=published_at,
            duration_seconds=None,
            media_type="podcast_episode",
            underlying_id=guid,
            alternate_urls=(),
            raw_payload_summary={"guid": guid, "timestamp_raw": timestamp_raw},
        ),
        None,
    )

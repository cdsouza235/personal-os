"""Live YouTube Lane B/C rail adapter (P-KE-2B) -- inert until a later, G5-gated
packet admits `shadow_live` (amendment Sec14.4; Session 2), exactly the same posture
`rails/knowledge_edge/podcasts.py` (P-KE-2A) shipped under. Read that module first --
its gating order, host-confined redirect handling, coverage-honesty dropped-item
counting, and refusal-taxonomy conventions are the house pattern this module extends,
not reinvents.

Per the D-YT decision (amendment §10.4, ratified Session 1 -- see
`docs/knowledge_edge/PHASE0_PROVIDERS_AND_ACCESS.md` §4), Lane B/C discovery uses TWO
independent mechanisms, both implemented in this one file (matching
`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1's module layout):

1. **`LiveYoutubeChannelAdapter`** -- official channel-upload RSS polling
   (`youtube.com/feeds/videos.xml?channel_id=...`), the Protocol
   `personalos.knowledge_edge.adapters.contracts.ChannelVideoAdapter` expects
   (`fetch_uploads`). This is outside the YouTube Data API Services terms entirely --
   no key, no quota. Gating mirrors `podcasts.py` minus the credential step (there is
   no credential for a mechanism that needs no key):
       feature_mode admission -> source/endpoint verification
2. **`LiveYoutubePersonSearchClient`** -- the Data API `search.list` endpoint,
   narrowed to person-search only per D-YT option 1. Gating mirrors `podcasts.py`
   exactly:
       feature_mode admission -> credentials-present -> source/endpoint verification
   Both mechanisms are read-only discovery, so per
   `PHASE0_ARCHITECTURE_DECISIONS.md` AD-3 neither needs the full four-gate write
   pattern (that pattern gates *writes to Chris's real accounts*; there is nothing to
   write here).

`LANE_BC_FEATURE_MODES` adds `shadow_live` (and the two Session-3 rungs) as config
vocabulary only, exactly like `podcasts.py`'s `LANE_A_FEATURE_MODES` -- nothing in
this repo constructs either class with anything but the `disabled` default outside
this module's own tests, and neither class is wired into `scan_orchestrator.py` or
`cli/knowledge_edge.py` by this packet (that wiring, like `LivePodcastFeedAdapter`'s,
is a later packet's job -- see those two files, which still only construct the
Packet 1B fixtures). Structurally reachable, not actually reached.

**No channel-ID seeding in this packet.** Per this packet's own scope note, the
youtube_channel source registry ships EMPTY -- this module's channel-upload mechanism
is fully fixture/unit-tested against synthetic feeds, but no real channel_id endpoint
row exists yet for `_evaluate_gates` to ever pass against. Real channels arrive via a
later Conductor-verified migration + acknowledgment + supervised smoke, exactly like
the 9 Lane A podcast feeds did (migration 00023,
`docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md`) -- this packet's own
mirror of that doc is
`docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md`. The same is true of the
person-search mechanism's own `ke_sources` row (`DEFAULT_PERSON_SEARCH_SOURCE_ID`
below): nothing in this packet inserts it (inserting reference rows previously meant
a migration -- see migrations 00022/00023 -- and this packet's hard constraints
forbid migrations), so `LiveYoutubePersonSearchClient._evaluate_gates` refuses with
`STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND` today regardless of feature_mode or
credential presence, until a future packet seeds that row and runs its own
supervised smoke.

**A known, deliberately surfaced schema gap -- provider-metadata TTL cache.**
Amendment §10.4/§13.4 requires Data-API-sourced display metadata (titles,
descriptions, channel names, for the person-search use only) to live in "a
TTL-controlled refreshable cache with expiry, refresh, and deletion tests," and this
packet's own brief describes that structure as something "1A's schema provides."
That is not what this repo's migrations actually contain: `migrations/00017`-`00024`
were re-read in full while building this packet, and none of them define any
provider-metadata cache table -- `PHASE0_TRACEABILITY.md` §10.4/§13.4 rows
independently confirm the cache/TTL implementation itself was always planned as
Packet 2B/3A *implementation* work, not something 1A had already shipped. Since this
packet's own hard constraints forbid migrations, and inventing an undocumented
persistence mechanism for it would be worse than no persistence at all, the TTL
cache is implemented here as a pure-Python, injectable `PersonSearchCacheStore`
Protocol (`expiry`/`refresh`/`deletion` semantics, all covered by this module's
tests) with an in-memory reference implementation (`InMemoryPersonSearchCache`).
**No SQLite-backed implementation ships in this packet.** A durable store needs its
own migration and is a named defect-back item for whichever future packet actually
wires `LiveYoutubePersonSearchClient` into a real scan -- mirroring exactly how the
P-KE-2A podcast smoke transcript's "flips deferred" defect got closed by naming the
next packet's scope rather than working around the missing state-layer helpers in
place (`audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md`).
Since the channel/person-search source registries both ship empty this packet, this
gap has no live consequence yet -- it is flagged here so it is not silently
rediscovered later.

**A known, deliberately surfaced classification gap -- channel-upload `format_hint`.**
`scan_orchestrator.py` calls `engine.directness.classify_directness(format_hint=
item.format_hint, ...)` synchronously, at persistence time, for every discovered
item -- this is existing Phase 1B architecture this packet does not (and per its own
scope, may not) change. `podcasts.py` could safely hardcode
`format_hint="original_podcast_guest"` for every episode because Lane A's roster is,
by curation, exclusively long-form interview shows. A Lane B/C official channel has
no equivalent uniform content shape: a government channel's uploads are plausibly
`government_testimony`, a company's own channel plausibly
`keynote_or_product_presentation`, a network channel's clips plausibly
`financial_media_segment` -- and `engine/directness.py`'s own docstring is explicit
that format_hint may never be inferred from free text. A bare RSS feed's metadata
(title/link/description) cannot honestly resolve that per-channel judgment call, and
this packet's own scope excludes both engine/orchestrator changes and real channel
seeding. `LiveYoutubeChannelAdapter` therefore accepts an explicit, constructor-level
`default_format_hint` (validated only as a non-empty string here -- this module does
not import `engine/directness.py`, matching `podcasts.py`'s equally
engine-independent shape) rather than silently baking one in module-wide, and
`DEFAULT_CHANNEL_UPLOAD_FORMAT_HINT` defaults to `"mentioned_only_appearance"` -- the
one format_hint that under-classifies (excluded from P0/P2 promotion, `mentioned_only`
directness) rather than over-claims a direct appearance the feed never verified.
This is flagged as a real, unresolved product question for whichever future packet
seeds the first real Lane B/C channel, not a settled design.

**Response-size cap.** The P-KE-2A supervised-smoke transcript
(`audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md`) found real
podcast archive feeds exceeding 5 MB -- an unbounded-growth feed shape (an
interview show's entire back catalog, one `<item>` per episode ever published).
YouTube's own channel-upload feed does not share that growth vector: it is
documented, consistent platform behavior that `feeds/videos.xml` returns only the
channel's most recent ~15 uploads, not a full history -- entry count does not grow
over time the way a podcast archive's does. `MAX_CHANNEL_FEED_RESPONSE_BYTES` is set
well below Lane A's cap specifically because this structural bound makes a much
smaller cap both safe (real feeds are consistently well under it) and more honest
(an anomalously large response is far more likely to signal something wrong --
e.g. a redirect landing on an unexpected non-feed page -- than a legitimate feed
outgrowing it). Oversized responses are refused (`YoutubeRailResponseTooLarge`,
raised before the body is parsed) exactly like `podcasts.py`'s equivalent case:
a counted, honest `healthy=False` refusal, never a parse failure.

Network stack is stdlib-only (`urllib.request`/`urllib.error`, `xml.etree.ElementTree`,
`json`), matching `podcasts.py` and this repo's zero-dependency posture.
`urllib.parse` is not imported here (that carve-out is scoped to
`engine/canonicalize.py` only) -- `search.list`'s query string is built by this
module's own minimal percent-encoder (`_percent_encode_query_value`). The API key --
read from `PERSONALOS_RAIL_KE_YOUTUBE_API_KEY` at call time only -- is used solely to
construct the outgoing request URL passed straight to `YoutubeSearchHttpClient.fetch`;
no code path in this module ever formats that constructed URL (or the raw key) into
an `error_summary`, a log line, or any other string this module returns -- every
`error_summary` this module builds either names the credential env var (never its
value) or echoes back the DB-stored, key-free endpoint base URL.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from xml.etree import ElementTree

import personalos.knowledge_edge.state as ke
from personalos.knowledge_edge.adapters.contracts import AdapterFetchResult, DiscoveredMediaItem

# ------------------------------------------------------------------ shared vocabulary

YOUTUBE_API_KEY_ENV_VAR = "PERSONALOS_RAIL_KE_YOUTUBE_API_KEY"

LANE_BC_FEATURE_MODES = (
    "disabled",
    "fixture",
    "shadow_live",
    "active_read_only",
    "active_with_obsidian_handoff",
)
DEFAULT_LANE_BC_FEATURE_MODE = "disabled"
_LANE_BC_LIVE_ADMITTING_MODES = frozenset(
    {"shadow_live", "active_read_only", "active_with_obsidian_handoff"}
)

REQUEST_TIMEOUT_SECONDS = 10.0
_EXCERPT_MAX_CHARS = 500
_DOCTYPE_MARKER = b"<!DOCTYPE"


def validate_lane_bc_feature_mode(value: str) -> str:
    if value not in LANE_BC_FEATURE_MODES:
        allowed = ", ".join(LANE_BC_FEATURE_MODES)
        raise ValueError(f"Lane B/C feature mode must be one of: {allowed}")
    return value


class YoutubeRailFetchError(Exception):
    """Base class for adapter-raised (non-transport) fetch failures in this rail."""


class YoutubeRailRedirectQuarantined(YoutubeRailFetchError):
    """An HTTP redirect pointed at a different host (or downgraded to http://) than
    the request's own -- refused, never silently followed."""


class YoutubeRailResponseTooLarge(YoutubeRailFetchError):
    """The response exceeded its mechanism's byte cap -- refused before the body was
    fully buffered, let alone parsed."""


class MalformedChannelFeedError(Exception):
    """The fetched document could not be parsed as a well-formed Atom channel-upload
    feed."""


class MalformedSearchResponseError(Exception):
    """The fetched document could not be parsed as a well-formed `search.list` JSON
    response."""


def _extract_host(url: str) -> str:
    """Lowercased host, extracted with plain string ops -- no `urllib.parse` import
    (scoped to `engine/canonicalize.py` only); mirrors `podcasts.py`'s
    `_extract_host` (itself mirroring `dashboard._url_host`)."""
    remainder = url.split("://", 1)[-1]
    host = remainder.split("/", 1)[0]
    return host.rsplit("@", 1)[-1].split(":", 1)[0].lower()


class _HostConfinedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only when it stays on the request's own host and stays
    https:// -- identical logic to `podcasts.py`'s handler of the same name,
    duplicated rather than imported so this module stays independent of the podcast
    rail (`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1's per-module independence)."""

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
        if not newurl.startswith("https://"):
            raise YoutubeRailRedirectQuarantined(
                f"refusing redirect from {req.full_url!r} to a non-https:// target: "
                "HTTPS->HTTP downgrade is never followed"
            )
        redirect_host = _extract_host(newurl)
        if redirect_host != self._allowed_host:
            raise YoutubeRailRedirectQuarantined(
                f"refusing redirect from host {self._allowed_host!r} to a different "
                f"host {redirect_host!r}"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _BoundedHttpClient:
    """Shared stdlib-only bounded-read HTTPS GET, used by both mechanisms in this
    module with different byte caps. Never logs or echoes the request URL (the
    person-search mechanism's URL carries the API key in its query string)."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_response_bytes: int,
        opener: Any | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._opener = opener

    def fetch(self, url: str, *, headers: Mapping[str, str]) -> bytes:
        request = urllib.request.Request(url, method="GET", headers=dict(headers))
        opener = self._opener
        if opener is None:
            redirect_handler = _HostConfinedRedirectHandler(_extract_host(url))
            opener = urllib.request.build_opener(redirect_handler).open
        with opener(request, timeout=self._timeout_seconds) as response:
            raw = response.read(self._max_response_bytes + 1)
        if len(raw) > self._max_response_bytes:
            raise YoutubeRailResponseTooLarge(
                f"response exceeded the {self._max_response_bytes}-byte cap"
            )
        return raw


def _parse_iso8601_to_iso_utc(text: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _merge_counts(*counters: Mapping[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counter in counters:
        for reason, count in counter.items():
            merged[reason] = merged.get(reason, 0) + count
    return merged


def _unhealthy(source_id: str, cursor: str | None, error_summary: str) -> AdapterFetchResult:
    return AdapterFetchResult(
        source_id=source_id,
        items=(),
        next_cursor_value=cursor,
        healthy=False,
        error_summary=error_summary,
    )


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


# ------------------------------------------------------- mechanism 1: channel RSS polling

YOUTUBE_CHANNEL_FEED_BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="

# See module docstring's "Response-size cap" section for the full reasoning: a
# channel-upload feed is structurally bounded (YouTube returns only the latest ~15
# uploads), unlike Lane A's unbounded interview-show archives, so this cap is set
# well below `podcasts.py`'s 2 MB while still being generous headroom over any
# realistic 15-entry feed.
MAX_CHANNEL_FEED_RESPONSE_BYTES = 1_000_000
MAX_UPLOADS_PER_FETCH = 200

DEFAULT_CHANNEL_UPLOAD_FORMAT_HINT = "mentioned_only_appearance"

STATUS_CHANNEL_BLOCKED_FEATURE_MODE = "youtube_channel_rail_live_fetch_blocked_feature_mode_not_live"
STATUS_CHANNEL_BLOCKED_SOURCE_NOT_FOUND = "youtube_channel_rail_live_fetch_blocked_source_not_found"
STATUS_CHANNEL_BLOCKED_NO_ENDPOINT = "youtube_channel_rail_live_fetch_blocked_no_active_endpoint"
STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED = "youtube_channel_rail_live_fetch_blocked_source_not_verified"
STATUS_CHANNEL_FETCH_TRANSPORT_FAILED = "youtube_channel_rail_live_fetch_transport_failed"
STATUS_CHANNEL_FETCH_REDIRECT_QUARANTINED = "youtube_channel_rail_live_fetch_redirect_quarantined"
STATUS_CHANNEL_FETCH_RESPONSE_TOO_LARGE = "youtube_channel_rail_live_fetch_response_too_large"
STATUS_CHANNEL_FETCH_MALFORMED_FEED = "youtube_channel_rail_live_fetch_malformed_feed"

DROP_REASON_MISSING_VIDEO_ID = "missing_video_id"
DROP_REASON_MISSING_TITLE = "missing_title"
DROP_REASON_MISSING_CANONICAL_URL = "missing_canonical_url"
DROP_REASON_MISSING_OR_UNPARSEABLE_PUBLISHED_AT = "missing_or_unparseable_published_at"
DROP_REASON_DUPLICATE_VIDEO_ID_IN_BATCH = "duplicate_video_id_in_batch"


class ChannelFeedHttpClientProtocol(Protocol):
    def fetch(self, url: str) -> bytes: ...


class YoutubeChannelFeedHttpClient:
    """Thin stdlib-only HTTPS client for one channel-upload feed. No credential --
    the RSS mechanism needs no API key (D-YT option 1) -- so no `user_agent` is
    threaded through here the way `podcasts.py`'s client takes one; a fixed,
    descriptive User-Agent identifies this rail without inventing a new credential
    surface Session 1's external-access bundle never named
    (`PHASE0_PROVIDERS_AND_ACCESS.md` §6 lists no UA credential for this mechanism)."""

    _USER_AGENT = "PersonalOS-KnowledgeEdge-YoutubeChannelPoll/1.0"

    def __init__(
        self,
        *,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_CHANNEL_FEED_RESPONSE_BYTES,
        opener: Any | None = None,
    ) -> None:
        self._client = _BoundedHttpClient(
            timeout_seconds=timeout_seconds, max_response_bytes=max_response_bytes, opener=opener
        )

    def fetch(self, url: str) -> bytes:
        return self._client.fetch(url, headers={"User-Agent": self._USER_AGENT})


@dataclass(frozen=True)
class _ParsedUpload:
    video_id: str
    title: str
    canonical_url: str
    description_excerpt: str
    published_at: str
    channel_id: str
    raw_payload_summary: Mapping[str, Any] = field(default_factory=dict)


class LiveYoutubeChannelAdapter:
    """Live implementation of `ChannelVideoAdapter`
    (`personalos.knowledge_edge.adapters.contracts`): `fetch_uploads(source_id=...,
    cursor=..., now=...)` per source, same shape as `FixtureChannelVideoAdapter`."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        feature_mode: str = DEFAULT_LANE_BC_FEATURE_MODE,
        client: ChannelFeedHttpClientProtocol | None = None,
        max_items_per_fetch: int = MAX_UPLOADS_PER_FETCH,
        default_format_hint: str = DEFAULT_CHANNEL_UPLOAD_FORMAT_HINT,
    ) -> None:
        self._connection = connection
        self._feature_mode = validate_lane_bc_feature_mode(feature_mode)
        self._client = client if client is not None else YoutubeChannelFeedHttpClient()
        self._max_items_per_fetch = max_items_per_fetch
        if not default_format_hint.strip():
            raise ValueError("default_format_hint must not be empty")
        self._default_format_hint = default_format_hint

    def fetch_uploads(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now  # every field this adapter reports comes from the feed's own declared
        # published/videoId, never the wall clock -- "time is an input" (contracts.py).

        error, feed_url, channel_id = self._evaluate_gates(source_id=source_id)
        if error is not None:
            return _unhealthy(source_id, cursor, error)

        try:
            raw = self._client.fetch(feed_url)
        except YoutubeRailRedirectQuarantined as fetch_error:
            reason = f"{STATUS_CHANNEL_FETCH_REDIRECT_QUARANTINED}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)
        except YoutubeRailResponseTooLarge as fetch_error:
            reason = f"{STATUS_CHANNEL_FETCH_RESPONSE_TOO_LARGE}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)
        except (OSError, urllib.error.URLError) as fetch_error:
            reason = f"{STATUS_CHANNEL_FETCH_TRANSPORT_FAILED}: {fetch_error}"
            return _unhealthy(source_id, cursor, reason)

        try:
            uploads, parse_dropped = _parse_channel_feed_document(
                raw, expected_channel_id=channel_id
            )
        except MalformedChannelFeedError as parse_error:
            reason = f"{STATUS_CHANNEL_FETCH_MALFORMED_FEED}: {parse_error}"
            return _unhealthy(source_id, cursor, reason)

        discovered, batch_dropped = _build_discovered_uploads(
            source_id=source_id,
            channel_id=channel_id,
            uploads=uploads,
            default_format_hint=self._default_format_hint,
        )
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
        """Returns `(error, feed_url, channel_id)`. No credential gate: RSS
        channel-upload polling needs no API key (D-YT option 1) -- see module
        docstring -- so the order collapses to feature_mode -> source/endpoint
        verification, the same two ends of `podcasts.py`'s three-gate order with the
        middle (credentials) step absent because there is no credential here."""
        if self._feature_mode not in _LANE_BC_LIVE_ADMITTING_MODES:
            return (
                f"{STATUS_CHANNEL_BLOCKED_FEATURE_MODE}: feature_mode "
                f"{self._feature_mode!r} does not admit a live Lane B/C fetch "
                "('disabled'/'fixture' never fetch live)",
                None,
                None,
            )

        source = ke.get_source(self._connection, source_id)
        if source is None:
            return (
                f"{STATUS_CHANNEL_BLOCKED_SOURCE_NOT_FOUND}: no ke_sources row for "
                f"{source_id!r}",
                None,
                None,
            )

        endpoint = _resolve_primary_channel_endpoint(self._connection, source_id=source_id)
        if endpoint is None:
            return (
                f"{STATUS_CHANNEL_BLOCKED_NO_ENDPOINT}: no active channel_id endpoint "
                f"on file for {source_id!r}",
                None,
                None,
            )

        verified_at = endpoint["endpoint_verified_at"]
        verified_by = endpoint["verified_by"]
        verified_by_present = verified_by is not None and str(verified_by).strip() != ""
        if source["status"] != "active" or verified_at is None or not verified_by_present:
            return (
                f"{STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED}: source status is "
                f"{source['status']!r} (endpoint_verified_at={verified_at!r}, "
                f"verified_by={verified_by!r}); refusing until the Conductor-supervised "
                "smoke records a verification (see "
                "docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md)",
                None,
                None,
            )
        if _parse_iso8601_to_iso_utc(str(verified_at)) is None:
            return (
                f"{STATUS_CHANNEL_BLOCKED_SOURCE_NOT_VERIFIED}: endpoint_verified_at="
                f"{verified_at!r} is not a parseable timestamp; refusing rather than "
                "trusting a malformed verification record",
                None,
                None,
            )

        # `channel_id`-type endpoints store the raw channel identifier as `url`
        # (SOURCE_ENDPOINT_TYPES' existing 'channel_id' type, migration 00017) -- this
        # adapter always constructs the fetch URL itself against YouTube's own host,
        # never trusting an arbitrary stored URL the way `podcasts.py` trusts a stored
        # feed URL; that is a strictly narrower trust surface, not a weaker one.
        channel_id = endpoint["url"]
        if not channel_id.strip():
            return (
                f"{STATUS_CHANNEL_BLOCKED_NO_ENDPOINT}: channel_id endpoint for "
                f"{source_id!r} has an empty identifier",
                None,
                None,
            )
        feed_url = f"{YOUTUBE_CHANNEL_FEED_BASE_URL}{_percent_encode_query_value(channel_id)}"
        return (None, feed_url, channel_id)


def _resolve_primary_channel_endpoint(
    connection: sqlite3.Connection, *, source_id: str
) -> dict[str, Any] | None:
    endpoints = [
        endpoint
        for endpoint in ke.list_source_endpoints(connection, source_id=source_id)
        if endpoint["endpoint_type"] == "channel_id" and endpoint["status"] == "active"
    ]
    if not endpoints:
        return None
    primary = [endpoint for endpoint in endpoints if endpoint["is_primary"]]
    return primary[0] if primary else endpoints[0]


def _build_discovered_uploads(
    *, source_id: str, channel_id: str, uploads: Sequence[_ParsedUpload], default_format_hint: str
) -> tuple[tuple[DiscoveredMediaItem, ...], dict[str, int]]:
    seen_video_ids: set[str] = set()
    items: list[DiscoveredMediaItem] = []
    dropped: dict[str, int] = {}
    for upload in uploads:
        if upload.video_id in seen_video_ids:
            dropped[DROP_REASON_DUPLICATE_VIDEO_ID_IN_BATCH] = (
                dropped.get(DROP_REASON_DUPLICATE_VIDEO_ID_IN_BATCH, 0) + 1
            )
            continue
        seen_video_ids.add(upload.video_id)
        items.append(
            DiscoveredMediaItem(
                source_id=source_id,
                source_specific_id=upload.video_id,
                canonical_url=upload.canonical_url,
                title=upload.title,
                media_type="video_interview",
                source_precedence="official",
                format_hint=default_format_hint,
                alternate_urls=(),
                description_excerpt=upload.description_excerpt,
                published_at=upload.published_at,
                duration_seconds=None,
                feed_guid=upload.video_id,
                underlying_id=upload.video_id,
                channel_id=upload.channel_id or channel_id,
                cursor_value=f"{upload.published_at}|{upload.video_id}",
                raw_payload_summary=upload.raw_payload_summary,
            )
        )
    return tuple(items), dropped


def _parse_channel_feed_document(
    raw: bytes, *, expected_channel_id: str
) -> tuple[list[_ParsedUpload], dict[str, int]]:
    if _DOCTYPE_MARKER in raw:
        raise MalformedChannelFeedError(
            "channel feed document declares a DOCTYPE; refusing to parse untrusted "
            "external entities"
        )
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as parse_error:
        raise MalformedChannelFeedError(
            f"channel feed document is not well-formed XML: {parse_error}"
        ) from parse_error

    root_name = _local_name(root.tag)
    if root_name != "feed":
        raise MalformedChannelFeedError(
            f"unsupported channel feed root element <{root_name}>; expected an Atom <feed>"
        )

    entries = _findall_local(root, "entry")
    parsed = [
        _parse_channel_entry(entry, expected_channel_id=expected_channel_id)
        for entry in entries
    ]

    uploads: list[_ParsedUpload] = []
    dropped: dict[str, int] = {}
    for upload, reason in parsed:
        if upload is not None:
            uploads.append(upload)
        else:
            dropped[reason] = dropped.get(reason, 0) + 1
    return uploads, dropped


def _parse_channel_entry(
    entry: ElementTree.Element, *, expected_channel_id: str
) -> tuple[_ParsedUpload | None, str | None]:
    # yt:videoId -- namespace-stripped local name "videoId".
    video_id = _text(_find_local(entry, "videoId"))
    if not video_id:
        return None, DROP_REASON_MISSING_VIDEO_ID
    title = _text(_find_local(entry, "title"))
    if not title:
        return None, DROP_REASON_MISSING_TITLE

    canonical_url: str | None = None
    for link in _findall_local(entry, "link"):
        href = link.get("href")
        rel = link.get("rel")
        if href and (rel is None or rel == "alternate"):
            canonical_url = href
            break
    if not canonical_url:
        return None, DROP_REASON_MISSING_CANONICAL_URL

    published_raw = _text(_find_local(entry, "published")) or _text(_find_local(entry, "updated"))
    published_at = _parse_iso8601_to_iso_utc(published_raw) if published_raw else None
    if published_at is None:
        return None, DROP_REASON_MISSING_OR_UNPARSEABLE_PUBLISHED_AT

    channel_id = _text(_find_local(entry, "channelId")) or expected_channel_id

    description = ""
    media_group = _find_local(entry, "group")  # media:group -- local name "group"
    if media_group is not None:
        description = _text(_find_local(media_group, "description"))[:_EXCERPT_MAX_CHARS]

    return (
        _ParsedUpload(
            video_id=video_id,
            title=title,
            canonical_url=canonical_url,
            description_excerpt=description,
            published_at=published_at,
            channel_id=channel_id,
            raw_payload_summary={"video_id": video_id, "published_raw": published_raw},
        ),
        None,
    )


# ---------------------------------------------------- mechanism 2: search.list person search

# Documented reference value for what a `ke_source_endpoints` row of endpoint_type
# 'api_endpoint' should hold for the (not-yet-seeded, see module docstring)
# person-search source -- this module never hardcodes it into the actual fetch path;
# the URL always comes from the verified endpoint row, exactly like `podcasts.py`
# never hardcodes a feed URL either.
YOUTUBE_SEARCH_ENDPOINT_URL = "https://www.googleapis.com/youtube/v3/search"
DEFAULT_PERSON_SEARCH_SOURCE_ID = "ke-source-youtube-person-search"

MAX_SEARCH_RESPONSE_BYTES = 500_000  # generous for a maxResults<=50 snippet-only JSON reply.

# §5's worst-case formula (PHASE0_PROVIDERS_AND_ACCESS.md §5): 29 subjects x 3 alias
# variants x 2 pagination pages x 2 daily runs = 348 calls/day, worst case. This
# client makes exactly one call per `search_person` call (no built-in pagination --
# see module docstring), so one scan's (one daily run's) share of that budget is
# half the daily figure: 29 x 3 x 2 = 174. The exact §5 per-call unit-cost/quota
# figures are still TBC pending the Google Cloud Console confirmation this packet's
# own supervised-smoke doc requires
# (docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md) -- this cap is a local,
# conservative ceiling independent of that confirmation.
MAX_SEARCH_CALLS_PER_SCAN = 174

PERSON_SEARCH_CACHE_TTL_DAYS = 30  # amendment §10.4's documented 30-day refresh rule.

STATUS_SEARCH_BLOCKED_FEATURE_MODE = "youtube_search_rail_live_fetch_blocked_feature_mode_not_live"
STATUS_SEARCH_BLOCKED_CREDENTIAL_MISSING = "youtube_search_rail_live_fetch_blocked_credential_env_var_missing"
STATUS_SEARCH_BLOCKED_CREDENTIAL_EMPTY = "youtube_search_rail_live_fetch_blocked_credential_env_var_empty"
STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND = "youtube_search_rail_live_fetch_blocked_source_not_found"
STATUS_SEARCH_BLOCKED_NO_ENDPOINT = "youtube_search_rail_live_fetch_blocked_no_active_endpoint"
STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED = "youtube_search_rail_live_fetch_blocked_source_not_verified"
STATUS_SEARCH_BLOCKED_ENDPOINT_INSECURE_SCHEME = "youtube_search_rail_live_fetch_blocked_endpoint_insecure_scheme"
STATUS_SEARCH_BLOCKED_BUDGET_EXHAUSTED = "youtube_search_rail_live_fetch_blocked_per_scan_budget_exhausted"
STATUS_SEARCH_FETCH_TRANSPORT_FAILED = "youtube_search_rail_live_fetch_transport_failed"
STATUS_SEARCH_FETCH_REDIRECT_QUARANTINED = "youtube_search_rail_live_fetch_redirect_quarantined"
STATUS_SEARCH_FETCH_RESPONSE_TOO_LARGE = "youtube_search_rail_live_fetch_response_too_large"
STATUS_SEARCH_FETCH_MALFORMED_RESPONSE = "youtube_search_rail_live_fetch_malformed_response"

_QUERY_VALUE_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
)


def _percent_encode_query_value(value: str) -> str:
    """Minimal RFC 3986 percent-encoder for one query-string value. Deliberately not
    `urllib.parse.quote` -- that carve-out is scoped to `engine/canonicalize.py`
    only (this repo's own constraint, restated in this module's docstring)."""
    encoded = []
    for byte in value.encode("utf-8"):
        char = chr(byte)
        if byte < 128 and char in _QUERY_VALUE_UNRESERVED_CHARS:
            encoded.append(char)
        else:
            encoded.append(f"%{byte:02X}")
    return "".join(encoded)


def _build_search_url(*, base_url: str, query: str, api_key: str, max_results: int) -> str:
    params = (
        ("part", "snippet"),
        ("type", "video"),
        ("q", query),
        ("maxResults", str(max_results)),
        ("key", api_key),
    )
    query_string = "&".join(f"{name}={_percent_encode_query_value(value)}" for name, value in params)
    return f"{base_url}?{query_string}"


class YoutubeSearchHttpClientProtocol(Protocol):
    def fetch(self, url: str) -> bytes: ...


class YoutubeSearchHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_response_bytes: int = MAX_SEARCH_RESPONSE_BYTES,
        opener: Any | None = None,
    ) -> None:
        self._client = _BoundedHttpClient(
            timeout_seconds=timeout_seconds, max_response_bytes=max_response_bytes, opener=opener
        )

    def fetch(self, url: str) -> bytes:
        return self._client.fetch(url, headers={"Accept": "application/json"})


@dataclass(frozen=True)
class PersonSearchResult:
    """A `search.list` result item, narrowed to stable identifiers + display
    metadata only -- no directness/confidence/priority-shaped field is ever set here
    (D-YT option 1's "no derived classification persisted from Data API fields")."""

    video_id: str
    channel_id: str
    title: str
    channel_title: str
    published_at: str | None
    description_excerpt: str


@dataclass(frozen=True)
class PersonSearchCacheEntry:
    person_id: str
    query: str
    results: tuple[PersonSearchResult, ...]
    fetched_at: str
    expires_at: str


class PersonSearchCacheStore(Protocol):
    def get(self, *, person_id: str, query: str) -> PersonSearchCacheEntry | None: ...
    def put(self, entry: PersonSearchCacheEntry) -> None: ...
    def delete(self, *, person_id: str, query: str) -> None: ...
    def purge_expired(self, *, now: datetime) -> int: ...


class InMemoryPersonSearchCache:
    """Pure-Python reference implementation of `PersonSearchCacheStore`. See module
    docstring's "known, deliberately surfaced schema gap" section for why no
    SQLite-backed store ships in this packet. A `put` for a key already present
    fully replaces the prior entry (never appends), so a person/query whose result
    set changed on refresh -- including a previously-returned video no longer coming
    back, e.g. because it was deleted -- does not accumulate stale rows."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], PersonSearchCacheEntry] = {}

    def get(self, *, person_id: str, query: str) -> PersonSearchCacheEntry | None:
        return self._entries.get((person_id, query))

    def put(self, entry: PersonSearchCacheEntry) -> None:
        self._entries[(entry.person_id, entry.query)] = entry

    def delete(self, *, person_id: str, query: str) -> None:
        self._entries.pop((person_id, query), None)

    def purge_expired(self, *, now: datetime) -> int:
        now_iso = now.astimezone(UTC).isoformat()
        expired_keys = [key for key, entry in self._entries.items() if entry.expires_at <= now_iso]
        for key in expired_keys:
            del self._entries[key]
        return len(expired_keys)


@dataclass(frozen=True)
class PersonSearchOutcome:
    healthy: bool
    results: tuple[PersonSearchResult, ...] = ()
    error_summary: str | None = None
    calls_made: int = 0
    served_from_cache: bool = False


def _parse_search_response(raw: bytes) -> tuple[PersonSearchResult, ...]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as parse_error:
        raise MalformedSearchResponseError(
            f"search.list response is not valid JSON: {parse_error}"
        ) from parse_error

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise MalformedSearchResponseError(
            "search.list response is missing a top-level 'items' array"
        )

    results: list[PersonSearchResult] = []
    seen_video_ids: set[str] = set()
    for entry in payload["items"]:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        video_id = entry_id.get("videoId") if isinstance(entry_id, dict) else None
        if not video_id or video_id in seen_video_ids:
            continue
        seen_video_ids.add(video_id)
        snippet = entry.get("snippet") if isinstance(entry.get("snippet"), dict) else {}
        results.append(
            PersonSearchResult(
                video_id=video_id,
                channel_id=str(snippet.get("channelId") or ""),
                title=str(snippet.get("title") or ""),
                channel_title=str(snippet.get("channelTitle") or ""),
                published_at=snippet.get("publishedAt"),
                description_excerpt=str(snippet.get("description") or "")[:_EXCERPT_MAX_CHARS],
            )
        )
    return tuple(results)


class LiveYoutubePersonSearchClient:
    """`search.list` person-search client, narrowed per D-YT option 1: stable
    identifiers + display metadata only, TTL-cached (see module docstring), never
    persisting a derived classification. One `search_person` call == at most one
    live HTTP call (a cache hit makes zero)."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        feature_mode: str = DEFAULT_LANE_BC_FEATURE_MODE,
        credential_env_var: str = YOUTUBE_API_KEY_ENV_VAR,
        source_id: str = DEFAULT_PERSON_SEARCH_SOURCE_ID,
        client: YoutubeSearchHttpClientProtocol | None = None,
        cache_store: PersonSearchCacheStore | None = None,
        max_calls_per_scan: int = MAX_SEARCH_CALLS_PER_SCAN,
    ) -> None:
        self._connection = connection
        self._feature_mode = validate_lane_bc_feature_mode(feature_mode)
        self._credential_env_var = credential_env_var
        self._source_id = source_id
        self._client = client if client is not None else YoutubeSearchHttpClient()
        self._cache_store = cache_store if cache_store is not None else InMemoryPersonSearchCache()
        self._max_calls_per_scan = max_calls_per_scan
        self._calls_made_this_scan = 0

    def search_person(
        self, *, person_id: str, query: str, now: datetime, max_results: int = 5
    ) -> PersonSearchOutcome:
        if self._feature_mode not in _LANE_BC_LIVE_ADMITTING_MODES:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=(
                    f"{STATUS_SEARCH_BLOCKED_FEATURE_MODE}: feature_mode "
                    f"{self._feature_mode!r} does not admit a live Lane B/C fetch "
                    "('disabled'/'fixture' never fetch live)"
                ),
            )

        now_iso = now.astimezone(UTC).isoformat()
        cached = self._cache_store.get(person_id=person_id, query=query)
        if cached is not None and cached.expires_at > now_iso:
            return PersonSearchOutcome(
                healthy=True, results=cached.results, calls_made=0, served_from_cache=True
            )

        error, endpoint_url, api_key = self._evaluate_gates()
        if error is not None:
            return PersonSearchOutcome(healthy=False, error_summary=error)

        if self._calls_made_this_scan >= self._max_calls_per_scan:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=(
                    f"{STATUS_SEARCH_BLOCKED_BUDGET_EXHAUSTED}: per-scan call budget "
                    f"({self._max_calls_per_scan}) already spent"
                ),
            )

        search_url = _build_search_url(
            base_url=endpoint_url, query=query, api_key=api_key, max_results=max_results
        )
        self._calls_made_this_scan += 1
        try:
            raw = self._client.fetch(search_url)
        except YoutubeRailRedirectQuarantined as fetch_error:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=f"{STATUS_SEARCH_FETCH_REDIRECT_QUARANTINED}: {fetch_error}",
                calls_made=self._calls_made_this_scan,
            )
        except YoutubeRailResponseTooLarge as fetch_error:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=f"{STATUS_SEARCH_FETCH_RESPONSE_TOO_LARGE}: {fetch_error}",
                calls_made=self._calls_made_this_scan,
            )
        except (OSError, urllib.error.URLError) as fetch_error:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=f"{STATUS_SEARCH_FETCH_TRANSPORT_FAILED}: {fetch_error}",
                calls_made=self._calls_made_this_scan,
            )

        try:
            results = _parse_search_response(raw)
        except MalformedSearchResponseError as parse_error:
            return PersonSearchOutcome(
                healthy=False,
                error_summary=f"{STATUS_SEARCH_FETCH_MALFORMED_RESPONSE}: {parse_error}",
                calls_made=self._calls_made_this_scan,
            )

        expires_at = (now + timedelta(days=PERSON_SEARCH_CACHE_TTL_DAYS)).astimezone(UTC).isoformat()
        entry = PersonSearchCacheEntry(
            person_id=person_id,
            query=query,
            results=results,
            fetched_at=now_iso,
            expires_at=expires_at,
        )
        self._cache_store.put(entry)
        return PersonSearchOutcome(healthy=True, results=results, calls_made=self._calls_made_this_scan)

    def _evaluate_gates(self) -> tuple[str | None, str | None, str | None]:
        """Returns `(error, endpoint_url, api_key)`. Gate order matches
        `podcasts.py` exactly: credentials -> source/endpoint verification (this
        method assumes the feature_mode gate already passed -- `search_person` checks
        it first, before even a cache read, so a `disabled` feature_mode never serves
        cached results either)."""
        if self._credential_env_var not in os.environ:
            return (
                f"{STATUS_SEARCH_BLOCKED_CREDENTIAL_MISSING}: credential env var is "
                f"not set: {self._credential_env_var}",
                None,
                None,
            )
        api_key = os.environ[self._credential_env_var]
        if not api_key.strip():
            return (
                f"{STATUS_SEARCH_BLOCKED_CREDENTIAL_EMPTY}: credential env var is set "
                f"but empty: {self._credential_env_var}",
                None,
                None,
            )

        source = ke.get_source(self._connection, self._source_id)
        if source is None:
            return (
                f"{STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND}: no ke_sources row for "
                f"{self._source_id!r}",
                None,
                None,
            )

        endpoint = _resolve_primary_search_endpoint(self._connection, source_id=self._source_id)
        if endpoint is None:
            return (
                f"{STATUS_SEARCH_BLOCKED_NO_ENDPOINT}: no active api_endpoint on file "
                f"for {self._source_id!r}",
                None,
                None,
            )

        verified_at = endpoint["endpoint_verified_at"]
        verified_by = endpoint["verified_by"]
        verified_by_present = verified_by is not None and str(verified_by).strip() != ""
        if source["status"] != "active" or verified_at is None or not verified_by_present:
            return (
                f"{STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED}: source status is "
                f"{source['status']!r} (endpoint_verified_at={verified_at!r}, "
                f"verified_by={verified_by!r}); refusing until the Conductor-supervised "
                "smoke records a verification (see "
                "docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md)",
                None,
                None,
            )
        if _parse_iso8601_to_iso_utc(str(verified_at)) is None:
            return (
                f"{STATUS_SEARCH_BLOCKED_SOURCE_NOT_VERIFIED}: endpoint_verified_at="
                f"{verified_at!r} is not a parseable timestamp; refusing rather than "
                "trusting a malformed verification record",
                None,
                None,
            )

        endpoint_url = endpoint["url"]
        if not endpoint_url.startswith("https://"):
            return (
                f"{STATUS_SEARCH_BLOCKED_ENDPOINT_INSECURE_SCHEME}: endpoint url "
                f"{endpoint_url!r} is not https://; refusing to construct a live "
                "request over an insecure scheme",
                None,
                None,
            )

        return (None, endpoint_url, api_key)


def _resolve_primary_search_endpoint(
    connection: sqlite3.Connection, *, source_id: str
) -> dict[str, Any] | None:
    endpoints = [
        endpoint
        for endpoint in ke.list_source_endpoints(connection, source_id=source_id)
        if endpoint["endpoint_type"] == "api_endpoint" and endpoint["status"] == "active"
    ]
    if not endpoints:
        return None
    primary = [endpoint for endpoint in endpoints if endpoint["is_primary"]]
    return primary[0] if primary else endpoints[0]

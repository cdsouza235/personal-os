"""Adapter contracts -- the seam AD-1 names between the engine/orchestrator and
future live rails (``src/personalos/rails/knowledge_edge/**``, Phase 2/3).

This module defines only typed interfaces (``Protocol`` classes) and the plain,
frozen dataclasses those interfaces exchange. It contains no adapter logic itself.
Packet 1B's only implementations of these contracts are the fixtures in
``adapters/fixtures.py``; a live rail (P-KE-2A/2B/3A/3B) implements the same
``Protocol`` against a real network client instead, so ``scan_orchestrator.py``
never has to change when a fixture is swapped for a live adapter -- it depends on
these Protocols, not on any concrete class.

Every fetch method takes ``now`` as an explicit argument. No adapter -- fixture or,
later, live -- may call ``datetime.now()`` internally; "time is an input," per the
amendment's own idempotency requirements and this packet's determinism constraint.

Four source classes, matching AD-1's four ``rails/knowledge_edge/*.py`` modules:

- ``PodcastFeedAdapter`` -- Lane A, mirrors the future ``podcasts.py`` (RSS/Atom).
- ``ChannelVideoAdapter`` -- Lane B/C, mirrors the future ``youtube.py`` (official
  channel uploads / person-search results).
- ``EarningsEventAdapter`` -- Lane D, mirrors the future ``earnings_calendar.py``
  (roster/EDGAR/official-IR earnings schedule discovery, per D-PO-019).
- ``FilingsAdapter`` -- Lane D, mirrors the future ``sec_edgar.py`` (filing links
  that enrich an already-discovered event; it never creates a new event by
  itself, matching §10.4's SEC-EDGAR-as-supplementary-source framing).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class DiscoveredMediaItem:
    """One adapter-reported media item, prior to canonicalization/classification.

    ``feed_guid``, ``underlying_id``, and ``is_replay_of_underlying_id`` are the
    explicit, adapter-declared identifiers ``engine.dedup`` evaluates -- see that
    module's docstring for exactly how each is used.
    """

    source_id: str
    source_specific_id: str
    canonical_url: str
    title: str
    media_type: str
    source_precedence: str
    format_hint: str
    alternate_urls: tuple[str, ...] = ()
    description_excerpt: str = ""
    published_at: str | None = None
    duration_seconds: int | None = None
    feed_guid: str | None = None
    underlying_id: str | None = None
    is_replay_of_underlying_id: str | None = None
    channel_id: str | None = None
    matched_person_id: str | None = None
    matched_role_id: str | None = None
    matched_company_id: str | None = None
    cursor_value: str = ""
    raw_payload_summary: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveredEvent:
    """One adapter-reported scheduled event (Lane D), prior to persistence."""

    source_id: str
    company_id: str
    event_id_hint: str
    event_type: str
    scheduled_date: str
    time_precision: str
    schedule_confidence: str
    schedule_source: str
    start_time_utc: str | None = None
    end_time_utc: str | None = None
    source_timezone: str = "UTC"
    timing_label: str | None = None
    fiscal_period: str | None = None
    official_event_page_url: str | None = None
    live_webcast_url: str | None = None
    replay_url: str | None = None
    earnings_release_url: str | None = None
    filing_urls: tuple[str, ...] = ()
    slides_url: str | None = None
    shareholder_letter_url: str | None = None
    prepared_remarks_url: str | None = None
    cursor_value: str = ""


@dataclass(frozen=True)
class DiscoveredFiling:
    """One adapter-reported SEC EDGAR filing, used only to enrich an existing
    scheduled_event's ``filing_urls`` -- never to create a new event."""

    company_id: str
    filing_type: str
    filing_url: str
    filed_at: str
    fiscal_period: str | None
    cursor_value: str


@dataclass(frozen=True)
class AdapterFetchResult:
    """The uniform result shape every adapter contract returns.

    ``healthy=False`` means the orchestrator must not advance this source's scan
    cursor and must record degraded/failed source health (amendment §17.2: "never
    advance a failed source cursor").
    """

    source_id: str
    items: tuple[Any, ...]
    next_cursor_value: str | None
    healthy: bool
    error_summary: str | None = None


class PodcastFeedAdapter(Protocol):
    def fetch_episodes(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult: ...


class ChannelVideoAdapter(Protocol):
    def fetch_uploads(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult: ...


class EarningsEventAdapter(Protocol):
    def fetch_events(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult: ...


class FilingsAdapter(Protocol):
    def fetch_filings(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult: ...

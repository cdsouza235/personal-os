"""Fixture implementations of the Packet 1B adapter contracts.

Every record in this module is synthetic/invented test data -- structurally
realistic, never derived from or copied out of a real provider response (Packet
0C's golden-fixture capture has not happened yet in this repo; see the Packet 1B
handoff notes). No network-capable import appears anywhere in this module and none
may be added to it.

Each ``Fixture*Adapter`` is a generic, injectable implementation of one contract
from ``adapters/contracts.py``: it holds a plain ``dict[str, tuple[...]]`` of
per-source records and simulates "fetch since cursor" by a simple string
comparison against each record's own ``cursor_value`` (records are expected to
carry a monotonically sortable cursor value, e.g. a zero-padded sequence number or
an ISO timestamp). ``failing_sources`` lets a test simulate a degraded/failed
source without touching the happy-path dataset.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from personalos.knowledge_edge.adapters.contracts import (
    AdapterFetchResult,
    DiscoveredEvent,
    DiscoveredFiling,
    DiscoveredMediaItem,
)

FIXTURE_FAILURE_SUMMARY = "fixture-simulated source failure"


def _fetch(
    *,
    source_id: str,
    cursor: str | None,
    records_by_source: Mapping[str, tuple],
    failing_sources: frozenset[str],
) -> AdapterFetchResult:
    if source_id in failing_sources:
        return AdapterFetchResult(
            source_id=source_id,
            items=(),
            next_cursor_value=cursor,
            healthy=False,
            error_summary=FIXTURE_FAILURE_SUMMARY,
        )
    all_records = records_by_source.get(source_id, ())
    due = tuple(
        record
        for record in all_records
        if cursor is None or record.cursor_value > cursor
    )
    due_sorted = tuple(sorted(due, key=lambda record: record.cursor_value))
    next_cursor = due_sorted[-1].cursor_value if due_sorted else cursor
    return AdapterFetchResult(
        source_id=source_id, items=due_sorted, next_cursor_value=next_cursor, healthy=True
    )


class FixturePodcastFeedAdapter:
    def __init__(
        self,
        records_by_source: Mapping[str, tuple[DiscoveredMediaItem, ...]],
        *,
        failing_sources: frozenset[str] = frozenset(),
    ) -> None:
        self._records_by_source = records_by_source
        self._failing_sources = failing_sources

    def fetch_episodes(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now  # fixture filtering is cursor-based only; time is never read internally.
        return _fetch(
            source_id=source_id,
            cursor=cursor,
            records_by_source=self._records_by_source,
            failing_sources=self._failing_sources,
        )


class FixtureChannelVideoAdapter:
    def __init__(
        self,
        records_by_source: Mapping[str, tuple[DiscoveredMediaItem, ...]],
        *,
        failing_sources: frozenset[str] = frozenset(),
    ) -> None:
        self._records_by_source = records_by_source
        self._failing_sources = failing_sources

    def fetch_uploads(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now
        return _fetch(
            source_id=source_id,
            cursor=cursor,
            records_by_source=self._records_by_source,
            failing_sources=self._failing_sources,
        )


class FixtureEarningsEventAdapter:
    def __init__(
        self,
        records_by_source: Mapping[str, tuple[DiscoveredEvent, ...]],
        *,
        failing_sources: frozenset[str] = frozenset(),
    ) -> None:
        self._records_by_source = records_by_source
        self._failing_sources = failing_sources

    def fetch_events(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now
        return _fetch(
            source_id=source_id,
            cursor=cursor,
            records_by_source=self._records_by_source,
            failing_sources=self._failing_sources,
        )


class FixtureFilingsAdapter:
    def __init__(
        self,
        records_by_source: Mapping[str, tuple[DiscoveredFiling, ...]],
        *,
        failing_sources: frozenset[str] = frozenset(),
    ) -> None:
        self._records_by_source = records_by_source
        self._failing_sources = failing_sources

    def fetch_filings(
        self, *, source_id: str, cursor: str | None, now: datetime
    ) -> AdapterFetchResult:
        del now
        return _fetch(
            source_id=source_id,
            cursor=cursor,
            records_by_source=self._records_by_source,
            failing_sources=self._failing_sources,
        )

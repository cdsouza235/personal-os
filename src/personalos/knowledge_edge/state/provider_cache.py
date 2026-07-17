"""Knowledge Edge provider-metadata TTL cache state (P-KE-2B iteration 2, F1).

Backs `personalos.rails.knowledge_edge.youtube.SqlitePersonSearchCache`'s
`expiry`/`refresh`/`deletion` semantics (amendment Sec10.4/Sec13.4's 30-day rule)
against `ke_person_search_cache` (migration 00025), so a cached `search.list` result
survives a process restart instead of living only in an injectable in-memory store.

This module deliberately stores `results_json` as an opaque, already-serialized
string -- it never imports `PersonSearchResult` or anything else from
`rails/knowledge_edge/youtube.py`. That mirrors this package's existing state/rails
split (AD-1): the state layer persists rows, the rail decides what a row means.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _utc_now,
    _validate_iso_datetime,
    _validate_required_text,
)


def put_person_search_cache_entry(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    query: str,
    results_json: str,
    fetched_at: str,
    expires_at: str,
) -> dict[str, Any]:
    """Insert a cache row, or fully replace the prior row for the same
    `(person_id, query)` key -- a refreshed result set never accumulates alongside a
    stale one (matches `InMemoryPersonSearchCache.put`'s existing replace-not-append
    contract)."""
    person_id = _validate_required_text("person_id", person_id)
    query = _validate_required_text("query", query)
    results_json = _validate_required_text("results_json", results_json)
    fetched_at = _validate_iso_datetime("fetched_at", fetched_at)
    expires_at = _validate_iso_datetime("expires_at", expires_at)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_person_search_cache (
                person_id, query, results_json, fetched_at, expires_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (person_id, query) DO UPDATE SET
                results_json = excluded.results_json,
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """,
            (person_id, query, results_json, fetched_at, expires_at, now, now),
        )

    entry = get_person_search_cache_entry(connection, person_id=person_id, query=query)
    if entry is None:
        raise RuntimeError(
            "Person search cache entry was not persisted for "
            f"person_id={person_id!r}, query={query!r}"
        )
    return entry


def get_person_search_cache_entry(
    connection: sqlite3.Connection, *, person_id: str, query: str
) -> dict[str, Any] | None:
    person_id = _validate_required_text("person_id", person_id)
    query = _validate_required_text("query", query)
    row = connection.execute(
        "SELECT * FROM ke_person_search_cache WHERE person_id = ? AND query = ?",
        (person_id, query),
    ).fetchone()
    return dict(row) if row is not None else None


def delete_person_search_cache_entry(
    connection: sqlite3.Connection, *, person_id: str, query: str
) -> None:
    person_id = _validate_required_text("person_id", person_id)
    query = _validate_required_text("query", query)
    with connection:
        connection.execute(
            "DELETE FROM ke_person_search_cache WHERE person_id = ? AND query = ?",
            (person_id, query),
        )


def purge_expired_person_search_cache_entries(
    connection: sqlite3.Connection, *, now: str
) -> int:
    """Delete every row whose `expires_at` is at or before `now` (an ISO 8601
    datetime), honoring the 30-day TTL rule at the persistence layer rather than
    trusting every caller to filter expired rows on read. Returns the number of rows
    deleted."""
    now = _validate_iso_datetime("now", now)
    with connection:
        cursor = connection.execute(
            "DELETE FROM ke_person_search_cache WHERE expires_at <= ?", (now,)
        )
        return cursor.rowcount


def count_person_search_cache_entries(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_person_search_cache")

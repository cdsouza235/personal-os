"""P-KE-2B iteration 2 (finding F1): `ke_person_search_cache` (migration 00025) /
`personalos.knowledge_edge.state.provider_cache` -- the SQLite-backed TTL cache that
replaced `youtube.py`'s in-memory-only default, so expiry/refresh/deletion semantics
survive a process restart (amendment Sec10.4/Sec13.4's 30-day rule).
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations


class PutAndGetTest(unittest.TestCase):
    def test_get_returns_none_when_absent(self) -> None:
        with _migrated_connection() as connection:
            entry = ke.get_person_search_cache_entry(connection, person_id="p1", query="q")
        self.assertIsNone(entry)

    def test_put_then_get_round_trips(self) -> None:
        with _migrated_connection() as connection:
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="Kevin Warsh",
                results_json='[{"video_id": "v1"}]',
                fetched_at="2026-07-17T00:00:00+00:00",
                expires_at="2026-08-16T00:00:00+00:00",
            )
            entry = ke.get_person_search_cache_entry(connection, person_id="p1", query="Kevin Warsh")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["results_json"], '[{"video_id": "v1"}]')
        self.assertEqual(entry["fetched_at"], "2026-07-17T00:00:00+00:00")
        self.assertEqual(entry["expires_at"], "2026-08-16T00:00:00+00:00")

    def test_put_replaces_prior_entry_for_the_same_key(self) -> None:
        with _migrated_connection() as connection:
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q",
                results_json='[{"video_id": "stale"}]',
                fetched_at="2026-07-17T00:00:00+00:00",
                expires_at="2026-08-16T00:00:00+00:00",
            )
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q",
                results_json='[{"video_id": "fresh"}]',
                fetched_at="2026-07-18T00:00:00+00:00",
                expires_at="2026-08-17T00:00:00+00:00",
            )
            entry = ke.get_person_search_cache_entry(connection, person_id="p1", query="q")
            count = ke.count_person_search_cache_entries(connection)
        self.assertEqual(entry["results_json"], '[{"video_id": "fresh"}]')
        self.assertEqual(entry["fetched_at"], "2026-07-18T00:00:00+00:00")
        self.assertEqual(count, 1)

    def test_malformed_fetched_at_is_refused(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.put_person_search_cache_entry(
                    connection,
                    person_id="p1",
                    query="q",
                    results_json="[]",
                    fetched_at="not-a-timestamp",
                    expires_at="2026-08-16T00:00:00+00:00",
                )

    def test_malformed_expires_at_is_refused(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.put_person_search_cache_entry(
                    connection,
                    person_id="p1",
                    query="q",
                    results_json="[]",
                    fetched_at="2026-07-17T00:00:00+00:00",
                    expires_at="not-a-timestamp",
                )

    def test_empty_person_id_is_refused(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(ValueError):
                ke.put_person_search_cache_entry(
                    connection,
                    person_id="",
                    query="q",
                    results_json="[]",
                    fetched_at="2026-07-17T00:00:00+00:00",
                    expires_at="2026-08-16T00:00:00+00:00",
                )


class DeleteTest(unittest.TestCase):
    def test_delete_removes_entry(self) -> None:
        with _migrated_connection() as connection:
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q",
                results_json="[]",
                fetched_at="2026-07-17T00:00:00+00:00",
                expires_at="2026-08-16T00:00:00+00:00",
            )
            ke.delete_person_search_cache_entry(connection, person_id="p1", query="q")
            entry = ke.get_person_search_cache_entry(connection, person_id="p1", query="q")
        self.assertIsNone(entry)

    def test_delete_of_absent_key_is_a_no_op(self) -> None:
        with _migrated_connection() as connection:
            ke.delete_person_search_cache_entry(connection, person_id="does-not-exist", query="q")


class PurgeExpiredTest(unittest.TestCase):
    def test_purge_expired_removes_only_expired_entries(self) -> None:
        with _migrated_connection() as connection:
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q-old",
                results_json="[]",
                fetched_at="2026-06-01T00:00:00+00:00",
                expires_at="2026-07-01T00:00:00+00:00",
            )
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q-new",
                results_json="[]",
                fetched_at="2026-07-17T00:00:00+00:00",
                expires_at="2026-08-16T00:00:00+00:00",
            )
            removed = ke.purge_expired_person_search_cache_entries(
                connection, now="2026-07-17T00:00:00+00:00"
            )
            remaining = ke.count_person_search_cache_entries(connection)
        self.assertEqual(removed, 1)
        self.assertEqual(remaining, 1)

    def test_entry_expiring_exactly_at_now_is_purged(self) -> None:
        # <= boundary, matching InMemoryPersonSearchCache.purge_expired's own
        # `entry.expires_at <= now_iso` semantics.
        with _migrated_connection() as connection:
            ke.put_person_search_cache_entry(
                connection,
                person_id="p1",
                query="q",
                results_json="[]",
                fetched_at="2026-06-17T00:00:00+00:00",
                expires_at="2026-07-17T00:00:00+00:00",
            )
            removed = ke.purge_expired_person_search_cache_entries(
                connection, now="2026-07-17T00:00:00+00:00"
            )
        self.assertEqual(removed, 1)


class PersistsAcrossProcessRestartTest(unittest.TestCase):
    """F1's central requirement: a cache entry written by one connection must be
    readable by a brand-new connection opened later against the same on-disk
    database file -- an in-memory dict cannot do this, a SQLite table can."""

    def test_entry_survives_closing_and_reopening_the_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = PersonalOSConfig(
                environment=Environment.TEST,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "test" / "personalos.sqlite3",
            )

            first_connection = connect_sqlite(config, runtime_dir=runtime_dir)
            apply_migrations(first_connection)
            ke.put_person_search_cache_entry(
                first_connection,
                person_id="p1",
                query="Kevin Warsh",
                results_json='[{"video_id": "v1"}]',
                fetched_at="2026-07-17T00:00:00+00:00",
                expires_at="2026-08-16T00:00:00+00:00",
            )
            first_connection.close()

            second_connection = connect_sqlite(config, runtime_dir=runtime_dir)
            try:
                entry = ke.get_person_search_cache_entry(
                    second_connection, person_id="p1", query="Kevin Warsh"
                )
            finally:
                second_connection.close()

        self.assertIsNotNone(entry)
        self.assertEqual(entry["results_json"], '[{"video_id": "v1"}]')


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        try:
            apply_migrations(connection)
            yield connection
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()

"""P-KE-1A: scan_run / scan_cursor / source_health / coverage_report state (amendment
§11.1 cursor behavior, §10.5 coverage reporting, §17.3 health surface).
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


def _seed_source(connection: sqlite3.Connection, source_id: str = "src-1") -> None:
    if ke.get_source(connection, source_id) is None:
        ke.create_source(
            connection,
            source_id=source_id,
            source_type="podcast_feed",
            lane="curated_podcasts",
            name="Test Podcast",
        )


class ScanRunTest(unittest.TestCase):
    def test_scan_run_lifecycle(self) -> None:
        with _migrated_connection() as connection:
            created = ke.create_scan_run(
                connection, scan_run_id="run-1", run_type="full_scan"
            )
            self.assertEqual(created["status"], "running")
            self.assertIsNone(created["completed_at"])

            completed = ke.complete_scan_run(
                connection,
                scan_run_id="run-1",
                status="completed",
                summary={"discovered": 12},
            )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["summary"], {"discovered": 12})
        self.assertIsNotNone(completed["completed_at"])

    def test_complete_scan_run_cannot_set_status_back_to_running(self) -> None:
        with _migrated_connection() as connection:
            ke.create_scan_run(connection, scan_run_id="run-1", run_type="full_scan")
            with self.assertRaises(ValueError):
                ke.complete_scan_run(connection, scan_run_id="run-1", status="running")

    def test_completed_at_cannot_precede_started_at(self) -> None:
        with _migrated_connection() as connection:
            ke.create_scan_run(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                started_at="2026-07-16T12:00:00+00:00",
            )
            with self.assertRaises(ValueError):
                ke.complete_scan_run(
                    connection,
                    scan_run_id="run-1",
                    status="completed",
                    completed_at="2026-07-16T11:00:00+00:00",
                )


class ScanCursorTest(unittest.TestCase):
    def test_cursor_created_then_advanced(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            first = ke.advance_scan_cursor(
                connection,
                cursor_id="cursor-1",
                source_id="src-1",
                last_successful_cursor_value="guid-1",
            )
            second = ke.advance_scan_cursor(
                connection,
                cursor_id="cursor-1",
                source_id="src-1",
                last_successful_cursor_value="guid-2",
            )
            fetched = ke.get_scan_cursor(connection, source_id="src-1")
            cursor_count = ke.count_scan_cursors(connection)
        self.assertEqual(first["last_successful_cursor_value"], "guid-1")
        self.assertEqual(second["last_successful_cursor_value"], "guid-2")
        self.assertEqual(fetched["last_successful_cursor_value"], "guid-2")
        # One cursor row per source: advancing updates in place, does not append.
        self.assertEqual(cursor_count, 1)

    def test_cursor_source_id_is_unique(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            ke.advance_scan_cursor(
                connection,
                cursor_id="cursor-1",
                source_id="src-1",
                last_successful_cursor_value="guid-1",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_scan_cursors (
                        cursor_id, source_id, last_successful_cursor_value,
                        last_successful_at, overlap_window_seconds, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "cursor-2", "src-1", "guid-2", "2026-07-16T00:00:00+00:00",
                        3600, "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )


class SourceHealthTest(unittest.TestCase):
    def test_source_health_upsert_transitions_status(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection)
            ke.upsert_source_health(
                connection, health_id="health-1", source_id="src-1", status="healthy"
            )
            degraded = ke.upsert_source_health(
                connection,
                health_id="health-1",
                source_id="src-1",
                status="degraded",
                consecutive_failure_count=2,
                last_error_summary="timeout",
            )
        self.assertEqual(degraded["status"], "degraded")
        self.assertEqual(degraded["consecutive_failure_count"], 2)

    def test_list_source_health_filters_by_status(self) -> None:
        with _migrated_connection() as connection:
            _seed_source(connection, "src-1")
            _seed_source(connection, "src-2")
            ke.upsert_source_health(
                connection, health_id="health-1", source_id="src-1", status="healthy"
            )
            ke.upsert_source_health(
                connection, health_id="health-2", source_id="src-2", status="failed"
            )
            failed_only = ke.list_source_health(connection, status="failed")
        self.assertEqual([row["source_id"] for row in failed_only], ["src-2"])


class CoverageReportTest(unittest.TestCase):
    def test_coverage_report_round_trip(self) -> None:
        with _migrated_connection() as connection:
            ke.create_scan_run(connection, scan_run_id="run-1", run_type="morning_refresh")
            created = ke.create_coverage_report(
                connection,
                coverage_report_id="report-1",
                scan_run_id="run-1",
                report_date="2026-07-16",
                report={"sources_checked": 5, "sources_failed": 0},
                overall_summary="All sources healthy.",
            )
        self.assertEqual(created["report"], {"sources_checked": 5, "sources_failed": 0})

    def test_coverage_report_requires_existing_scan_run(self) -> None:
        with _migrated_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO ke_coverage_reports (
                        coverage_report_id, scan_run_id, report_date, report_json,
                        overall_summary, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "report-orphan", "missing-run", "2026-07-16", "{}", "",
                        "2026-07-16T00:00:00+00:00",
                    ),
                )


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(
    config: PersonalOSConfig,
    *,
    runtime_dir: Path,
) -> Iterator[sqlite3.Connection]:
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
            apply_migrations(connection)
            yield connection


if __name__ == "__main__":
    unittest.main()

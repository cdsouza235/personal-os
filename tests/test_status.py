import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from personalos.config import (
    DEFAULT_TIMEZONE,
    Environment,
    PersonalOSConfig,
    ProductionConfigUnavailable,
    RUNTIME_DIR,
    load_config,
)
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.events import EventType, create_system_event, record_system_event
from personalos.state import upsert_permission_setting
from personalos.status import create_status_summary, list_recent_system_events


class StatusSummaryTest(unittest.TestCase):
    def test_summary_handles_empty_tables(self) -> None:
        with _migrated_test_connection() as connection:
            summary = create_status_summary(connection)

        self.assertEqual(
            summary["counts"],
            {
                "routines": 0,
                "priorities": 0,
                "projects": 0,
                "followups": 0,
                "fitness_integration_state": 0,
                "fitness_validation_runs": 0,
                "fitness_file_contracts": 0,
                "external_write_intents": 0,
                "external_write_attempts": 0,
                "idempotency_records": 0,
                "synthesis_apply_runs": 0,
                "synthesis_apply_items": 0,
                "scheduler_jobs": 0,
                "scheduler_runs": 0,
            },
        )
        self.assertEqual(summary["permission_settings"], [])
        self.assertEqual(summary["permission_settings_count"], 0)
        self.assertEqual(summary["recent_system_events"], [])
        self.assertNotIn("environment", summary)
        self.assertEqual(datetime.fromisoformat(summary["generated_at_utc"]).tzinfo, UTC)

    def test_summary_returns_core_counts_permissions_events_and_environment(self) -> None:
        with _migrated_test_connection() as connection:
            _insert_core_state_rows(connection)
            permission = upsert_permission_setting(
                connection,
                category="routine_todoist_tasks",
                mode="auto_write",
                metadata={"source": "tests"},
                updated_by="tests",
                updated_at_utc="2026-06-13T10:00:00+00:00",
            )
            event = create_system_event(
                source="tests.status",
                event_type=EventType.INFO,
                message="status event",
                metadata={"safe": True},
            )
            record_system_event(connection, event)
            config = PersonalOSConfig(
                environment=Environment.TEST,
                timezone=DEFAULT_TIMEZONE,
                database_path=Path("unused-by-summary.sqlite3"),
            )

            summary = create_status_summary(connection, config=config)

        self.assertEqual(
            summary["counts"],
            {
                "routines": 1,
                "priorities": 1,
                "projects": 1,
                "followups": 1,
                "fitness_integration_state": 0,
                "fitness_validation_runs": 0,
                "fitness_file_contracts": 0,
                "external_write_intents": 0,
                "external_write_attempts": 0,
                "idempotency_records": 0,
                "synthesis_apply_runs": 0,
                "synthesis_apply_items": 0,
                "scheduler_jobs": 0,
                "scheduler_runs": 0,
            },
        )
        self.assertEqual(summary["permission_settings"], [permission])
        self.assertEqual(summary["permission_settings_count"], 1)
        self.assertEqual(summary["environment"], "test")
        self.assertEqual(len(summary["recent_system_events"]), 1)
        self.assertEqual(summary["recent_system_events"][0]["event_id"], event.event_id)
        self.assertEqual(summary["recent_system_events"][0]["metadata"], {"safe": True})

    def test_recent_system_events_are_limited_and_ordered(self) -> None:
        with _migrated_test_connection() as connection:
            first = create_system_event(
                source="tests.status",
                event_type=EventType.INFO,
                message="first",
            )
            second = create_system_event(
                source="tests.status",
                event_type=EventType.WARNING,
                message="second",
            )
            record_system_event(connection, first)
            record_system_event(connection, second)

            recent_events = list_recent_system_events(connection, limit=1)

        self.assertEqual(len(recent_events), 1)
        self.assertEqual(recent_events[0]["event_id"], second.event_id)
        self.assertEqual(recent_events[0]["event_type"], "warning")

    def test_recent_system_event_negative_limit_is_rejected(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ValueError):
                list_recent_system_events(connection, limit=-1)

    def test_summary_helpers_do_not_create_repo_runtime_artifacts(self) -> None:
        runtime_dir_existed_before = RUNTIME_DIR.exists()

        with _migrated_test_connection() as connection:
            summary = create_status_summary(connection)

        config = load_config(Environment.DEVELOPMENT)
        self.assertEqual(summary["counts"]["routines"], 0)
        self.assertFalse(config.database_path.exists())
        if not runtime_dir_existed_before:
            self.assertFalse(RUNTIME_DIR.exists())

    def test_production_database_access_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)

            self.assertFalse(production_config.database_path.exists())


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        try:
            yield connection
        finally:
            connection.close()


def _insert_core_state_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-06-13T10:00:00+00:00"
    with connection:
        connection.execute(
            """
            INSERT INTO routines (
                routine_id,
                name,
                status,
                enabled,
                settings_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("routine-1", "Routine", "active", 1, "{}", "", timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO priorities (
                priority_id,
                title,
                status,
                metadata_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("priority-1", "Priority", "active", "{}", "", timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO projects (
                project_id,
                title,
                status,
                metadata_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("project-1", "Project", "active", "{}", "", timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO followups (
                followup_id,
                title,
                status,
                source,
                metadata_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("followup-1", "Followup", "open", "tests", "{}", "", timestamp, timestamp),
        )

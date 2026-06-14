import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
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
from personalos.state import (
    count_followups,
    count_priorities,
    count_projects,
    count_routines,
    get_permission_setting,
    list_followups,
    list_permission_settings,
    list_priorities,
    list_projects,
    list_routines,
    upsert_permission_setting,
)


class StateStoreHelperTest(unittest.TestCase):
    def test_permission_settings_can_be_inserted_updated_fetched_and_listed(self) -> None:
        with _migrated_test_connection() as connection:
            inserted = upsert_permission_setting(
                connection,
                category="routine_todoist_tasks",
                mode="auto_write",
                metadata={"source": "test", "rank": 2},
                updated_by="tests",
                updated_at_utc="2026-06-13T10:00:00+00:00",
            )
            updated = upsert_permission_setting(
                connection,
                category="routine_todoist_tasks",
                mode="approval_required",
                metadata={"source": "updated", "rank": 1},
                updated_by="tests",
                updated_at_utc="2026-06-13T11:00:00+00:00",
            )
            second = upsert_permission_setting(
                connection,
                category="messages_to_other_people",
                mode="approval_required",
                metadata={},
                updated_by="tests",
                updated_at_utc="2026-06-13T12:00:00+00:00",
            )

            fetched = get_permission_setting(connection, "routine_todoist_tasks")
            missing = get_permission_setting(connection, "missing")
            listed = list_permission_settings(connection)

        self.assertEqual(inserted["mode"], "auto_write")
        self.assertEqual(updated["mode"], "approval_required")
        self.assertEqual(updated["metadata"], {"rank": 1, "source": "updated"})
        self.assertEqual(fetched, updated)
        self.assertIsNone(missing)
        self.assertEqual(
            [item["category"] for item in listed],
            [second["category"], updated["category"]],
        )

    def test_permission_metadata_is_json_safe_and_sorted_in_storage(self) -> None:
        with _migrated_test_connection() as connection:
            setting = upsert_permission_setting(
                connection,
                category="self_calendar_blocks",
                mode="auto_write",
                metadata={"z": "last", "a": "first", "unicode": "check"},
                updated_by="tests",
                updated_at_utc="2026-06-13T10:00:00+00:00",
            )
            row = connection.execute(
                "SELECT metadata_json FROM permission_settings WHERE category = ?",
                ("self_calendar_blocks",),
            ).fetchone()

        self.assertEqual(
            setting["metadata"],
            {"a": "first", "unicode": "check", "z": "last"},
        )
        self.assertEqual(row["metadata_json"], '{"a":"first","unicode":"check","z":"last"}')

    def test_unserializable_permission_metadata_is_rejected_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(TypeError):
                upsert_permission_setting(
                    connection,
                    category="routine_todoist_tasks",
                    mode="auto_write",
                    metadata={"bad": object()},
                    updated_by="tests",
                )

            row = connection.execute("SELECT COUNT(*) FROM permission_settings").fetchone()

        self.assertEqual(row[0], 0)

    def test_non_finite_permission_metadata_is_rejected_without_write(self) -> None:
        non_finite_values = (float("nan"), float("inf"), float("-inf"))

        with _migrated_test_connection() as connection:
            for value in non_finite_values:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        upsert_permission_setting(
                            connection,
                            category="routine_todoist_tasks",
                            mode="auto_write",
                            metadata={"bad": value},
                            updated_by="tests",
                        )

                    row = connection.execute(
                        "SELECT COUNT(*) FROM permission_settings"
                    ).fetchone()
                    self.assertEqual(row[0], 0)

    def test_invalid_stored_metadata_is_rejected_fail_closed(self) -> None:
        with _migrated_test_connection() as connection:
            connection.execute(
                """
                INSERT INTO permission_settings (
                    category,
                    mode,
                    metadata_json,
                    updated_at_utc,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "routine_todoist_tasks",
                    "auto_write",
                    "[]",
                    "2026-06-13T10:00:00+00:00",
                    "tests",
                ),
            )
            connection.commit()

            with self.assertRaises(ValueError):
                get_permission_setting(connection, "routine_todoist_tasks")

    def test_read_only_core_state_helpers_list_and_count_rows(self) -> None:
        with _migrated_test_connection() as connection:
            _insert_core_state_rows(connection)

            routines = list_routines(connection)
            priorities = list_priorities(connection)
            projects = list_projects(connection)
            followups = list_followups(connection)

            counts = {
                "routines": count_routines(connection),
                "priorities": count_priorities(connection),
                "projects": count_projects(connection),
                "followups": count_followups(connection),
            }

        self.assertEqual(counts, {"routines": 1, "priorities": 1, "projects": 1, "followups": 1})
        self.assertEqual(routines[0]["settings"], {"cadence": "manual"})
        self.assertTrue(routines[0]["enabled"])
        self.assertEqual(priorities[0]["metadata"], {"weight": 1})
        self.assertEqual(projects[0]["metadata"], {"area": "ops"})
        self.assertEqual(followups[0]["source"], "tests")
        self.assertEqual(followups[0]["metadata"], {"channel": "manual"})

    def test_helpers_do_not_create_repo_runtime_artifacts(self) -> None:
        runtime_dir_existed_before = RUNTIME_DIR.exists()

        with _migrated_test_connection() as connection:
            upsert_permission_setting(
                connection,
                category="routine_todoist_tasks",
                mode="auto_write",
                metadata={},
                updated_by="tests",
            )
            self.assertEqual(count_routines(connection), 0)

        config = load_config(Environment.DEVELOPMENT)
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
            (
                "routine-1",
                "Manual Routine",
                "active",
                1,
                '{"cadence":"manual"}',
                "",
                timestamp,
                timestamp,
            ),
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
            ("priority-1", "Priority", "active", '{"weight":1}', "", timestamp, timestamp),
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
            ("project-1", "Project", "active", '{"area":"ops"}', "", timestamp, timestamp),
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
            (
                "followup-1",
                "Followup",
                "open",
                "tests",
                '{"channel":"manual"}',
                "",
                timestamp,
                timestamp,
            ),
        )

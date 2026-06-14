import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig, RUNTIME_DIR
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.priorities import (
    PRIORITY_ENGINE_READ_PERMISSION,
    PRIORITY_ENGINE_WRITE_PERMISSION,
    PriorityEnginePermissionDenied,
    create_priority_flow,
    create_priority_record,
    read_active_priority_summary,
    read_priorities,
    read_priority,
    read_priority_count,
    read_priority_counts_by_status,
    read_priority_dashboard_summary,
    transition_priority_status_flow,
    transition_priority_status_record,
    update_priority_flow,
    update_priority_record,
)
from personalos.state import (
    count_priorities,
    count_priorities_by_status,
    create_priority,
    get_priority,
    list_active_priorities,
    list_priorities,
    summarize_priorities,
    update_priority,
    update_priority_status,
    upsert_permission_setting,
)


class PriorityStateHelperTest(unittest.TestCase):
    def test_create_get_list_count_update_and_transition_priority(self) -> None:
        with _migrated_test_connection() as connection:
            created = create_priority(
                connection,
                priority_id="priority-1",
                title="Priority Foundation",
                status="active",
                metadata={"source": "manual", "weight": 1},
                notes="dev/test only",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            fetched = get_priority(connection, "priority-1")
            listed = list_priorities(connection)
            updated = update_priority(
                connection,
                priority_id="priority-1",
                title="Priority Registry",
                metadata={"source": "manual", "weight": 2},
                notes="updated locally",
                updated_at_utc="2026-06-14T11:00:00+00:00",
            )
            transitioned = update_priority_status(
                connection,
                priority_id="priority-1",
                status="paused",
                updated_at_utc="2026-06-14T12:00:00+00:00",
            )

        self.assertEqual(created["priority_id"], "priority-1")
        self.assertEqual(created["metadata"], {"source": "manual", "weight": 1})
        self.assertEqual(fetched, created)
        self.assertEqual([priority["priority_id"] for priority in listed], ["priority-1"])
        self.assertEqual(updated["title"], "Priority Registry")
        self.assertEqual(updated["metadata"], {"source": "manual", "weight": 2})
        self.assertEqual(transitioned["status"], "paused")
        self.assertEqual(transitioned["updated_at_utc"], "2026-06-14T12:00:00+00:00")

    def test_priority_validation_rejects_malformed_create_inputs_without_write(self) -> None:
        invalid_inputs = (
            {"priority_id": "", "title": "Priority"},
            {"priority_id": "priority-1", "title": ""},
            {"priority_id": "priority-1", "title": "Priority", "status": "ranking"},
            {"priority_id": "priority-1", "title": "Priority", "metadata": []},
            {"priority_id": "priority-1", "title": "Priority", "metadata": {"bad": float("nan")}},
            {"priority_id": "priority-1", "title": "Priority", "notes": 1},
            {
                "priority_id": "priority-1",
                "title": "Priority",
                "created_at_utc": "2026-06-14T10:00:00",
            },
            {
                "priority_id": "priority-1",
                "title": "Priority",
                "updated_at_utc": "not-a-datetime",
            },
        )

        with _migrated_test_connection() as connection:
            for item in invalid_inputs:
                with self.subTest(item=item):
                    with self.assertRaises((TypeError, ValueError)):
                        create_priority(connection, **item)

                    self.assertEqual(count_priorities(connection), 0)

    def test_priority_update_validation_rejects_malformed_inputs_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(
                connection,
                priority_id="priority-1",
                title="Priority",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )

            invalid_updates = (
                {},
                {"status": "ranking"},
                {"metadata": []},
                {"notes": 1},
                {"updated_at_utc": "2026-06-14T11:00:00"},
            )
            for item in invalid_updates:
                with self.subTest(item=item):
                    with self.assertRaises((TypeError, ValueError)):
                        update_priority(
                            connection,
                            priority_id="priority-1",
                            **item,
                        )

            with self.assertRaises(ValueError):
                update_priority(
                    connection,
                    priority_id="missing-priority",
                    title="Missing",
                )

            priority = get_priority(connection, "priority-1")

        self.assertEqual(priority["title"], "Priority")
        self.assertEqual(priority["status"], "active")
        self.assertEqual(priority["updated_at_utc"], "2026-06-14T10:00:00+00:00")

    def test_priority_summary_helpers_return_deterministic_shapes(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(connection, priority_id="active-1", title="A Active")
            create_priority(connection, priority_id="active-2", title="B Active")
            create_priority(connection, priority_id="paused-1", title="C Paused", status="paused")
            create_priority(
                connection,
                priority_id="completed-1",
                title="D Completed",
                status="completed",
            )
            summary = summarize_priorities(connection)
            counts_by_status = count_priorities_by_status(connection)
            active_priorities = list_active_priorities(connection)

        self.assertEqual(
            counts_by_status,
            {"active": 2, "paused": 1, "completed": 1, "archived": 0},
        )
        self.assertEqual(summary["total_count"], 4)
        self.assertEqual(summary["active_count"], 2)
        self.assertEqual(
            [priority["priority_id"] for priority in active_priorities],
            ["active-1", "active-2"],
        )
        self.assertEqual(summary["active_priorities"], active_priorities)


class PriorityEnginePermissionTest(unittest.TestCase):
    def test_missing_read_permission_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(PriorityEnginePermissionDenied):
                read_priorities(connection)

    def test_disabled_read_permission_denies_reads(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_READ_PERMISSION, PermissionMode.DISABLED)

            with self.assertRaises(PriorityEnginePermissionDenied):
                read_priorities(connection)

    def test_enabled_read_permission_allows_read_helpers(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(connection, priority_id="priority-1", title="Priority")
            _set_permission(connection, PRIORITY_ENGINE_READ_PERMISSION, PermissionMode.AUTO_WRITE)

            priority = read_priority(connection, priority_id="priority-1")
            priorities = read_priorities(connection)
            count = read_priority_count(connection)
            counts_by_status = read_priority_counts_by_status(connection)
            active_summary = read_active_priority_summary(connection)
            dashboard_summary = read_priority_dashboard_summary(connection)

        self.assertEqual(priority["priority_id"], "priority-1")
        self.assertEqual([item["priority_id"] for item in priorities], ["priority-1"])
        self.assertEqual(count, 1)
        self.assertEqual(counts_by_status["active"], 1)
        self.assertEqual(active_summary["active_count"], 1)
        self.assertEqual(dashboard_summary["total_count"], 1)

    def test_missing_write_permission_fails_closed_for_create(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(PriorityEnginePermissionDenied):
                create_priority_record(
                    connection,
                    priority_id="priority-1",
                    title="Priority",
                )

            self.assertEqual(count_priorities(connection), 0)

    def test_disabled_write_permission_denies_create(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.DISABLED)

            with self.assertRaises(PriorityEnginePermissionDenied):
                create_priority_record(
                    connection,
                    priority_id="priority-1",
                    title="Priority",
                )

            self.assertEqual(count_priorities(connection), 0)

    def test_approval_required_write_permission_denies_without_prompting(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(
                connection,
                PRIORITY_ENGINE_WRITE_PERMISSION,
                PermissionMode.APPROVAL_REQUIRED,
            )

            with self.assertRaises(PriorityEnginePermissionDenied):
                create_priority_record(
                    connection,
                    priority_id="priority-1",
                    title="Priority",
                )

            self.assertEqual(count_priorities(connection), 0)

    def test_enabled_write_permission_allows_create_update_and_transition(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            created = create_priority_record(
                connection,
                priority_id="priority-1",
                title="Priority",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            updated = update_priority_record(
                connection,
                priority_id="priority-1",
                title="Updated Priority",
                updated_at_utc="2026-06-14T11:00:00+00:00",
            )
            transitioned = transition_priority_status_record(
                connection,
                priority_id="priority-1",
                status="completed",
                updated_at_utc="2026-06-14T12:00:00+00:00",
            )

        self.assertEqual(created["status"], "active")
        self.assertEqual(updated["title"], "Updated Priority")
        self.assertEqual(transitioned["status"], "completed")


class PriorityFlowTest(unittest.TestCase):
    def test_missing_write_permission_blocks_create_flow_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            result = create_priority_flow(
                connection,
                priority_id="priority-1",
                title="Priority",
                dry_run=True,
            )
            count = count_priorities(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing priority engine permission", result["reason"])
        self.assertFalse(result["database_write"])
        self.assertEqual(count, 0)

    def test_dry_run_priority_creation_does_not_mutate_database(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            result = create_priority_flow(
                connection,
                priority_id="priority-1",
                title="Priority",
                dry_run=True,
                metadata={"source": "unit-test"},
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            count = count_priorities(connection)

        self.assertEqual(result["status"], "would_create")
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["no_send"])
        self.assertFalse(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(result["would_write"]["metadata"], {"source": "unit-test"})
        self.assertEqual(count, 0)

    def test_non_dry_run_priority_creation_writes_dev_test_sqlite_only(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            result = create_priority_flow(
                connection,
                priority_id="priority-1",
                title="Priority",
                dry_run=False,
                metadata={"source": "unit-test"},
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            count = count_priorities(connection)
            priority = get_priority(connection, "priority-1")

        self.assertEqual(result["status"], "created")
        self.assertFalse(result["dry_run"])
        self.assertTrue(result["no_send"])
        self.assertTrue(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(count, 1)
        self.assertEqual(result["priority"], priority)

    def test_dry_run_priority_update_does_not_mutate_database(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(
                connection,
                priority_id="priority-1",
                title="Priority",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            result = update_priority_flow(
                connection,
                priority_id="priority-1",
                title="Updated Priority",
                metadata={"source": "unit-test"},
                dry_run=True,
                updated_at_utc="2026-06-14T11:00:00+00:00",
            )
            priority = get_priority(connection, "priority-1")

        self.assertEqual(result["status"], "would_update")
        self.assertFalse(result["database_write"])
        self.assertEqual(result["would_write"]["title"], "Updated Priority")
        self.assertEqual(priority["title"], "Priority")
        self.assertEqual(priority["updated_at_utc"], "2026-06-14T10:00:00+00:00")

    def test_dry_run_priority_status_transition_does_not_mutate_database(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(
                connection,
                priority_id="priority-1",
                title="Priority",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            result = transition_priority_status_flow(
                connection,
                priority_id="priority-1",
                status="archived",
                dry_run=True,
                updated_at_utc="2026-06-14T11:00:00+00:00",
            )
            priority = get_priority(connection, "priority-1")

        self.assertEqual(result["status"], "would_transition")
        self.assertFalse(result["database_write"])
        self.assertEqual(result["would_write"]["status"], "archived")
        self.assertEqual(priority["status"], "active")
        self.assertEqual(priority["updated_at_utc"], "2026-06-14T10:00:00+00:00")

    def test_non_dry_run_priority_update_and_transition_write_dev_test_sqlite_only(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(
                connection,
                priority_id="priority-1",
                title="Priority",
                created_at_utc="2026-06-14T10:00:00+00:00",
                updated_at_utc="2026-06-14T10:00:00+00:00",
            )
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            update_result = update_priority_flow(
                connection,
                priority_id="priority-1",
                title="Updated Priority",
                dry_run=False,
                updated_at_utc="2026-06-14T11:00:00+00:00",
            )
            transition_result = transition_priority_status_flow(
                connection,
                priority_id="priority-1",
                status="completed",
                dry_run=False,
                updated_at_utc="2026-06-14T12:00:00+00:00",
            )
            priority = get_priority(connection, "priority-1")

        self.assertEqual(update_result["status"], "updated")
        self.assertTrue(update_result["database_write"])
        self.assertEqual(transition_result["status"], "transitioned")
        self.assertTrue(transition_result["database_write"])
        self.assertEqual(priority["title"], "Updated Priority")
        self.assertEqual(priority["status"], "completed")
        self.assertFalse(update_result["external_mutation"])
        self.assertFalse(transition_result["sent"])

    def test_flow_malformed_inputs_are_rejected_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)

            invalid_creates = (
                {"priority_id": "", "title": "Priority"},
                {"priority_id": "priority-1", "title": "Priority", "status": "ranking"},
                {"priority_id": "priority-1", "title": "Priority", "metadata": []},
            )
            for item in invalid_creates:
                with self.subTest(item=item):
                    with self.assertRaises((TypeError, ValueError)):
                        create_priority_flow(connection, **item)

            create_priority(connection, priority_id="priority-1", title="Priority")
            with self.assertRaises(ValueError):
                update_priority_flow(connection, priority_id="priority-1")
            with self.assertRaises(ValueError):
                transition_priority_status_flow(
                    connection,
                    priority_id="priority-1",
                    status="ranking",
                )
            count = count_priorities(connection)

        self.assertEqual(count, 1)

    def test_priority_engine_helpers_do_not_create_repo_runtime_artifacts(self) -> None:
        runtime_dir_existed_before = RUNTIME_DIR.exists()

        with _migrated_test_connection() as connection:
            _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            create_priority_flow(
                connection,
                priority_id="priority-1",
                title="Priority",
                dry_run=False,
            )

        if not runtime_dir_existed_before:
            self.assertFalse(RUNTIME_DIR.exists())


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


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "4", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-14T10:00:00+00:00",
    )

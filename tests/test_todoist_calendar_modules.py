import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.calendar_blocks import (
    CALENDAR_MODULE_READ_PERMISSION,
    CALENDAR_MODULE_SIMULATED_WRITE_PERMISSION,
    CALENDAR_MODULE_WRITE_PERMISSION,
    CalendarModulePermissionDenied,
    FakeCalendarClient,
    create_calendar_block_record,
    preview_calendar_block,
    read_calendar_block,
    read_calendar_block_count,
    read_calendar_blocks,
    simulate_calendar_block_write,
    update_calendar_block_status_record,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.state import (
    build_calendar_block_record,
    build_todoist_task_record,
    count_calendar_blocks,
    count_todoist_tasks,
    get_calendar_block,
    get_todoist_task,
    list_calendar_blocks,
    list_todoist_tasks,
    upsert_permission_setting,
)
from personalos.todoist import (
    TODOIST_MODULE_READ_PERMISSION,
    TODOIST_MODULE_SIMULATED_WRITE_PERMISSION,
    TODOIST_MODULE_WRITE_PERMISSION,
    FakeTodoistClient,
    TodoistModulePermissionDenied,
    create_todoist_task_record,
    preview_todoist_task,
    read_todoist_task,
    read_todoist_task_count,
    read_todoist_tasks,
    simulate_todoist_task_write,
    update_todoist_task_status_record,
)


class TodoistCalendarValidationTest(unittest.TestCase):
    def test_todoist_validation_happy_path_generates_deterministic_record(self) -> None:
        task = build_todoist_task_record(**_todoist_input())

        self.assertEqual(task["task_title"], "Read market notes")
        self.assertEqual(task["labels"], ["review", "routine"])
        self.assertEqual(task["priority"], 2)
        self.assertEqual(task["risk_level"], "low")
        self.assertEqual(task["approval_mode"], "auto_allowed")
        self.assertEqual(task["status"], "proposed")
        self.assertTrue(task["dedupe_key"].startswith("todoist:task:"))
        self.assertTrue(task["todoist_task_id"].startswith("todoist-task-"))

    def test_todoist_validation_rejects_malformed_inputs_without_write(self) -> None:
        invalid_inputs = (
            {"task_title": ""},
            {"source_type": " "},
            {"source_id": ""},
            {"project": ""},
            {"labels": "review"},
            {"labels": ["review", 1]},
            {"priority": 0},
            {"priority": 5},
            {"risk_level": "urgent"},
            {"approval_mode": "live_write"},
            {"status": "live_created"},
            {"dedupe_key": " "},
        )

        with _migrated_test_connection() as connection:
            for item in invalid_inputs:
                with self.subTest(item=item):
                    task_input = _todoist_input()
                    task_input.update(item)
                    with self.assertRaises(ValueError):
                        build_todoist_task_record(**task_input)

            self.assertEqual(count_todoist_tasks(connection), 0)

    def test_calendar_validation_happy_path_generates_deterministic_record(self) -> None:
        block = build_calendar_block_record(**_calendar_input())

        self.assertEqual(block["title"], "Deep work")
        self.assertEqual(block["duration_minutes"], 60)
        self.assertEqual(block["calendar_id"], "primary")
        self.assertEqual(block["timezone"], DEFAULT_TIMEZONE)
        self.assertEqual(block["approval_mode"], "auto_allowed")
        self.assertEqual(block["status"], "proposed")
        self.assertTrue(block["dedupe_key"].startswith("calendar:block:"))
        self.assertTrue(block["calendar_block_id"].startswith("calendar-block-"))

    def test_calendar_validation_rejects_malformed_inputs_without_write(self) -> None:
        invalid_inputs = (
            {"title": ""},
            {"source_type": ""},
            {"source_id": ""},
            {"start_time": "not-a-time"},
            {"start_time": "2026-06-15T10:00:00"},
            {"end_time": "not-a-time"},
            {"duration_minutes": 0},
            {"calendar_id": ""},
            {"timezone": ""},
            {"risk_level": "urgent"},
            {"approval_mode": "live_write"},
            {"status": "live_created"},
            {"dedupe_key": ""},
        )

        with _migrated_test_connection() as connection:
            for item in invalid_inputs:
                with self.subTest(item=item):
                    block_input = _calendar_input()
                    block_input.update(item)
                    with self.assertRaises(ValueError):
                        build_calendar_block_record(**block_input)

            self.assertEqual(count_calendar_blocks(connection), 0)

    def test_calendar_start_end_and_duration_must_be_consistent(self) -> None:
        invalid_windows = (
            {
                "start_time": "2026-06-15T10:00:00+00:00",
                "end_time": "2026-06-15T10:00:00+00:00",
                "duration_minutes": 60,
            },
            {
                "start_time": "2026-06-15T10:00:00+00:00",
                "end_time": "2026-06-15T09:00:00+00:00",
                "duration_minutes": 60,
            },
            {
                "start_time": "2026-06-15T10:00:00+00:00",
                "end_time": "2026-06-15T11:00:00+00:00",
                "duration_minutes": 45,
            },
        )

        for item in invalid_windows:
            with self.subTest(item=item):
                block_input = _calendar_input()
                block_input.update(item)
                with self.assertRaises(ValueError):
                    build_calendar_block_record(**block_input)

    def test_risk_level_allowed_values_are_enforced(self) -> None:
        for risk_level in ("low", "medium", "high"):
            with self.subTest(risk_level=risk_level):
                task = build_todoist_task_record(
                    **_todoist_input(risk_level=risk_level, approval_mode=None)
                )
                self.assertEqual(task["risk_level"], risk_level)

        with self.assertRaises(ValueError):
            build_todoist_task_record(**_todoist_input(risk_level="critical"))

    def test_approval_mode_allowed_values_and_defaults_are_enforced(self) -> None:
        medium_task = build_todoist_task_record(
            **_todoist_input(risk_level="medium", approval_mode=None, status=None)
        )
        high_block = build_calendar_block_record(
            **_calendar_input(risk_level="high", approval_mode="manual_only")
        )

        self.assertEqual(medium_task["approval_mode"], "approval_required")
        self.assertEqual(medium_task["status"], "needs_approval")
        self.assertEqual(high_block["approval_mode"], "manual_only")

        with self.assertRaises(ValueError):
            build_calendar_block_record(**_calendar_input(approval_mode="live_write"))

    def test_high_risk_auto_allowed_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_todoist_task_record(
                **_todoist_input(risk_level="high", approval_mode="auto_allowed")
            )

    def test_medium_risk_auto_allowed_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_calendar_block_record(
                **_calendar_input(risk_level="medium", approval_mode="auto_allowed")
            )

    def test_dedupe_key_generation_is_deterministic_and_normalized(self) -> None:
        first = build_todoist_task_record(**_todoist_input(task_title="  Read Market Notes "))
        second = build_todoist_task_record(**_todoist_input(task_title="read market notes"))
        explicit = build_todoist_task_record(
            **_todoist_input(dedupe_key="  Custom Dedupe Key  ")
        )
        first_block = build_calendar_block_record(**_calendar_input(title="  Deep Work "))
        second_block = build_calendar_block_record(**_calendar_input(title="deep work"))

        self.assertEqual(first["dedupe_key"], second["dedupe_key"])
        self.assertEqual(first["todoist_task_id"], second["todoist_task_id"])
        self.assertEqual(explicit["dedupe_key"], "custom dedupe key")
        self.assertEqual(first_block["dedupe_key"], second_block["dedupe_key"])
        self.assertEqual(first_block["calendar_block_id"], second_block["calendar_block_id"])


class TodoistCalendarFlowTest(unittest.TestCase):
    def test_duplicate_dedupe_creates_return_existing_without_duplicate_row(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            first = create_todoist_task_record(connection, **_todoist_input())
            second = create_todoist_task_record(connection, **_todoist_input(task_title="read market notes"))
            count = count_todoist_tasks(connection)

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "already_exists")
        self.assertEqual(second["task"], first["task"])
        self.assertEqual(count, 1)

    def test_todoist_preview_does_not_mutate_database_or_call_adapters(self) -> None:
        with _migrated_test_connection() as connection:
            preview = preview_todoist_task(**_todoist_input())
            count = count_todoist_tasks(connection)

        self.assertEqual(preview["status"], "would_create")
        self.assertFalse(preview["database_write"])
        self.assertFalse(preview["adapter_called"])
        self.assertEqual(count, 0)

    def test_calendar_preview_does_not_mutate_database_or_call_adapters(self) -> None:
        with _migrated_test_connection() as connection:
            preview = preview_calendar_block(**_calendar_input())
            count = count_calendar_blocks(connection)

        self.assertEqual(preview["status"], "would_create")
        self.assertFalse(preview["database_write"])
        self.assertFalse(preview["adapter_called"])
        self.assertEqual(count, 0)

    def test_todoist_dev_test_write_requires_permission(self) -> None:
        with _migrated_test_connection() as connection:
            result = create_todoist_task_record(connection, **_todoist_input())
            count = count_todoist_tasks(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing Todoist module permission", result["reason"])
        self.assertEqual(count, 0)

    def test_calendar_dev_test_write_requires_permission(self) -> None:
        with _migrated_test_connection() as connection:
            result = create_calendar_block_record(connection, **_calendar_input())
            count = count_calendar_blocks(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing Calendar module permission", result["reason"])
        self.assertEqual(count, 0)

    def test_permission_defaults_fail_closed_for_reads_and_simulated_writes(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(TodoistModulePermissionDenied):
                read_todoist_tasks(connection)
            with self.assertRaises(CalendarModulePermissionDenied):
                read_calendar_blocks(connection)

            todoist_sim = simulate_todoist_task_write(
                connection,
                todoist_task_id="missing-task",
            )
            calendar_sim = simulate_calendar_block_write(
                connection,
                calendar_block_id="missing-block",
            )

        self.assertEqual(todoist_sim["status"], "blocked")
        self.assertEqual(calendar_sim["status"], "blocked")

    def test_todoist_simulated_write_requires_simulated_write_permission(self) -> None:
        client = FakeTodoistClient()
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            created = create_todoist_task_record(connection, **_todoist_input())["task"]
            result = simulate_todoist_task_write(
                connection,
                todoist_task_id=created["todoist_task_id"],
                client=client,
            )
            task = get_todoist_task(connection, created["todoist_task_id"])

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing Todoist module permission", result["reason"])
        self.assertEqual(client.created_tasks, [])
        self.assertEqual(task["status"], "proposed")

    def test_calendar_simulated_write_requires_simulated_write_permission(self) -> None:
        client = FakeCalendarClient()
        with _migrated_test_connection() as connection:
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            created = create_calendar_block_record(connection, **_calendar_input())["block"]
            result = simulate_calendar_block_write(
                connection,
                calendar_block_id=created["calendar_block_id"],
                client=client,
            )
            block = get_calendar_block(connection, created["calendar_block_id"])

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing Calendar module permission", result["reason"])
        self.assertEqual(client.created_blocks, [])
        self.assertEqual(block["status"], "proposed")

    def test_fake_todoist_client_produces_deterministic_fake_result(self) -> None:
        client = FakeTodoistClient()
        task = build_todoist_task_record(**_todoist_input())

        first = client.create_task(task)
        second = client.create_task(task)

        self.assertEqual(first, second)
        self.assertTrue(first["external_task_id"].startswith("fake-todoist-task-"))
        self.assertFalse(first["network_called"])
        self.assertFalse(first["credentials_read"])
        self.assertEqual(len(client.created_tasks), 2)

    def test_fake_calendar_client_produces_deterministic_fake_result(self) -> None:
        client = FakeCalendarClient()
        block = build_calendar_block_record(**_calendar_input())

        first = client.create_calendar_block(block)
        second = client.create_calendar_block(block)

        self.assertEqual(first, second)
        self.assertTrue(first["external_event_id"].startswith("fake-calendar-event-"))
        self.assertFalse(first["network_called"])
        self.assertFalse(first["credentials_read"])
        self.assertEqual(len(client.created_blocks), 2)

    def test_todoist_simulated_write_uses_fake_client_and_updates_local_status(self) -> None:
        client = FakeTodoistClient()
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            _set_permission(connection, TODOIST_MODULE_SIMULATED_WRITE_PERMISSION)
            created = create_todoist_task_record(connection, **_todoist_input())["task"]
            result = simulate_todoist_task_write(
                connection,
                todoist_task_id=created["todoist_task_id"],
                client=client,
                updated_at_utc="2026-06-15T12:00:00+00:00",
            )
            updated = get_todoist_task(connection, created["todoist_task_id"])

        self.assertEqual(result["status"], "simulated_created")
        self.assertTrue(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(updated["status"], "simulated_created")
        self.assertEqual(updated["external_task_id"], result["client_result"]["external_task_id"])
        self.assertEqual(len(client.created_tasks), 1)

    def test_calendar_simulated_write_uses_fake_client_and_updates_local_status(self) -> None:
        client = FakeCalendarClient()
        with _migrated_test_connection() as connection:
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_SIMULATED_WRITE_PERMISSION)
            created = create_calendar_block_record(connection, **_calendar_input())["block"]
            result = simulate_calendar_block_write(
                connection,
                calendar_block_id=created["calendar_block_id"],
                client=client,
                updated_at_utc="2026-06-15T12:00:00+00:00",
            )
            updated = get_calendar_block(connection, created["calendar_block_id"])

        self.assertEqual(result["status"], "simulated_created")
        self.assertTrue(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(updated["status"], "simulated_created")
        self.assertEqual(updated["external_event_id"], result["client_result"]["external_event_id"])
        self.assertEqual(len(client.created_blocks), 1)

    def test_list_count_and_read_helpers_support_basic_filters(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            _set_permission(connection, TODOIST_MODULE_READ_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_READ_PERMISSION)

            task = create_todoist_task_record(connection, **_todoist_input())["task"]
            create_todoist_task_record(
                connection,
                **_todoist_input(
                    task_title="Project review",
                    source_id="priority-2",
                    project="Deep Work",
                    risk_level="medium",
                    approval_mode=None,
                ),
            )
            block = create_calendar_block_record(connection, **_calendar_input())["block"]

            read_task = read_todoist_task(
                connection,
                todoist_task_id=task["todoist_task_id"],
            )
            filtered_tasks = read_todoist_tasks(connection, project="Admin")
            task_count = read_todoist_task_count(connection, risk_level="medium")
            read_block = read_calendar_block(
                connection,
                calendar_block_id=block["calendar_block_id"],
            )
            filtered_blocks = read_calendar_blocks(
                connection,
                calendar_id="primary",
                time_min="2026-06-15T09:30:00+00:00",
                time_max="2026-06-15T11:30:00+00:00",
            )
            block_count = read_calendar_block_count(connection, calendar_id="primary")

        self.assertEqual(read_task, task)
        self.assertEqual([item["todoist_task_id"] for item in filtered_tasks], [task["todoist_task_id"]])
        self.assertEqual(task_count, 1)
        self.assertEqual(read_block, block)
        self.assertEqual([item["calendar_block_id"] for item in filtered_blocks], [block["calendar_block_id"]])
        self.assertEqual(block_count, 1)

    def test_status_update_helpers_require_permission_and_update_status(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            task = create_todoist_task_record(connection, **_todoist_input())["task"]
            block = create_calendar_block_record(connection, **_calendar_input())["block"]
            updated_task = update_todoist_task_status_record(
                connection,
                todoist_task_id=task["todoist_task_id"],
                status="cancelled",
                updated_at_utc="2026-06-15T13:00:00+00:00",
            )
            updated_block = update_calendar_block_status_record(
                connection,
                calendar_block_id=block["calendar_block_id"],
                status="cancelled",
                updated_at_utc="2026-06-15T13:00:00+00:00",
            )

        self.assertEqual(updated_task["status"], "cancelled")
        self.assertEqual(updated_block["status"], "cancelled")

        with _migrated_test_connection() as connection:
            with self.assertRaises(TodoistModulePermissionDenied):
                update_todoist_task_status_record(
                    connection,
                    todoist_task_id="missing",
                    status="cancelled",
                )

    def test_state_helpers_support_unpermissioned_internal_list_and_count(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, TODOIST_MODULE_WRITE_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            task = create_todoist_task_record(connection, **_todoist_input())["task"]
            block = create_calendar_block_record(connection, **_calendar_input())["block"]

            tasks = list_todoist_tasks(connection, source_type="priority")
            blocks = list_calendar_blocks(connection, source_type="priority")
            task_count = count_todoist_tasks(connection)
            block_count = count_calendar_blocks(connection)

        self.assertEqual(task_count, 1)
        self.assertEqual(block_count, 1)
        self.assertEqual(tasks, [task])
        self.assertEqual(blocks, [block])

    def test_calendar_block_filters_parse_mixed_timezone_offsets(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            early_block = create_calendar_block_record(
                connection,
                **_calendar_input(
                    title="Offset early block",
                    source_id="calendar-offset-early",
                    start_time="2026-06-15T16:30:00+02:00",
                    end_time="2026-06-15T17:00:00+02:00",
                    duration_minutes=30,
                ),
            )["block"]
            later_block = create_calendar_block_record(
                connection,
                **_calendar_input(
                    title="Offset later block",
                    source_id="calendar-offset-later",
                    start_time="2026-06-15T09:50:00-05:00",
                    end_time="2026-06-15T10:20:00-05:00",
                    duration_minutes=30,
                ),
            )["block"]
            create_calendar_block_record(
                connection,
                **_calendar_input(
                    title="Outside block",
                    source_id="calendar-offset-outside",
                    start_time="2026-06-15T16:30:00-05:00",
                    end_time="2026-06-15T17:00:00-05:00",
                    duration_minutes=30,
                ),
            )

            filtered_blocks = list_calendar_blocks(
                connection,
                time_min="2026-06-15T09:45:00-05:00",
                time_max="2026-06-15T10:15:00-05:00",
            )
            filtered_count = count_calendar_blocks(
                connection,
                time_min="2026-06-15T09:45:00-05:00",
                time_max="2026-06-15T10:15:00-05:00",
            )

        self.assertEqual(
            [item["calendar_block_id"] for item in filtered_blocks],
            [early_block["calendar_block_id"], later_block["calendar_block_id"]],
        )
        self.assertEqual(filtered_count, 2)

    def test_manual_only_objects_are_not_routed_to_fake_clients(self) -> None:
        client = FakeCalendarClient()
        with _migrated_test_connection() as connection:
            _set_permission(connection, CALENDAR_MODULE_WRITE_PERMISSION)
            _set_permission(connection, CALENDAR_MODULE_SIMULATED_WRITE_PERMISSION)
            block = create_calendar_block_record(
                connection,
                **_calendar_input(
                    risk_level="high",
                    approval_mode="manual_only",
                    status="proposed",
                ),
            )["block"]
            result = simulate_calendar_block_write(
                connection,
                calendar_block_id=block["calendar_block_id"],
                client=client,
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("manual_only", result["reason"])
        self.assertEqual(client.created_blocks, [])


class TodoistCalendarArtifactSafetyTest(unittest.TestCase):
    def test_repo_has_no_runtime_database_or_var_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        sqlite_artifacts = [
            path
            for path in repo_root.rglob("*")
            if ".git" not in path.parts
            and path.is_file()
            and path.suffix in {".sqlite", ".sqlite3", ".db"}
        ]
        var_dirs = [
            path
            for path in repo_root.rglob("var")
            if ".git" not in path.parts and path.is_dir()
        ]

        self.assertEqual(sqlite_artifacts, [])
        self.assertEqual(var_dirs, [])


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
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "5", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _todoist_input(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "task_title": "Read market notes",
        "description": "Review the weekly notes without external sends.",
        "source_type": "priority",
        "source_id": "priority-1",
        "project": "Admin",
        "labels": ["review", "routine"],
        "due_date_or_due_string": "2026-06-15",
        "priority": 2,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
        "created_at_utc": "2026-06-15T10:00:00+00:00",
        "updated_at_utc": "2026-06-15T10:00:00+00:00",
    }
    item.update(overrides)
    return item


def _calendar_input(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "title": "Deep work",
        "description": "Self-only priority work block.",
        "source_type": "priority",
        "source_id": "priority-1",
        "start_time": "2026-06-15T10:00:00+00:00",
        "end_time": "2026-06-15T11:00:00+00:00",
        "duration_minutes": 60,
        "calendar_id": "primary",
        "timezone": DEFAULT_TIMEZONE,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
        "created_at_utc": "2026-06-15T10:00:00+00:00",
        "updated_at_utc": "2026-06-15T10:00:00+00:00",
    }
    item.update(overrides)
    return item

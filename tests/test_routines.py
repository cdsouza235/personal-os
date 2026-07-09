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
from personalos.routines import (
    ROUTINE_ENGINE_READ_PERMISSION,
    ROUTINE_ENGINE_WRITE_PERMISSION,
    RoutineEnginePermissionDenied,
    complete_routine,
    create_routine_record,
    read_routine,
    read_routines,
    update_routine_record_status_enabled,
)
from personalos.state import (
    count_routine_completions,
    count_routines,
    create_routine,
    get_routine,
    list_routine_completions,
    list_routines,
    record_routine_completion,
    update_routine_status_enabled,
    upsert_permission_setting,
    validate_routine_cadence_type,
    validate_routine_missed_behavior,
)


class RoutineStateHelperTest(unittest.TestCase):
    def test_create_get_list_count_and_update_routine(self) -> None:
        with _migrated_test_connection() as connection:
            created = create_routine(
                connection,
                routine_id="routine-1",
                name="Morning Review",
                status="active",
                enabled=True,
                settings={"cadence": "manual_only"},
                notes="dev/test only",
                created_at_utc="2026-06-13T10:00:00+00:00",
                updated_at_utc="2026-06-13T10:00:00+00:00",
            )
            fetched = get_routine(connection, "routine-1")
            listed = list_routines(connection)
            updated = update_routine_status_enabled(
                connection,
                routine_id="routine-1",
                status="paused",
                enabled=False,
                updated_at_utc="2026-06-13T11:00:00+00:00",
            )

        self.assertEqual(created["routine_id"], "routine-1")
        self.assertEqual(created["settings"], {"cadence": "manual_only"})
        self.assertEqual(fetched, created)
        self.assertEqual([routine["routine_id"] for routine in listed], ["routine-1"])
        self.assertEqual(updated["status"], "paused")
        self.assertFalse(updated["enabled"])
        self.assertEqual(updated["updated_at_utc"], "2026-06-13T11:00:00+00:00")

    def test_routine_count_reflects_created_records(self) -> None:
        with _migrated_test_connection() as connection:
            self.assertEqual(count_routines(connection), 0)
            create_routine(
                connection,
                routine_id="routine-1",
                name="Morning Review",
            )

            count = count_routines(connection)

        self.assertEqual(count, 1)

    def test_invalid_routine_status_is_rejected_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ValueError):
                create_routine(
                    connection,
                    routine_id="routine-1",
                    name="Morning Review",
                    status="running",
                )

            self.assertEqual(count_routines(connection), 0)

    def test_invalid_enabled_flag_is_rejected_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ValueError):
                create_routine(
                    connection,
                    routine_id="routine-1",
                    name="Morning Review",
                    enabled=1,  # type: ignore[arg-type]
                )

            self.assertEqual(count_routines(connection), 0)

    def test_record_completion_validates_routine_and_returns_inert_row(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(
                connection,
                routine_id="routine-1",
                name="Morning Review",
            )
            completion = record_routine_completion(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                completion_id="completion-1",
                completed_at_utc="2026-06-13T12:00:00+00:00",
                source="tests",
                metadata={"note": "done"},
                created_at_utc="2026-06-13T12:00:00+00:00",
            )
            completions = list_routine_completions(connection, routine_id="routine-1")

        self.assertEqual(completion["completion_id"], "completion-1")
        self.assertEqual(completion["routine_id"], "routine-1")
        self.assertEqual(completion["completed_for_date"], "2026-06-13")
        self.assertEqual(completion["metadata"], {"note": "done"})
        self.assertEqual(completions, [completion])

    def test_completion_rejects_missing_disabled_and_inactive_routines(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(
                connection,
                routine_id="paused-routine",
                name="Paused Routine",
                status="paused",
            )
            create_routine(
                connection,
                routine_id="disabled-routine",
                name="Disabled Routine",
                enabled=False,
            )

            for routine_id in ("missing-routine", "paused-routine", "disabled-routine"):
                with self.subTest(routine_id=routine_id):
                    with self.assertRaises(ValueError):
                        record_routine_completion(
                            connection,
                            routine_id=routine_id,
                            completed_for_date="2026-06-13",
                        )

            count = count_routine_completions(connection)

        self.assertEqual(count, 0)


class RoutineCadenceSchemaTest(unittest.TestCase):
    def test_create_routine_with_cadence_fields_round_trips(self) -> None:
        with _migrated_test_connection() as connection:
            created = create_routine(
                connection,
                routine_id="routine-cadence-1",
                name="Reading",
                cadence_type="weekly_target_count",
                cadence_config={"target": 4},
                missed_behavior_default="carry_forward_within_week",
                rotation_group="reading-pool",
                weekly_target=4,
            )
            fetched = get_routine(connection, "routine-cadence-1")
            listed = list_routines(connection)

        for routine in (created, fetched, listed[0]):
            self.assertEqual(routine["cadence_type"], "weekly_target_count")
            self.assertEqual(routine["cadence_config"], {"target": 4})
            self.assertEqual(routine["missed_behavior_default"], "carry_forward_within_week")
            self.assertEqual(routine["rotation_group"], "reading-pool")
            self.assertEqual(routine["weekly_target"], 4)
            self.assertIsInstance(routine["weekly_target"], int)

    def test_create_routine_without_cadence_fields_defaults_to_none_and_empty(self) -> None:
        with _migrated_test_connection() as connection:
            created = create_routine(
                connection,
                routine_id="routine-1",
                name="Morning Review",
            )
            fetched = get_routine(connection, "routine-1")

        for routine in (created, fetched):
            self.assertIsNone(routine["cadence_type"])
            self.assertEqual(routine["cadence_config"], {})
            self.assertIsNone(routine["missed_behavior_default"])
            self.assertIsNone(routine["rotation_group"])
            self.assertIsNone(routine["weekly_target"])
            self.assertEqual(routine["settings"], {})
            self.assertEqual(routine["notes"], "")

    def test_validate_routine_cadence_type_rejects_invalid_and_allows_none(self) -> None:
        self.assertIsNone(validate_routine_cadence_type(None))
        self.assertEqual(validate_routine_cadence_type("daily"), "daily")
        with self.assertRaises(ValueError):
            validate_routine_cadence_type("not_a_real_type")

    def test_validate_routine_missed_behavior_rejects_invalid_and_allows_none(self) -> None:
        self.assertIsNone(validate_routine_missed_behavior(None))
        self.assertEqual(
            validate_routine_missed_behavior("skip_and_continue"), "skip_and_continue"
        )
        with self.assertRaises(ValueError):
            validate_routine_missed_behavior("not_a_real_behavior")

    def test_legacy_row_cadence_backfills_from_settings_json_cadence_key(self) -> None:
        with _connection_with_legacy_routines(
            [
                {
                    "routine_id": "legacy-with-cadence",
                    "name": "Legacy With Cadence",
                    "settings_json": '{"cadence": "manual_only"}',
                },
            ]
        ) as connection:
            fetched = get_routine(connection, "legacy-with-cadence")

        self.assertEqual(fetched["cadence_type"], "manual_only")
        self.assertEqual(fetched["cadence_config"], {})

    def test_legacy_row_without_cadence_key_backfills_to_manual_only(self) -> None:
        with _connection_with_legacy_routines(
            [
                {
                    "routine_id": "legacy-no-cadence",
                    "name": "Legacy No Cadence",
                    "settings_json": "{}",
                },
            ]
        ) as connection:
            fetched = get_routine(connection, "legacy-no-cadence")

        self.assertEqual(fetched["cadence_type"], "manual_only")
        self.assertEqual(fetched["cadence_config"], {})


class RoutineEnginePermissionTest(unittest.TestCase):
    def test_missing_read_permission_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(RoutineEnginePermissionDenied):
                read_routines(connection)

    def test_disabled_read_permission_denies_reads(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, ROUTINE_ENGINE_READ_PERMISSION, PermissionMode.DISABLED)

            with self.assertRaises(RoutineEnginePermissionDenied):
                read_routines(connection)

    def test_enabled_read_permission_allows_reads(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_READ_PERMISSION, PermissionMode.AUTO_WRITE)

            routine = read_routine(connection, routine_id="routine-1")
            routines = read_routines(connection)

        self.assertEqual(routine["routine_id"], "routine-1")
        self.assertEqual([item["routine_id"] for item in routines], ["routine-1"])

    def test_missing_write_permission_fails_closed_for_create(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(RoutineEnginePermissionDenied):
                create_routine_record(
                    connection,
                    routine_id="routine-1",
                    name="Morning Review",
                )

            self.assertEqual(count_routines(connection), 0)

    def test_disabled_write_permission_denies_create(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.DISABLED)

            with self.assertRaises(RoutineEnginePermissionDenied):
                create_routine_record(
                    connection,
                    routine_id="routine-1",
                    name="Morning Review",
                )

            self.assertEqual(count_routines(connection), 0)

    def test_approval_required_write_permission_denies_without_prompting(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(
                connection,
                ROUTINE_ENGINE_WRITE_PERMISSION,
                PermissionMode.APPROVAL_REQUIRED,
            )

            with self.assertRaises(RoutineEnginePermissionDenied):
                create_routine_record(
                    connection,
                    routine_id="routine-1",
                    name="Morning Review",
                )

            self.assertEqual(count_routines(connection), 0)

    def test_enabled_write_permission_allows_create_and_update(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            created = create_routine_record(
                connection,
                routine_id="routine-1",
                name="Morning Review",
            )
            updated = update_routine_record_status_enabled(
                connection,
                routine_id="routine-1",
                status="archived",
                enabled=False,
            )

        self.assertEqual(created["status"], "active")
        self.assertEqual(updated["status"], "archived")
        self.assertFalse(updated["enabled"])


class RoutineCompletionFlowTest(unittest.TestCase):
    def test_missing_write_permission_blocks_completion_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")

            result = complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                dry_run=True,
            )

            count = count_routine_completions(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing routine engine permission", result["reason"])
        self.assertFalse(result["database_write"])
        self.assertEqual(count, 0)

    def test_disabled_write_permission_blocks_completion_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.DISABLED)

            result = complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                dry_run=False,
            )

            count = count_routine_completions(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("disabled", result["reason"])
        self.assertFalse(result["database_write"])
        self.assertEqual(count, 0)

    def test_dry_run_completion_validates_without_writing_row(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)

            result = complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                dry_run=True,
                metadata={"source": "unit-test"},
                completed_at_utc="2026-06-13T12:00:00+00:00",
            )
            count = count_routine_completions(connection)

        self.assertEqual(result["status"], "would_complete")
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["no_send"])
        self.assertFalse(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(result["would_write"]["metadata"], {"source": "unit-test"})
        self.assertEqual(count, 0)

    def test_non_dry_run_completion_writes_only_dev_test_sqlite_row(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)

            result = complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                dry_run=False,
                metadata={"source": "unit-test"},
                completed_at_utc="2026-06-13T12:00:00+00:00",
            )
            count = count_routine_completions(connection, routine_id="routine-1")
            completions = list_routine_completions(connection, routine_id="routine-1")

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["dry_run"])
        self.assertTrue(result["no_send"])
        self.assertTrue(result["database_write"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])
        self.assertEqual(count, 1)
        self.assertEqual(completions[0], result["completion"])

    def test_missing_disabled_and_inactive_routines_block_completion_flow(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            create_routine(
                connection,
                routine_id="paused-routine",
                name="Paused Routine",
                status="paused",
            )
            create_routine(
                connection,
                routine_id="disabled-routine",
                name="Disabled Routine",
                enabled=False,
            )

            results = {
                routine_id: complete_routine(
                    connection,
                    routine_id=routine_id,
                    completed_for_date="2026-06-13",
                    dry_run=False,
                )
                for routine_id in ("missing-routine", "paused-routine", "disabled-routine")
            }
            count = count_routine_completions(connection)

        self.assertEqual(count, 0)
        self.assertEqual(results["missing-routine"]["status"], "blocked")
        self.assertIn("does not exist", results["missing-routine"]["reason"])
        self.assertEqual(results["paused-routine"]["status"], "blocked")
        self.assertIn("not active", results["paused-routine"]["reason"])
        self.assertEqual(results["disabled-routine"]["status"], "blocked")
        self.assertIn("disabled", results["disabled-routine"]["reason"])

    def test_invalid_completion_input_is_rejected_without_write(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)

            invalid_inputs = (
                {"routine_id": "", "completed_for_date": "2026-06-13"},
                {"routine_id": "routine-1", "completed_for_date": "not-a-date"},
            )
            for item in invalid_inputs:
                with self.subTest(item=item):
                    with self.assertRaises(ValueError):
                        complete_routine(
                            connection,
                            routine_id=item["routine_id"],
                            completed_for_date=item["completed_for_date"],
                        )

            with self.assertRaises(ValueError):
                complete_routine(
                    connection,
                    routine_id="routine-1",
                    completed_for_date="2026-06-13",
                    metadata={"bad": float("nan")},
                )

            count = count_routine_completions(connection)

        self.assertEqual(count, 0)

    def test_routine_engine_does_not_call_external_services(self) -> None:
        class ExternalServiceProbe:
            called = False

            def send(self) -> None:
                self.called = True

        probe = ExternalServiceProbe()

        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)

            result = complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
                dry_run=False,
                metadata={"probe": "not-called"},
            )

        self.assertEqual(result["status"], "completed")
        self.assertFalse(probe.called)
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["sent"])

    def test_routine_engine_helpers_do_not_create_repo_runtime_artifacts(self) -> None:
        runtime_dir_existed_before = RUNTIME_DIR.exists()

        with _migrated_test_connection() as connection:
            create_routine(connection, routine_id="routine-1", name="Morning Review")
            _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION, PermissionMode.AUTO_WRITE)
            complete_routine(
                connection,
                routine_id="routine-1",
                completed_for_date="2026-06-13",
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


# Mirrors the routines table shape from migrations/0003_core_state_tables.sql, before
# migration 00015 adds the first-class cadence columns. Used to simulate pre-migration
# legacy rows and confirm the 00015 backfill runs against them as expected.
_PRE_CADENCE_ROUTINES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS routines (
    routine_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    settings_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (enabled IN (0, 1))
);
"""


@contextmanager
def _connection_with_legacy_routines(
    rows: list[dict[str, str]],
) -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        connection.executescript(_PRE_CADENCE_ROUTINES_TABLE_SQL)
        with connection:
            for row in rows:
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
                        row["routine_id"],
                        row["name"],
                        row.get("status", "active"),
                        row.get("enabled", 1),
                        row["settings_json"],
                        row.get("notes", ""),
                        row.get("created_at_utc", "2026-01-01T00:00:00+00:00"),
                        row.get("updated_at_utc", "2026-01-01T00:00:00+00:00"),
                    ),
                )
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
        metadata={"phase": "3", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-13T10:00:00+00:00",
    )

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.briefings import (
    BRIEFING_LOOP_READ_PERMISSION,
    BRIEFING_LOOP_RUN_PERMISSION,
    BRIEFING_LOOP_WRITE_PERMISSION,
)
from personalos.composer import (
    COMPOSER_MODULE_READ_PERMISSION,
    COMPOSER_MODULE_RUN_PERMISSION,
    COMPOSER_MODULE_WRITE_PERMISSION,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.runtime_bootstrap import (
    RUNTIME_BOOTSTRAP_RUN_PERMISSION,
    RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
    bootstrap_runtime_database,
)
from personalos.scheduler import (
    SAFE_NO_SEND_SEED_PROFILE,
    SchedulerValidationError,
    build_scheduler_job_definition,
    count_scheduler_jobs,
    count_scheduler_runs,
    preview_scheduler_jobs,
    run_scheduler_job_simulated,
    seed_dev_scheduler_jobs,
    summarize_scheduler,
)
from personalos.side_effects import count_external_write_attempts
from personalos.state import (
    count_briefing_outputs,
    count_composer_outputs,
    count_composer_packets,
    count_daily_plans,
    count_model_runs,
    upsert_permission_setting,
)


SOURCE_DATE = "2026-06-15"
RUN_AT = "2026-06-15T10:00:00+00:00"


class SchedulerValidationTest(unittest.TestCase):
    def test_valid_no_send_scheduler_job_definition_is_accepted(self) -> None:
        job = build_scheduler_job_definition(
            scheduler_job_id="scheduler-job-test",
            name="Today View simulation",
            job_type="today_view",
            cadence_type="daily",
            schedule_json={"time": "06:00"},
            timezone=DEFAULT_TIMEZONE,
            enabled=True,
            status="enabled_dev_test",
            created_at=RUN_AT,
        )

        self.assertEqual(job["job_type"], "today_view")
        self.assertTrue(job["enabled"])
        self.assertTrue(job["no_send_mode"])
        self.assertTrue(job["no_external_writes"])
        self.assertTrue(job["fake_model_only"])

    def test_invalid_and_prohibited_job_types_are_rejected(self) -> None:
        for job_type in (
            "unknown",
            "gmail_send",
            "gmail_draft",
            "todoist_write",
            "calendar_write",
            "personalos_markdown_write",
            "launch_agent_install",
            "crontab_install",
            "daemon_runtime",
            "production_runtime_activation",
            "live_model_api_call",
        ):
            with self.subTest(job_type=job_type):
                with self.assertRaises(SchedulerValidationError):
                    build_scheduler_job_definition(
                        name="Rejected scheduler job",
                        job_type=job_type,
                        cadence_type="manual",
                        schedule_json={},
                        timezone=DEFAULT_TIMEZONE,
                        created_at=RUN_AT,
                    )

    def test_schedule_timezone_date_and_window_validation_fail_closed(self) -> None:
        with self.assertRaises(SchedulerValidationError):
            build_scheduler_job_definition(
                name="Bad specific times",
                job_type="status_summary",
                cadence_type="specific_times",
                schedule_json={},
                timezone=DEFAULT_TIMEZONE,
                created_at=RUN_AT,
            )
        with self.assertRaises(SchedulerValidationError):
            build_scheduler_job_definition(
                name="Bad timezone",
                job_type="status_summary",
                cadence_type="manual",
                schedule_json={},
                timezone="Not/AZone",
                created_at=RUN_AT,
            )
        with _migrated_connection() as connection:
            with self.assertRaises(SchedulerValidationError):
                run_scheduler_job_simulated(
                    connection,
                    job_type="today_view",
                    timezone=DEFAULT_TIMEZONE,
                    run_at=RUN_AT,
                )
            with self.assertRaises(SchedulerValidationError):
                run_scheduler_job_simulated(
                    connection,
                    job_type="briefing_preview",
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    run_at=RUN_AT,
                )


class SchedulerSimulationTest(unittest.TestCase):
    def test_seed_dev_creates_only_safe_no_send_scheduler_jobs(self) -> None:
        with _migrated_connection() as connection:
            result = seed_dev_scheduler_jobs(
                connection,
                profile=SAFE_NO_SEND_SEED_PROFILE,
                timezone=DEFAULT_TIMEZONE,
                created_at=RUN_AT,
            )
            jobs = result["scheduler_jobs"]

        self.assertEqual(result["status"], "seeded")
        self.assertEqual(result["scheduler_job_count"], 5)
        for job in jobs:
            with self.subTest(job=job["scheduler_job_id"]):
                self.assertTrue(job["enabled"])
                self.assertEqual(job["status"], "enabled_dev_test")
                self.assertTrue(job["no_send_mode"])
                self.assertTrue(job["no_external_writes"])
                self.assertTrue(job["fake_model_only"])

    def test_scheduler_preview_is_read_only(self) -> None:
        with _migrated_connection() as connection:
            seed_dev_scheduler_jobs(
                connection,
                profile=SAFE_NO_SEND_SEED_PROFILE,
                timezone=DEFAULT_TIMEZONE,
                created_at=RUN_AT,
            )
            before = _table_counts(connection)
            result = preview_scheduler_jobs(
                connection,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
            )
            after = _table_counts(connection)

        self.assertEqual(before, after)
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["database_write"])
        self.assertTrue(result["no_send_mode"])
        self.assertTrue(result["no_external_writes"])
        self.assertFalse(result["scheduler_activation"])
        self.assertFalse(result["launch_agent_installed"])

    def test_status_summary_run_records_scheduler_run_only(self) -> None:
        with _migrated_connection() as connection:
            before = _table_counts(connection)
            result = run_scheduler_job_simulated(
                connection,
                job_type="status_summary",
                run_at=RUN_AT,
            )
            after = _table_counts(connection)

        changed = {
            table_name: after[table_name] - before.get(table_name, 0)
            for table_name in after
            if after[table_name] != before.get(table_name, 0)
        }
        report = result["completion_report"]
        self.assertEqual(changed, {"scheduler_runs": 1})
        self.assertEqual(result["status"], "completed")
        self.assertTrue(report["no_send_mode"])
        self.assertTrue(report["no_external_writes"])
        self.assertFalse(report["live_write"])
        self.assertFalse(report["external_mutation"])
        self.assertFalse(report["scheduler_activation"])
        self.assertFalse(report["launch_agent_installed"])
        self.assertTrue(report["foreground_synchronous"])
        self.assertFalse(report["daemonized"])
        self.assertFalse(report["background_process_started"])

    def test_briefing_preview_run_uses_fake_no_send_composer_only(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_permissions(connection)
                _enable_composer_permissions(connection)
                before = _briefing_counts(connection)
                before_attempts = count_external_write_attempts(connection)
                result = run_scheduler_job_simulated(
                    connection,
                    job_type="briefing_preview",
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    run_at=RUN_AT,
                )
                after = _briefing_counts(connection)
                after_attempts = count_external_write_attempts(connection)

        workflow_report = result["workflow_report"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(after["scheduler_runs"] - before["scheduler_runs"], 1)
        self.assertEqual(after["daily_plans"] - before["daily_plans"], 1)
        self.assertEqual(after["briefing_outputs"] - before["briefing_outputs"], 1)
        self.assertEqual(after["composer_packets"] - before["composer_packets"], 1)
        self.assertEqual(after["composer_outputs"] - before["composer_outputs"], 1)
        self.assertEqual(after["model_runs"] - before["model_runs"], 1)
        self.assertEqual(after_attempts, before_attempts)
        self.assertTrue(workflow_report["no_send_mode"])
        self.assertTrue(workflow_report["no_external_writes"])
        self.assertTrue(workflow_report["no_live_model_call"])
        self.assertTrue(workflow_report["fake_composer_adapter"])
        self.assertFalse(workflow_report["network_called"])
        self.assertFalse(result["completion_report"]["scheduler_activation"])
        self.assertFalse(result["completion_report"]["launch_agent_installed"])

    def test_scheduler_summary_is_read_only_and_surfaces_latest_run_status(self) -> None:
        with _migrated_connection() as connection:
            run_scheduler_job_simulated(
                connection,
                job_type="status_summary",
                run_at=RUN_AT,
            )
            before = _table_counts(connection)
            summary = summarize_scheduler(connection)
            after = _table_counts(connection)

        self.assertEqual(before, after)
        self.assertEqual(summary["scheduler_run_count"], 1)
        self.assertEqual(summary["latest_status"], "completed")
        self.assertTrue(summary["read_only"])
        self.assertFalse(summary["scheduler_activation"])
        self.assertFalse(summary["launch_agent_installed"])


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
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


@contextmanager
def _seeded_runtime_db() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        profile = {
            "profile_name": "phase-13c-preview",
            "runtime_mode": "local_runtime_preview",
            "db_path_label": "temp-runtime-preview",
            "db_path": str(temp_path / "runtime" / "preview" / "personalos.sqlite3"),
            "backup_enabled": True,
            "backup_dir": None,
            "no_external_writes": True,
            "no_send_mode": True,
            "seed_profile_name": "mvp_preview_safe_seed",
            "created_by": "tests",
        }
        with _migrated_auth_connection(temp_path / "auth-runtime") as permission_connection:
            _set_permission(permission_connection, RUNTIME_BOOTSTRAP_WRITE_PERMISSION)
            _set_permission(permission_connection, RUNTIME_BOOTSTRAP_RUN_PERMISSION)
            result = bootstrap_runtime_database(
                profile,
                permission_connection=permission_connection,
            )
        if result["status"] != "completed":
            raise AssertionError(f"runtime bootstrap failed in test setup: {result['status']}")
        yield Path(profile["db_path"])


@contextmanager
def _migrated_auth_connection(runtime_dir: Path) -> Iterator[sqlite3.Connection]:
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


@contextmanager
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _enable_briefing_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_WRITE_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_RUN_PERMISSION)


def _enable_composer_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"phase": "13c", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc=RUN_AT,
    )


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        table_name = row["name"]
        if table_name.startswith("sqlite_"):
            continue
        counts[table_name] = int(
            connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        )
    return counts


def _briefing_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "daily_plans": count_daily_plans(connection),
        "briefing_outputs": count_briefing_outputs(connection),
        "composer_packets": count_composer_packets(connection),
        "composer_outputs": count_composer_outputs(connection),
        "model_runs": count_model_runs(connection),
        "scheduler_jobs": count_scheduler_jobs(connection),
        "scheduler_runs": count_scheduler_runs(connection),
    }

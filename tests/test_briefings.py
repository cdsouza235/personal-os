import inspect
import os
import re
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
    BriefingLoopPermissionDenied,
    BriefingLoopValidationError,
    build_no_send_daily_plan,
    generate_no_send_briefing_preview,
    read_briefing_output_count,
    read_briefing_outputs,
    read_daily_plan_count,
    read_daily_plans,
    select_briefing_window,
)
from personalos.composer import (
    COMPOSER_MODULE_READ_PERMISSION,
    COMPOSER_MODULE_RUN_PERMISSION,
    COMPOSER_MODULE_WRITE_PERMISSION,
    FakeComposerAdapter,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.runtime_bootstrap import (
    RUNTIME_BOOTSTRAP_READ_PERMISSION,
    RUNTIME_BOOTSTRAP_RUN_PERMISSION,
    RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
    bootstrap_runtime_database,
)
from personalos.state import (
    count_briefing_outputs,
    count_calendar_blocks,
    count_composer_outputs,
    count_composer_packets,
    count_daily_plans,
    count_model_runs,
    count_todoist_tasks,
    create_daily_plan,
    list_briefing_outputs,
    upsert_permission_setting,
)
from personalos.today import create_today_view_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE = "2026-06-15"
RUN_AT = "2026-06-15T14:00:00+00:00"


class BriefingLoopMigrationTest(unittest.TestCase):
    def test_migration_0009_is_applied(self) -> None:
        with _migrated_test_connection() as connection:
            rows = connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()

        migration_names = {row["version"]: row["name"] for row in rows}
        self.assertEqual(migration_names["0009"], "briefing_loop_tables")

    def test_daily_plan_check_constraints_reject_invalid_status(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO daily_plans (
                        id,
                        source_date,
                        timezone,
                        plan_json,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "daily-plan-invalid",
                        SOURCE_DATE,
                        DEFAULT_TIMEZONE,
                        "{}",
                        "sent",
                        RUN_AT,
                        RUN_AT,
                    ),
                )

    def test_briefing_output_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("briefing_window_name", "overnight"),
            ("delivery_mode", "send_gmail"),
            ("status", "sent"),
        )

        with _migrated_test_connection() as connection:
            create_daily_plan(
                connection,
                daily_plan_id="daily-plan-check",
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
                plan_json={"no_external_writes": True},
                created_at=RUN_AT,
                updated_at=RUN_AT,
            )
            for index, (column_name, invalid_value) in enumerate(invalid_cases):
                with self.subTest(column_name=column_name):
                    values = {
                        "id": f"briefing-output-check-{index}",
                        "daily_plan_id": "daily-plan-check",
                        "briefing_window_id": None,
                        "briefing_window_name": "morning",
                        "source_date": SOURCE_DATE,
                        "timezone": DEFAULT_TIMEZONE,
                        "composer_packet_id": None,
                        "composer_output_id": None,
                        "readable_text": "Readable output.",
                        "output_json": "{}",
                        "manual_export_markdown": (
                            "# Manual export\n\n"
                            "- No-send preview\n"
                            "- No external writes performed"
                        ),
                        "completion_report_json": '{"no_external_writes":true}',
                        "delivery_mode": "no_send",
                        "status": "generated",
                        "created_at": RUN_AT,
                        "updated_at": RUN_AT,
                    }
                    values[column_name] = invalid_value

                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(
                            """
                            INSERT INTO briefing_outputs (
                                id,
                                daily_plan_id,
                                briefing_window_id,
                                briefing_window_name,
                                source_date,
                                timezone,
                                composer_packet_id,
                                composer_output_id,
                                readable_text,
                                output_json,
                                manual_export_markdown,
                                completion_report_json,
                                delivery_mode,
                                status,
                                created_at,
                                updated_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                values["id"],
                                values["daily_plan_id"],
                                values["briefing_window_id"],
                                values["briefing_window_name"],
                                values["source_date"],
                                values["timezone"],
                                values["composer_packet_id"],
                                values["composer_output_id"],
                                values["readable_text"],
                                values["output_json"],
                                values["manual_export_markdown"],
                                values["completion_report_json"],
                                values["delivery_mode"],
                                values["status"],
                                values["created_at"],
                                values["updated_at"],
                            ),
                        )


class BriefingLoopPlanAndWindowTest(unittest.TestCase):
    def test_no_send_daily_plan_generation_uses_runtime_state_summaries(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                plan = build_no_send_daily_plan(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    generated_at=RUN_AT,
                )

        self.assertEqual(plan["source_date"], SOURCE_DATE)
        self.assertEqual(plan["timezone"], DEFAULT_TIMEZONE)
        self.assertTrue(plan["no_external_writes"])
        self.assertTrue(plan["no_send_mode"])
        self.assertEqual(len(plan["active_or_draft_briefing_windows"]), 4)
        self.assertEqual(plan["routine_summary"]["total_count"], 2)
        self.assertEqual(plan["priority_summary"]["total_count"], 1)
        self.assertIn("today_view_summary", plan)

    def test_briefing_window_selection_accepts_seeded_windows(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
                selected = [
                    select_briefing_window(
                        connection,
                        source_date=SOURCE_DATE,
                        timezone=DEFAULT_TIMEZONE,
                        briefing_window_name=name,
                    )
                    for name in ("morning", "midday", "afternoon", "evening")
                ]

        self.assertEqual([window["name"] for window in selected], ["morning", "midday", "afternoon", "evening"])
        self.assertTrue(all(window["status"] == "draft" for window in selected))
        self.assertTrue(all(window["delivery_mode"] == "no_send" for window in selected))

    def test_missing_briefing_window_is_rejected(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
                with connection:
                    connection.execute("DELETE FROM briefing_windows WHERE name = ?", ("morning",))

                with self.assertRaises(BriefingLoopValidationError):
                    select_briefing_window(
                        connection,
                        source_date=SOURCE_DATE,
                        timezone=DEFAULT_TIMEZONE,
                        briefing_window_name="morning",
                    )


class BriefingLoopPermissionTest(unittest.TestCase):
    def test_permission_defaults_fail_closed_for_read_and_run(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                with self.assertRaises(BriefingLoopPermissionDenied):
                    read_daily_plan_count(connection)
                with self.assertRaises(BriefingLoopPermissionDenied):
                    read_briefing_output_count(connection)

                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    run_at=RUN_AT,
                )

                daily_plans = count_daily_plans(connection)
                briefing_outputs = count_briefing_outputs(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing briefing loop permission", result["reason"])
        self.assertEqual(daily_plans, 0)
        self.assertEqual(briefing_outputs, 0)

    def test_permission_gated_read_list_count_helpers(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    run_at=RUN_AT,
                )

                daily_plan_count = read_daily_plan_count(connection, source_date=SOURCE_DATE)
                briefing_output_count = read_briefing_output_count(
                    connection,
                    source_date=SOURCE_DATE,
                    briefing_window_name="morning",
                )
                daily_plans = read_daily_plans(connection, source_date=SOURCE_DATE)
                briefing_outputs = read_briefing_outputs(connection, source_date=SOURCE_DATE)

        self.assertEqual(result["status"], "generated")
        self.assertEqual(daily_plan_count, 1)
        self.assertEqual(briefing_output_count, 1)
        self.assertEqual(daily_plans[0]["source_date"], SOURCE_DATE)
        self.assertEqual(briefing_outputs[0]["briefing_window_name"], "morning")


class BriefingPreviewGenerationTest(unittest.TestCase):
    def test_no_send_briefing_preview_success_uses_fake_composer_only(self) -> None:
        adapter = FakeComposerAdapter()

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                todoist_count_before = count_todoist_tasks(connection)
                calendar_count_before = count_calendar_blocks(connection)

                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    adapter=adapter,
                    run_at=RUN_AT,
                )

                todoist_count_after = count_todoist_tasks(connection)
                calendar_count_after = count_calendar_blocks(connection)
                daily_plan_count = count_daily_plans(connection)
                outputs = list_briefing_outputs(connection, source_date=SOURCE_DATE)

        self.assertEqual(result["status"], "generated")
        self.assertEqual(adapter.calls, [{"packet_id": result["composer_packet_id"]}])
        self.assertEqual(daily_plan_count, 1)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["status"], "generated")
        self.assertEqual(outputs[0]["delivery_mode"], "no_send")
        self.assertEqual(outputs[0]["completion_report_json"]["status"], "generated")
        self.assertTrue(result["no_external_writes"])
        self.assertTrue(result["no_send_mode"])
        self.assertTrue(result["no_live_model_call"])
        self.assertTrue(result["no_todoist_writes"])
        self.assertTrue(result["no_calendar_writes"])
        self.assertTrue(result["no_gmail_send"])
        self.assertTrue(result["fake_composer_adapter"])
        self.assertFalse(result["network_called"])
        self.assertIn("No-send preview", result["manual_export_markdown"])
        self.assertIn("No external writes performed", result["manual_export_markdown"])
        self.assertEqual(todoist_count_before, todoist_count_after)
        self.assertEqual(calendar_count_before, calendar_count_after)

    def test_preview_persists_composer_and_briefing_records(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="midday",
                    run_at=RUN_AT,
                )

                daily_plan_count = count_daily_plans(connection)
                briefing_output_count = count_briefing_outputs(connection)
                packet_count = count_composer_packets(connection)
                composer_output_count = count_composer_outputs(connection)
                model_run_count = count_model_runs(connection)

        self.assertEqual(result["status"], "generated")
        self.assertEqual(daily_plan_count, 1)
        self.assertEqual(briefing_output_count, 1)
        self.assertEqual(packet_count, 1)
        self.assertEqual(composer_output_count, 1)
        self.assertEqual(model_run_count, 1)

    def test_completion_report_includes_all_no_send_flags(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="afternoon",
                    run_at=RUN_AT,
                )

        required_true_flags = (
            "no_external_writes",
            "no_send_mode",
            "no_live_model_call",
            "no_todoist_writes",
            "no_calendar_writes",
            "no_gmail_send",
            "no_gmail_draft",
        )
        for flag in required_true_flags:
            with self.subTest(flag=flag):
                self.assertIs(result[flag], True)
        self.assertEqual(result["delivery_mode"], "no_send")
        self.assertEqual(result["briefing_window_name"], "afternoon")
        self.assertIsNotNone(result["daily_plan_id"])
        self.assertIsNotNone(result["composer_packet_id"])
        self.assertIsNotNone(result["composer_output_id"])

    def test_fake_composer_failure_records_failed_briefing_output(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="evening",
                    adapter=FakeComposerAdapter(should_fail=True),
                    run_at=RUN_AT,
                )
                outputs = list_briefing_outputs(connection, source_date=SOURCE_DATE)
                composer_outputs = count_composer_outputs(connection)
                model_runs = count_model_runs(connection)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(outputs[0]["status"], "failed")
        self.assertEqual(outputs[0]["completion_report_json"]["status"], "failed")
        self.assertIn("No-send preview", outputs[0]["manual_export_markdown"])
        self.assertEqual(composer_outputs, 0)
        self.assertEqual(model_runs, 1)

    def test_today_view_remains_read_only_after_briefing_output_exists(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    run_at=RUN_AT,
                )
                before_counts = _table_counts(connection)

                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )
                after_counts = _table_counts(connection)

        self.assertEqual(before_counts, after_counts)
        self.assertEqual(summary["briefing_loop_summary"]["latest_briefing_output_count"], 1)
        self.assertEqual(summary["briefing_loop_summary"]["source_date_briefing_output_count"], 1)
        self.assertTrue(summary["briefing_loop_summary"]["no_send_mode"])

    def test_temp_runtime_smoke_generates_morning_no_send_preview(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_loop_permissions(connection)
                _enable_composer_permissions(connection)
                result = generate_no_send_briefing_preview(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name="morning",
                    run_at=RUN_AT,
                )

                daily_plan_count = count_daily_plans(connection)
                briefing_output_count = count_briefing_outputs(connection)

        self.assertEqual(result["status"], "generated")
        self.assertEqual(daily_plan_count, 1)
        self.assertEqual(briefing_output_count, 1)
        self.assertTrue(result["no_external_writes"])
        self.assertTrue(result["no_send_mode"])
        self.assertFalse(result["network_called"])

    def test_briefings_module_has_no_live_api_client_imports(self) -> None:
        from personalos import briefings

        source = inspect.getsource(briefings)
        forbidden_imports = (
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "openrouter",
            "googleapiclient",
            "todoist",
            "gmail",
            "tradingview",
            "notion",
            "healthkit",
            "oura",
            "whoop",
            "garmin",
            "fitbit",
        )
        for module_name in forbidden_imports:
            pattern = rf"^\s*(from|import)\s+{re.escape(module_name)}\b"
            with self.subTest(module_name=module_name):
                self.assertIsNone(re.search(pattern, source, re.MULTILINE))


class Phase10BDocsAndArtifactSafetyTest(unittest.TestCase):
    def test_docs_describe_phase_10b_no_send_briefing_boundary(self) -> None:
        docs_text = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "SAFETY_POLICY.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "CODEX_WORKFLOW.md").read_text(encoding="utf-8"),
            ]
        ).lower()

        required_phrases = (
            "phase 10b no-send daily briefing loop foundation",
            "manual export only",
            "no gmail sending",
            "no live model calls",
            "no scheduler or launchagents",
            "no todoist/calendar writes",
            "fake composer path only",
            "completion report",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_repo_artifact_safety_has_no_var_or_database_artifacts_outside_git(self) -> None:
        db_artifacts: list[Path] = []
        var_dirs: list[Path] = []
        for directory, directories, filenames in os.walk(REPO_ROOT):
            current = Path(directory)
            if ".git" in current.parts:
                directories[:] = []
                continue
            directories[:] = [item for item in directories if item != ".git"]
            for dirname in directories:
                if dirname == "var":
                    var_dirs.append(current / dirname)
            for filename in filenames:
                path = current / filename
                is_named_db_artifact = filename in {".sqlite", ".sqlite3"}
                is_db_suffix = path.suffix in {".sqlite", ".sqlite3", ".db"}
                if is_named_db_artifact or is_db_suffix:
                    db_artifacts.append(path)

        self.assertEqual(db_artifacts, [])
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


@contextmanager
def _seeded_runtime_db() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        profile = _profile(temp_path)
        with _authorized_connection(temp_path) as permission_connection:
            result = bootstrap_runtime_database(
                profile,
                permission_connection=permission_connection,
            )
        if result["status"] != "completed":
            raise AssertionError(f"runtime bootstrap failed in test setup: {result['status']}")
        yield Path(profile["db_path"])


@contextmanager
def _authorized_connection(temp_path: Path) -> Iterator[sqlite3.Connection]:
    with _migrated_connection(temp_path / "auth-runtime") as connection:
        _set_permission(connection, RUNTIME_BOOTSTRAP_READ_PERMISSION)
        _set_permission(connection, RUNTIME_BOOTSTRAP_WRITE_PERMISSION)
        _set_permission(connection, RUNTIME_BOOTSTRAP_RUN_PERMISSION)
        yield connection


@contextmanager
def _migrated_connection(runtime_dir: Path) -> Iterator[sqlite3.Connection]:
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


def _enable_briefing_loop_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_WRITE_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_RUN_PERMISSION)


def _enable_composer_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "10b", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _profile(temp_path: Path) -> dict[str, object]:
    return {
        "profile_name": "phase-10b-preview",
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

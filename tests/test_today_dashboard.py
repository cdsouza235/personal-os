import inspect
import os
import re
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos import dashboard
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
from personalos.state import create_calendar_block, create_todoist_task, upsert_permission_setting
from personalos.today import create_today_view_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE = "2026-06-15"


class TodayViewSummaryTest(unittest.TestCase):
    def test_today_view_summary_includes_core_sections_from_safe_seed(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)

                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

        self.assertEqual(summary["source_date"], SOURCE_DATE)
        self.assertEqual(summary["timezone"], DEFAULT_TIMEZONE)
        self.assertTrue(summary["no_external_writes"])
        self.assertEqual(summary["routine_summary"]["total_count"], 2)
        self.assertEqual(summary["routine_summary"]["disabled_count"], 2)
        self.assertEqual(summary["priority_summary"]["total_count"], 1)
        self.assertEqual(summary["followup_summary"]["total_count"], 1)
        self.assertEqual(summary["followup_summary"]["open_count"], 1)
        self.assertEqual(summary["todoist_candidate_summary"]["total_count"], 1)
        self.assertEqual(summary["calendar_block_summary"]["total_count"], 1)
        self.assertEqual(summary["calendar_block_summary"]["source_date_count"], 1)
        self.assertEqual(summary["briefing_window_summary"]["total_count"], 4)
        self.assertGreaterEqual(summary["permission_summary"]["total_count"], 1)
        self.assertIn("counts", summary["system_status_summary"])

    def test_today_view_summary_does_not_mutate_table_counts(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                before_counts = _table_counts(connection)

                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

                after_counts = _table_counts(connection)

        self.assertTrue(summary["no_external_writes"])
        self.assertEqual(before_counts, after_counts)

    def test_today_view_summary_rejects_invalid_inputs(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                with self.assertRaises(ValueError):
                    create_today_view_summary(
                        connection,
                        source_date="2026-99-99",
                        timezone=DEFAULT_TIMEZONE,
                    )
                with self.assertRaises(ValueError):
                    create_today_view_summary(
                        connection,
                        source_date=SOURCE_DATE,
                        timezone="Not/AZone",
                    )


class DashboardShellTest(unittest.TestCase):
    def test_dashboard_html_render_includes_required_sections_and_safety_banner(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                html = dashboard.render_today_view_html_from_connection(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

        self.assertIn("Personal OS Today View", html)
        self.assertIn("Read-only preview", html)
        self.assertIn("no_external_writes=true", html)
        self.assertIn("no live Todoist/Calendar/Gmail/model calls", html)
        self.assertIn("localhost-only by default", html)
        self.assertIn("Routines", html)
        self.assertIn("Priorities", html)
        self.assertIn("Follow-ups", html)
        self.assertIn("Todoist Candidates", html)
        self.assertIn("Calendar Blocks", html)
        self.assertIn("Briefing Windows", html)
        self.assertIn("Permissions", html)
        self.assertIn("System Status", html)
        self.assertIn("Warnings", html)

    def test_dashboard_html_render_from_db_path_uses_read_only_connection(self) -> None:
        with _seeded_runtime_db() as db_path:
            html = dashboard.render_today_view_html_from_db_path(
                db_path,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
            )

        self.assertIn("Personal OS Today View", html)
        self.assertIn("Read-only preview", html)

    def test_dashboard_server_defaults_to_localhost_and_rejects_public_bind(self) -> None:
        self.assertEqual(dashboard.DEFAULT_DASHBOARD_HOST, "localhost")
        self.assertEqual(dashboard.validate_dashboard_bind_host("localhost"), "localhost")
        self.assertEqual(dashboard.validate_dashboard_bind_host("127.0.0.1"), "127.0.0.1")
        with self.assertRaises(ValueError):
            dashboard.validate_dashboard_bind_host("0.0.0.0")
        with self.assertRaises(ValueError):
            dashboard.validate_dashboard_bind_host("192.168.1.25")

    def test_dashboard_db_path_validation_rejects_protected_and_production_paths(self) -> None:
        protected_personalos = Path.home() / "PersonalOS" / "runtime.sqlite3"
        protected_openclaw = Path.home() / ".openclaw" / "runtime.sqlite3"

        with self.assertRaises(ValueError):
            dashboard.validate_dashboard_db_path(protected_personalos, must_exist=False)
        with self.assertRaises(ValueError):
            dashboard.validate_dashboard_db_path(protected_openclaw, must_exist=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            production_path = Path(temp_dir) / "production" / "personalos.sqlite3"
            with self.assertRaises(ValueError):
                dashboard.validate_dashboard_db_path(production_path, must_exist=False)

    def test_dashboard_request_handler_can_be_created_without_starting_server(self) -> None:
        with _seeded_runtime_db() as db_path:
            handler = dashboard.make_dashboard_request_handler(
                db_path,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
            )

        self.assertTrue(issubclass(handler, dashboard.BaseHTTPRequestHandler))

    def test_dashboard_module_has_no_live_api_client_imports(self) -> None:
        source = inspect.getsource(dashboard)
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


class Phase10ADocsAndArtifactSafetyTest(unittest.TestCase):
    def test_docs_describe_phase_10a_dashboard_boundary(self) -> None:
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
            "phase 10a local dashboard today view foundation",
            "personal os today view",
            "read-only local dashboard shell",
            "localhost-only by default",
            "no public internet exposure",
            "no live todoist writes",
            "no task/calendar mutation from dashboard",
            "no scheduler",
            "no production runtime activation",
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
def _seeded_runtime_db() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        profile = _profile(temp_path)
        with _authorized_connection(temp_path) as permission_connection:
            result = bootstrap_runtime_database(
                profile,
                permission_connection=permission_connection,
            )
        self_check_status = result["status"]
        if self_check_status != "completed":
            raise AssertionError(f"runtime bootstrap failed in test setup: {self_check_status}")
        yield Path(profile["db_path"])


def _insert_dashboard_fixture_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-06-15T10:00:00+00:00"
    create_todoist_task(
        connection,
        task_title="Review local Today View",
        description="Local preview task only.",
        source_type="tests",
        source_id="phase-10a",
        project="Personal OS",
        labels=["preview"],
        due_date_or_due_string=SOURCE_DATE,
        priority=2,
        risk_level="low",
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
    )
    create_calendar_block(
        connection,
        title="Local Today View review",
        description="Local preview block only.",
        source_type="tests",
        source_id="phase-10a",
        start_time="2026-06-15T09:00:00-05:00",
        end_time="2026-06-15T09:30:00-05:00",
        duration_minutes=30,
        calendar_id="local-preview",
        timezone=DEFAULT_TIMEZONE,
        risk_level="low",
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
    )
    with connection:
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
                "followup-phase-10a",
                "Check dashboard shell",
                "open",
                "tests",
                "{}",
                "Local test row.",
                timestamp,
                timestamp,
            ),
        )


def _profile(temp_path: Path) -> dict[str, object]:
    return {
        "profile_name": "phase-10a-preview",
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
    try:
        yield connection
    finally:
        connection.close()


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"source": "tests"},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
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

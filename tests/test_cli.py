import io
import inspect
import json
import os
import re
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

from personalos import cli
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
from personalos.state import (
    count_briefing_outputs,
    count_composer_outputs,
    count_composer_packets,
    count_daily_plans,
    count_model_runs,
    count_synthesis_import_previews,
    upsert_permission_setting,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE = "2026-06-15"


class OperatorCliArgumentAndPathSafetyTest(unittest.TestCase):
    def test_cli_help_renders(self) -> None:
        result = _run_cli(["--help"])

        self.assertEqual(result.code, 0)
        self.assertIn("Safe local operator CLI", result.stdout)
        self.assertIn("status", result.stdout)
        self.assertIn("briefing", result.stdout)
        self.assertIn("synthesis", result.stdout)
        self.assertIn("dashboard", result.stdout)

    def test_db_backed_commands_require_explicit_db(self) -> None:
        for args in (
            ["status"],
            ["today", "--date", SOURCE_DATE],
            ["briefing", "preview", "--date", SOURCE_DATE, "--window", "morning"],
            [
                "synthesis",
                "preview",
                "--input-file",
                "/tmp/input.json",
                "--source-type",
                "chatgpt_synthesis",
            ],
        ):
            with self.subTest(args=args):
                result = _run_cli(args)
                self.assertEqual(result.code, 2)
                self.assertIn("--db", result.stderr)

    def test_cli_rejects_protected_and_production_db_paths(self) -> None:
        protected = Path.home() / "PersonalOS" / "runtime.sqlite3"
        openclaw = Path.home() / ".openclaw" / "runtime.sqlite3"
        with tempfile.TemporaryDirectory() as temp_dir:
            production = Path(temp_dir) / "production" / "personalos.sqlite3"

            for db_path in (protected, openclaw, production):
                with self.subTest(db_path=db_path):
                    result = _run_cli(["status", "--db", str(db_path)])
                    self.assertEqual(result.code, 1)
                    self.assertIn("error:", result.stderr)

    def test_file_output_commands_require_output_file(self) -> None:
        with _seeded_runtime_db() as db_path:
            briefing_result = _run_cli(
                [
                    "briefing",
                    "export",
                    "--db",
                    str(db_path),
                    "--briefing-output-id",
                    "missing",
                ]
            )
            dashboard_result = _run_cli(
                [
                    "dashboard",
                    "render",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                ]
            )

        self.assertEqual(briefing_result.code, 2)
        self.assertIn("--output-file", briefing_result.stderr)
        self.assertEqual(dashboard_result.code, 2)
        self.assertIn("--output-file", dashboard_result.stderr)

    def test_output_file_path_safety_rejects_protected_sensitive_and_repo_var_paths(self) -> None:
        protected_personalos = Path.home() / "PersonalOS" / "cli-output.html"
        protected_openclaw = Path.home() / ".openclaw" / "cli-output.html"
        credential_path = Path(tempfile.gettempdir()) / "oauth-token-output.html"
        repo_var_path = REPO_ROOT / "var" / "cli-output.html"

        with _seeded_runtime_db() as db_path:
            for output_path in (
                protected_personalos,
                protected_openclaw,
                credential_path,
                repo_var_path,
            ):
                with self.subTest(output_path=output_path):
                    result = _run_cli(
                        [
                            "dashboard",
                            "render",
                            "--db",
                            str(db_path),
                            "--date",
                            SOURCE_DATE,
                            "--output-file",
                            str(output_path),
                        ]
                    )
                    self.assertEqual(result.code, 1)
                    self.assertIn("error:", result.stderr)

    def test_briefing_preview_cli_rejects_adapter_injection_surface(self) -> None:
        with _seeded_runtime_db() as db_path:
            result = _run_cli(
                [
                    "briefing",
                    "preview",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--window",
                    "morning",
                    "--adapter",
                    "live-model",
                ]
            )

        self.assertEqual(result.code, 2)
        self.assertIn("unrecognized arguments", result.stderr)


class OperatorCliReadAndPreviewWorkflowTest(unittest.TestCase):
    def test_status_command_works_against_temp_bootstrapped_db(self) -> None:
        with _seeded_runtime_db() as db_path:
            result = _run_cli(["status", "--db", str(db_path), "--json"])

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "completed")
        self.assertFalse(payload["database_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertIn("routines", payload["summary"]["counts"])

    def test_today_command_is_read_only_and_does_not_mutate_table_counts(self) -> None:
        with _seeded_runtime_db() as db_path:
            before = _table_counts(db_path)
            result = _run_cli(
                [
                    "today",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--json",
                ]
            )
            after = _table_counts(db_path)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(before, after)
        self.assertEqual(payload["summary"]["source_date"], SOURCE_DATE)
        self.assertTrue(payload["summary"]["no_external_writes"])
        self.assertFalse(payload["database_write"])

    def test_briefing_preview_creates_only_no_send_fake_preview_records(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_permissions(connection)
                _enable_composer_permissions(connection)
                before = _briefing_counts(connection)

            result = _run_cli(
                [
                    "briefing",
                    "preview",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--window",
                    "morning",
                    "--json",
                ]
            )

            with _sqlite_connection(db_path) as connection:
                after = _briefing_counts(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "generated")
        self.assertEqual(after["daily_plans"] - before["daily_plans"], 1)
        self.assertEqual(after["briefing_outputs"] - before["briefing_outputs"], 1)
        self.assertEqual(after["composer_packets"] - before["composer_packets"], 1)
        self.assertEqual(after["composer_outputs"] - before["composer_outputs"], 1)
        self.assertEqual(after["model_runs"] - before["model_runs"], 1)
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_send_mode"])
        self.assertTrue(payload["no_live_model_call"])
        self.assertTrue(payload["no_todoist_writes"])
        self.assertTrue(payload["no_calendar_writes"])
        self.assertTrue(payload["no_gmail_send"])
        self.assertTrue(payload["fake_composer_adapter"])
        self.assertFalse(payload["network_called"])

    def test_synthesis_preview_persists_exactly_one_valid_preview_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "synthesis.json"
            input_path.write_text(json.dumps(_synthesis_payload()), encoding="utf-8")
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)
                    before = count_synthesis_import_previews(connection)

                result = _run_cli(
                    [
                        "synthesis",
                        "preview",
                        "--db",
                        str(db_path),
                        "--input-file",
                        str(input_path),
                        "--source-type",
                        "chatgpt_synthesis",
                        "--json",
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = count_synthesis_import_previews(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(after - before, 1)
        self.assertEqual(payload["status"], "created")
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_state_mutation"])
        self.assertTrue(payload["no_personalos_writes"])
        self.assertTrue(payload["no_todoist_writes"])
        self.assertTrue(payload["no_calendar_writes"])
        self.assertTrue(payload["no_gmail_send"])
        self.assertTrue(payload["no_live_model_call"])

    def test_synthesis_preview_rejects_raw_prose_and_persists_no_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "notes.txt"
            input_path.write_text("Please turn these raw notes into tasks.", encoding="utf-8")
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)
                    before = count_synthesis_import_previews(connection)

                result = _run_cli(
                    [
                        "synthesis",
                        "preview",
                        "--db",
                        str(db_path),
                        "--input-file",
                        str(input_path),
                        "--source-type",
                        "chatgpt_synthesis",
                        "--json",
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = count_synthesis_import_previews(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 1)
        self.assertEqual(after, before)
        self.assertEqual(payload["status"], "rejected")
        self.assertFalse(payload["database_write"])
        self.assertTrue(payload["no_external_writes"])

    def test_synthesis_preview_rejects_credential_input_and_persists_no_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "synthesis.json"
            input_path.write_text(
                json.dumps(
                    _synthesis_payload(
                        summary="This includes token.json and must be rejected."
                    )
                ),
                encoding="utf-8",
            )
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)
                    before = count_synthesis_import_previews(connection)

                result = _run_cli(
                    [
                        "synthesis",
                        "preview",
                        "--db",
                        str(db_path),
                        "--input-file",
                        str(input_path),
                        "--source-type",
                        "chatgpt_synthesis",
                        "--json",
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = count_synthesis_import_previews(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 1)
        self.assertEqual(after, before)
        self.assertEqual(payload["status"], "rejected")
        self.assertTrue(payload["no_external_writes"])


class OperatorCliFileOutputWorkflowTest(unittest.TestCase):
    def test_briefing_export_writes_existing_output_to_explicit_safe_path_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "morning-brief.md"
            with _db_with_briefing_output() as tuple_result:
                db_path, briefing_output_id = tuple_result
                before = _table_counts(db_path)
                result = _run_cli(
                    [
                        "briefing",
                        "export",
                        "--db",
                        str(db_path),
                        "--briefing-output-id",
                        briefing_output_id,
                        "--output-file",
                        str(output_path),
                        "--json",
                    ]
                )
                after = _table_counts(db_path)

            payload = json.loads(result.stdout)
            self.assertEqual(result.code, 0)
            self.assertEqual(before, after)
            self.assertTrue(output_path.is_file())
            self.assertIn("No-send preview", output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "exported")
            self.assertFalse(payload["database_write"])
            self.assertTrue(payload["file_write"])
            self.assertTrue(payload["no_external_writes"])

    def test_dashboard_render_writes_static_html_without_db_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "today.html"
            with _seeded_runtime_db() as db_path:
                before = _table_counts(db_path)
                result = _run_cli(
                    [
                        "dashboard",
                        "render",
                        "--db",
                        str(db_path),
                        "--date",
                        SOURCE_DATE,
                        "--timezone",
                        DEFAULT_TIMEZONE,
                        "--output-file",
                        str(output_path),
                        "--json",
                    ]
                )
                after = _table_counts(db_path)

            html = output_path.read_text(encoding="utf-8")
            payload = json.loads(result.stdout)

        self.assertEqual(result.code, 0)
        self.assertEqual(before, after)
        self.assertIn("Personal OS Today View", html)
        self.assertIn("Read-only preview", html)
        self.assertNotIn("<form", html.lower())
        self.assertNotIn("/synthesis-import/preview", html)
        self.assertEqual(payload["status"], "rendered")
        self.assertTrue(payload["static_html_only"])
        self.assertFalse(payload["database_write"])
        self.assertTrue(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])

    def test_safe_temp_output_paths_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "safe-output.html"
            with _seeded_runtime_db() as db_path:
                result = _run_cli(
                    [
                        "dashboard",
                        "render",
                        "--db",
                        str(db_path),
                        "--date",
                        SOURCE_DATE,
                        "--output-file",
                        str(output_path),
                    ]
                )
                output_exists = output_path.is_file()

        self.assertEqual(result.code, 0)
        self.assertIn("status: rendered", result.stdout)
        self.assertTrue(output_exists)


class OperatorCliBoundaryTest(unittest.TestCase):
    def test_docs_describe_phase_12a_operator_cli_boundary(self) -> None:
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
            "phase 12a",
            "operator cli",
            "personalos status",
            "personalos briefing preview",
            "personalos synthesis preview",
            "personalos dashboard render",
            "explicit `--db`",
            "explicit `--output-file`",
            "no live model/api calls",
            "no scheduler",
            "no launchagents",
            "no production runtime activation",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_cli_modules_have_no_live_api_client_imports(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(cli),
                (REPO_ROOT / "src" / "personalos" / "path_safety.py").read_text(
                    encoding="utf-8"
                ),
            ]
        )
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

    def test_phase_12a_tests_leave_no_repo_var_or_sqlite_artifacts(self) -> None:
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
                if filename in {".sqlite", ".sqlite3"} or path.suffix in {
                    ".sqlite",
                    ".sqlite3",
                    ".db",
                }:
                    db_artifacts.append(path)

        self.assertEqual(db_artifacts, [])
        self.assertEqual(var_dirs, [])


class CliRunResult:
    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def _run_cli(args: list[str]) -> CliRunResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = cli.main(args)
        except SystemExit as error:
            code = 0 if error.code is None else int(error.code)
    return CliRunResult(code, stdout.getvalue(), stderr.getvalue())


@contextmanager
def _db_with_briefing_output() -> Iterator[tuple[Path, str]]:
    with _seeded_runtime_db() as db_path:
        with _sqlite_connection(db_path) as connection:
            _enable_briefing_permissions(connection)
            _enable_composer_permissions(connection)
            result = _run_cli(
                [
                    "briefing",
                    "preview",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--window",
                    "morning",
                    "--json",
                ]
            )
            if result.code != 0:
                raise AssertionError("briefing preview setup failed")
            output_id = connection.execute(
                "SELECT id FROM briefing_outputs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()["id"]
        yield db_path, str(output_id)


@contextmanager
def _seeded_runtime_db() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        profile = _runtime_profile(temp_path)
        with _migrated_connection(temp_path / "auth-runtime") as permission_connection:
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


def _enable_briefing_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_WRITE_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_RUN_PERMISSION)


def _enable_composer_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)


def _enable_synthesis_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"phase": "12a", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _runtime_profile(temp_path: Path) -> dict[str, object]:
    return {
        "profile_name": "phase-12a-preview",
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


def _table_counts(db_path: Path) -> dict[str, int]:
    with _sqlite_connection(db_path) as connection:
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
    }


def _synthesis_payload(
    *,
    summary: str = "Structured ChatGPT synthesis for preview import.",
) -> dict[str, object]:
    return {
        "schema_version": "synthesis_import.v1",
        "source_type": "chatgpt_synthesis",
        "source_timestamp": "2026-06-15T10:00:00+00:00",
        "source_reference": "chatgpt-thread-phase-12a",
        "summary": summary,
        "candidates": {
            "priorities": [
                {
                    "title": "Stabilize operator CLI",
                    "summary": "Keep CLI workflows no-send and preview-only.",
                    "source_type": "chatgpt_synthesis",
                    "source_id": "phase-12a",
                    "risk_level": "low",
                    "approval_mode": "auto_allowed",
                    "status": "active",
                    "review_note": "Review CLI output before later runtime wiring.",
                }
            ],
            "projects": [],
            "followups": [],
            "routine_changes": [],
            "todoist_tasks": [],
            "calendar_blocks": [],
            "clarity_notes": [],
            "review_questions": [],
        },
        "warnings": ["Preview only; no writes."],
    }

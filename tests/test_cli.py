import io
import inspect
import json
import os
import re
import sqlite3
import tempfile
import unittest
from unittest import mock
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import date
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
from personalos.priorities import (
    PRIORITY_ENGINE_READ_PERMISSION,
    PRIORITY_ENGINE_WRITE_PERMISSION,
)
from personalos.routines import (
    ROUTINE_ENGINE_READ_PERMISSION,
    ROUTINE_ENGINE_WRITE_PERMISSION,
)
from personalos.runtime_bootstrap import (
    RUNTIME_BOOTSTRAP_RUN_PERMISSION,
    RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
    bootstrap_runtime_database,
)
from personalos.scheduler import count_scheduler_jobs, count_scheduler_runs
from personalos.side_effects import (
    SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    SIDE_EFFECT_LEDGER_READ_PERMISSION,
    SIDE_EFFECT_LEDGER_WRITE_PERMISSION,
    count_external_write_attempts,
    count_external_write_intents,
    count_idempotency_records,
)
from personalos.synthesis_apply import (
    SYNTHESIS_APPLY_APPLY_PERMISSION,
    SYNTHESIS_APPLY_READ_PERMISSION,
    SYNTHESIS_APPLY_WRITE_PERMISSION,
    count_synthesis_apply_runs,
)
from personalos.state import (
    count_briefing_outputs,
    count_composer_outputs,
    count_composer_packets,
    count_daily_plans,
    count_model_runs,
    count_priorities,
    count_projects,
    count_synthesis_import_previews,
    upsert_permission_setting,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
    create_synthesis_import_preview_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE = "2026-06-15"


class OperatorCliArgumentAndPathSafetyTest(unittest.TestCase):

    def test_scheduler_help_keeps_simulated_no_send_no_activation_wording(self) -> None:
        scheduler_result = _run_cli(["scheduler", "--help"])
        scheduler_help = " ".join(scheduler_result.stdout.split())
        self.assertEqual(scheduler_result.code, 0)
        self.assertIn("No-send scheduler", scheduler_help)
        self.assertIn("never activate a scheduler", scheduler_help)
        self.assertIn("foreground no-send simulation only", scheduler_help)
        self.assertIn("scheduler activation", scheduler_help)

        expected_phrases = (
            "no-send",
            "scheduler",
            "LaunchAgent",
            "crontab",
            "daemon",
            "background loop",
            "production runtime",
        )
        for command in ("jobs", "preview", "run", "seed-dev"):
            with self.subTest(command=command):
                result = _run_cli(["scheduler", command, "--help"])
                help_text = " ".join(result.stdout.split())
                self.assertEqual(result.code, 0)
                for phrase in expected_phrases:
                    self.assertIn(phrase, help_text)

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
            [
                "synthesis",
                "apply",
                "--preview-id",
                "synthesis-import-preview-test",
                "--approval-file",
                "/tmp/approval.json",
            ],
            ["side-effects", "summary"],
            ["side-effects", "record-dry-run", "--input-file", "/tmp/input.json"],
            ["scheduler", "jobs"],
            ["scheduler", "preview", "--date", SOURCE_DATE],
            ["scheduler", "run", "--job-type", "status_summary"],
            ["scheduler", "seed-dev", "--profile", "safe_no_send"],
        ):
            with self.subTest(args=args):
                result = _run_cli(args)
                self.assertEqual(result.code, 2)
                self.assertIn("--db", result.stderr)
                self.assertIn("No external writes were attempted.", result.stderr)
                self.assertIn("Next: rerun with --db <path-to-local-test-db>.", result.stderr)


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


    def test_synthesis_apply_requires_approval_file(self) -> None:
        with _seeded_runtime_db() as db_path:
            result = _run_cli(
                [
                    "synthesis",
                    "apply",
                    "--db",
                    str(db_path),
                    "--preview-id",
                    "synthesis-import-preview-test",
                ]
            )

        self.assertEqual(result.code, 2)
        self.assertIn("--approval-file", result.stderr)



class OperatorCliReadAndPreviewWorkflowTest(unittest.TestCase):




























































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

    def test_synthesis_preview_human_output_has_no_send_completion_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "synthesis.json"
            input_path.write_text(json.dumps(_synthesis_payload()), encoding="utf-8")
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)

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
                    ]
                )

        self.assertEqual(result.code, 0)
        self.assertIn("Workflow complete: ChatGPT synthesis preview", result.stdout)
        self.assertIn("Mode: inert / no-send / preview", result.stdout)
        self.assertIn("DB target: temporary/test/local safe DB", result.stdout)
        self.assertIn("Local SQLite read: yes", result.stdout)
        self.assertIn("Local SQLite changes: local preview/audit rows changed", result.stdout)
        self.assertIn("External writes: none", result.stdout)
        self.assertIn("Credentials: not loaded", result.stdout)
        self.assertIn("Output: stdout human", result.stdout)
        self.assertIn("Candidate changes:", result.stdout)
        self.assertIn("Safe next action:", result.stdout)
        self.assertIn("- Review preview candidate changes.", result.stdout)
        self.assertIn("Rail states:", result.stdout)
        self.assertIn("- gmail: inert", result.stdout)
        self.assertIn("- todoist: inert", result.stdout)
        self.assertIn("Scheduler: off", result.stdout)

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

    def test_synthesis_apply_rejects_malformed_approval_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_path = Path(temp_dir) / "approval.json"
            approval_path.write_text("{bad json", encoding="utf-8")
            with _seeded_runtime_db() as db_path:
                result = _run_cli(
                    [
                        "synthesis",
                        "apply",
                        "--db",
                        str(db_path),
                        "--preview-id",
                        "synthesis-import-preview-test",
                        "--approval-file",
                        str(approval_path),
                    ]
                )

        self.assertEqual(result.code, 1)
        self.assertIn("input file must contain JSON", result.stderr)
        self.assertIn("No external writes were attempted.", result.stderr)
        self.assertIn("Next: fix the JSON file", result.stderr)

    def test_synthesis_apply_rejects_mismatched_preview_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_path = Path(temp_dir) / "approval.json"
            approval_path.write_text(
                json.dumps(
                    {
                        "preview_id": "wrong-preview",
                        "approved_candidates": [
                            {"candidate_type": "priority", "candidate_index": 0}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)
                    _enable_synthesis_apply_permissions(connection)
                    preview = create_synthesis_import_preview_record(
                        connection,
                        json.dumps(_synthesis_payload_with_project()),
                    )
                    before = _synthesis_apply_counts(connection)

                result = _run_cli(
                    [
                        "synthesis",
                        "apply",
                        "--db",
                        str(db_path),
                        "--preview-id",
                        preview["record"]["id"],
                        "--approval-file",
                        str(approval_path),
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = _synthesis_apply_counts(connection)

        self.assertEqual(result.code, 1)
        self.assertIn("preview_id does not match", result.stderr)
        self.assertEqual(after, before)

    def test_synthesis_apply_cli_applies_internal_state_only_from_approval_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_path = Path(temp_dir) / "approval.json"
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_synthesis_permissions(connection)
                    _enable_synthesis_apply_permissions(connection)
                    preview = create_synthesis_import_preview_record(
                        connection,
                        json.dumps(_synthesis_payload_with_project()),
                    )
                    preview_id = preview["record"]["id"]
                    approval_path.write_text(
                        json.dumps(
                            {
                                "preview_id": preview_id,
                                "approved_candidates": [
                                    {"candidate_type": "priority", "candidate_index": 0},
                                    {"candidate_type": "project", "candidate_index": 0},
                                ],
                                "rejected_candidates": [],
                                "approval_note": "Internal SQLite apply only.",
                            }
                        ),
                        encoding="utf-8",
                    )
                    before = _table_counts(db_path)

                result = _run_cli(
                    [
                        "synthesis",
                        "apply",
                        "--db",
                        str(db_path),
                        "--preview-id",
                        preview_id,
                        "--approval-file",
                        str(approval_path),
                        "--json",
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = _table_counts(db_path)
                    priority_count = count_priorities(connection)
                    project_count = count_projects(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(after["priorities"] - before["priorities"], 1)
        self.assertEqual(after["projects"] - before["projects"], 1)
        self.assertEqual(after["synthesis_apply_runs"] - before["synthesis_apply_runs"], 1)
        self.assertEqual(after["external_write_intents"], before["external_write_intents"])
        self.assertEqual(after["external_write_attempts"], before["external_write_attempts"])
        self.assertGreaterEqual(priority_count, 1)
        self.assertGreaterEqual(project_count, 1)
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_send_mode"])
        self.assertFalse(payload["live_write"])
        self.assertTrue(payload["internal_state_mutation"])
        self.assertFalse(payload["external_mutation"])

    def test_side_effects_summary_fails_closed_without_read_permission(self) -> None:
        with _seeded_runtime_db() as db_path:
            before = _table_counts(db_path)
            result = _run_cli(["side-effects", "summary", "--db", str(db_path), "--json"])
            after = _table_counts(db_path)

        self.assertEqual(result.code, 1)
        self.assertEqual(before, after)
        self.assertIn("side-effect ledger permission", result.stderr.lower())

    def test_side_effects_summary_is_read_only_with_read_permission(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, SIDE_EFFECT_LEDGER_READ_PERMISSION)
            before = _table_counts(db_path)
            result = _run_cli(["side-effects", "summary", "--db", str(db_path), "--json"])
            after = _table_counts(db_path)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(before, after)
        self.assertFalse(payload["database_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_send_mode"])
        self.assertFalse(payload["live_write"])
        self.assertEqual(payload["summary"]["intent_count"], 0)
        self.assertEqual(payload["summary"]["attempt_count"], 0)

    def test_side_effects_record_dry_run_persists_only_local_ledger_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "side-effect.json"
            input_path.write_text(json.dumps(_side_effect_payload()), encoding="utf-8")
            with _seeded_runtime_db() as db_path:
                with _sqlite_connection(db_path) as connection:
                    _enable_side_effect_permissions(connection)
                    before = _side_effect_counts(connection)

                result = _run_cli(
                    [
                        "side-effects",
                        "record-dry-run",
                        "--db",
                        str(db_path),
                        "--input-file",
                        str(input_path),
                        "--json",
                    ]
                )

                with _sqlite_connection(db_path) as connection:
                    after = _side_effect_counts(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(after["external_write_intents"] - before["external_write_intents"], 1)
        self.assertEqual(after["external_write_attempts"] - before["external_write_attempts"], 1)
        self.assertEqual(after["idempotency_records"] - before["idempotency_records"], 1)
        self.assertEqual(payload["status"], "recorded")
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_send_mode"])
        self.assertFalse(payload["live_write"])
        self.assertTrue(payload["simulated_or_dry_run"])
        self.assertFalse(payload["external_mutation"])

    def test_routines_create_update_list_round_trip_via_cli(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, ROUTINE_ENGINE_READ_PERMISSION)
                _set_permission(connection, ROUTINE_ENGINE_WRITE_PERMISSION)

            create_result = _run_cli(
                [
                    "routines",
                    "create",
                    "--db",
                    str(db_path),
                    "--routine-id",
                    "routine-cli-test",
                    "--name",
                    "Morning pages",
                    "--notes",
                    "Write three pages.",
                    "--json",
                ]
            )
            update_result = _run_cli(
                [
                    "routines",
                    "update",
                    "--db",
                    str(db_path),
                    "--routine-id",
                    "routine-cli-test",
                    "--name",
                    "Morning pages (renamed)",
                    "--no-enabled",
                    "--notes",
                    "Disabled for travel.",
                    "--json",
                ]
            )
            list_result = _run_cli(
                ["routines", "list", "--db", str(db_path), "--json"]
            )

        create_payload = json.loads(create_result.stdout)
        update_payload = json.loads(update_result.stdout)
        list_payload = json.loads(list_result.stdout)

        self.assertEqual(create_result.code, 0)
        self.assertEqual(create_payload["status"], "created")
        self.assertEqual(create_payload["routine"]["name"], "Morning pages")

        self.assertEqual(update_result.code, 0)
        self.assertEqual(update_payload["status"], "updated")
        self.assertEqual(update_payload["routine"]["name"], "Morning pages (renamed)")
        self.assertFalse(update_payload["routine"]["enabled"])
        self.assertEqual(update_payload["routine"]["notes"], "Disabled for travel.")

        self.assertEqual(list_result.code, 0)
        routines_by_id = {
            routine["routine_id"]: routine for routine in list_payload["routines"]
        }
        self.assertIn("routine-cli-test", routines_by_id)
        self.assertEqual(routines_by_id["routine-cli-test"]["name"], "Morning pages (renamed)")
        self.assertFalse(routines_by_id["routine-cli-test"]["enabled"])

    def test_routines_create_reports_clean_failure_without_write_permission(self) -> None:
        with _seeded_runtime_db() as db_path:
            before = _table_counts(db_path)
            result = _run_cli(
                [
                    "routines",
                    "create",
                    "--db",
                    str(db_path),
                    "--routine-id",
                    "routine-denied",
                    "--name",
                    "Should not persist",
                    "--json",
                ]
            )
            after = _table_counts(db_path)

        self.assertEqual(result.code, 1)
        self.assertEqual(before, after)
        self.assertIn(ROUTINE_ENGINE_WRITE_PERMISSION.lower(), result.stderr.lower())
        self.assertEqual(result.stdout, "")

    def test_priorities_create_update_list_round_trip_via_cli(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, PRIORITY_ENGINE_READ_PERMISSION)
                _set_permission(connection, PRIORITY_ENGINE_WRITE_PERMISSION)

            create_result = _run_cli(
                [
                    "priorities",
                    "create",
                    "--db",
                    str(db_path),
                    "--priority-id",
                    "priority-cli-test",
                    "--title",
                    "Ship P-CORE-03",
                    "--json",
                ]
            )
            update_result = _run_cli(
                [
                    "priorities",
                    "update",
                    "--db",
                    str(db_path),
                    "--priority-id",
                    "priority-cli-test",
                    "--title",
                    "Ship P-CORE-03 (updated)",
                    "--status",
                    "paused",
                    "--json",
                ]
            )
            list_result = _run_cli(
                ["priorities", "list", "--db", str(db_path), "--json"]
            )

        create_payload = json.loads(create_result.stdout)
        update_payload = json.loads(update_result.stdout)
        list_payload = json.loads(list_result.stdout)

        self.assertEqual(create_result.code, 0)
        self.assertEqual(create_payload["status"], "created")
        self.assertEqual(create_payload["priority"]["title"], "Ship P-CORE-03")

        self.assertEqual(update_result.code, 0)
        self.assertEqual(update_payload["status"], "updated")
        self.assertEqual(
            update_payload["priority_after"]["title"], "Ship P-CORE-03 (updated)"
        )
        self.assertEqual(update_payload["priority_after"]["status"], "paused")

        self.assertEqual(list_result.code, 0)
        priorities_by_id = {
            priority["priority_id"]: priority for priority in list_payload["priorities"]
        }
        self.assertIn("priority-cli-test", priorities_by_id)
        self.assertEqual(
            priorities_by_id["priority-cli-test"]["title"], "Ship P-CORE-03 (updated)"
        )
        self.assertEqual(priorities_by_id["priority-cli-test"]["status"], "paused")

    def test_priorities_create_reports_clean_failure_without_write_permission(self) -> None:
        with _seeded_runtime_db() as db_path:
            before = _table_counts(db_path)
            result = _run_cli(
                [
                    "priorities",
                    "create",
                    "--db",
                    str(db_path),
                    "--priority-id",
                    "priority-denied",
                    "--title",
                    "Should not persist",
                    "--json",
                ]
            )
            after = _table_counts(db_path)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 1)
        self.assertEqual(before, after)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn(PRIORITY_ENGINE_WRITE_PERMISSION, payload["reason"])

    def test_scheduler_seed_dev_creates_safe_no_send_job_records(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                before = count_scheduler_jobs(connection)

            result = _run_cli(
                [
                    "scheduler",
                    "seed-dev",
                    "--db",
                    str(db_path),
                    "--profile",
                    "safe_no_send",
                    "--json",
                ]
            )

            with _sqlite_connection(db_path) as connection:
                after = count_scheduler_jobs(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(after - before, 5)
        self.assertEqual(payload["status"], "seeded")
        self.assertEqual(payload["scheduler_job_count"], 5)
        self.assertTrue(payload["no_send_mode"])
        self.assertTrue(payload["no_external_writes"])
        self.assertFalse(payload["live_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["scheduler_activation"])
        self.assertFalse(payload["launch_agent_installed"])
        for job in payload["scheduler_jobs"]:
            with self.subTest(job=job["scheduler_job_id"]):
                self.assertTrue(job["enabled"])
                self.assertEqual(job["status"], "enabled_dev_test")
                self.assertTrue(job["no_send_mode"])
                self.assertTrue(job["no_external_writes"])
                self.assertTrue(job["fake_model_only"])

    def test_scheduler_jobs_and_preview_are_read_only(self) -> None:
        with _seeded_runtime_db() as db_path:
            seed_result = _run_cli(
                [
                    "scheduler",
                    "seed-dev",
                    "--db",
                    str(db_path),
                    "--profile",
                    "safe_no_send",
                    "--json",
                ]
            )
            self.assertEqual(seed_result.code, 0)
            before_jobs = _table_counts(db_path)
            jobs_result = _run_cli(["scheduler", "jobs", "--db", str(db_path), "--json"])
            after_jobs = _table_counts(db_path)
            preview_result = _run_cli(
                [
                    "scheduler",
                    "preview",
                    "--db",
                    str(db_path),
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--json",
                ]
            )
            after_preview = _table_counts(db_path)

        jobs_payload = json.loads(jobs_result.stdout)
        preview_payload = json.loads(preview_result.stdout)
        self.assertEqual(jobs_result.code, 0)
        self.assertEqual(preview_result.code, 0)
        self.assertEqual(before_jobs, after_jobs)
        self.assertEqual(after_jobs, after_preview)
        self.assertEqual(jobs_payload["scheduler_job_count"], 5)
        self.assertFalse(jobs_payload["database_write"])
        self.assertFalse(preview_payload["database_write"])
        self.assertFalse(preview_payload["scheduler_activation"])
        self.assertFalse(preview_payload["launch_agent_installed"])

    def test_scheduler_run_status_summary_records_scheduler_run_only(self) -> None:
        with _seeded_runtime_db() as db_path:
            before = _table_counts(db_path)
            result = _run_cli(
                [
                    "scheduler",
                    "run",
                    "--db",
                    str(db_path),
                    "--job-type",
                    "status_summary",
                    "--json",
                ]
            )
            after = _table_counts(db_path)

        payload = json.loads(result.stdout)
        changed = {
            table_name: after[table_name] - before.get(table_name, 0)
            for table_name in after
            if after[table_name] != before.get(table_name, 0)
        }
        report = payload["completion_report"]
        self.assertEqual(result.code, 0)
        self.assertEqual(changed, {"scheduler_runs": 1})
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(report["no_send_mode"])
        self.assertTrue(report["no_external_writes"])
        self.assertFalse(report["live_write"])
        self.assertFalse(report["external_mutation"])
        self.assertFalse(report["scheduler_activation"])
        self.assertFalse(report["launch_agent_installed"])
        self.assertFalse(report["daemonized"])
        self.assertFalse(report["background_process_started"])

    def test_scheduler_run_briefing_preview_uses_fake_no_send_composer_only(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_briefing_permissions(connection)
                _enable_composer_permissions(connection)
                before = _briefing_counts(connection)
                before_scheduler_runs = count_scheduler_runs(connection)
                before_external_attempts = count_external_write_attempts(connection)

            result = _run_cli(
                [
                    "scheduler",
                    "run",
                    "--db",
                    str(db_path),
                    "--job-type",
                    "briefing_preview",
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
                after_scheduler_runs = count_scheduler_runs(connection)
                after_external_attempts = count_external_write_attempts(connection)

        payload = json.loads(result.stdout)
        workflow_report = payload["workflow_report"]
        self.assertEqual(result.code, 0)
        self.assertEqual(after_scheduler_runs - before_scheduler_runs, 1)
        self.assertEqual(after["daily_plans"] - before["daily_plans"], 1)
        self.assertEqual(after["briefing_outputs"] - before["briefing_outputs"], 1)
        self.assertEqual(after["composer_packets"] - before["composer_packets"], 1)
        self.assertEqual(after["composer_outputs"] - before["composer_outputs"], 1)
        self.assertEqual(after["model_runs"] - before["model_runs"], 1)
        self.assertEqual(after_external_attempts, before_external_attempts)
        self.assertTrue(workflow_report["no_send_mode"])
        self.assertTrue(workflow_report["no_external_writes"])
        self.assertTrue(workflow_report["no_live_model_call"])
        self.assertTrue(workflow_report["fake_composer_adapter"])
        self.assertFalse(workflow_report["network_called"])
        self.assertFalse(payload["completion_report"]["scheduler_activation"])
        self.assertFalse(payload["completion_report"]["launch_agent_installed"])

    def test_scheduler_dashboard_render_preview_requires_output_file(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                before_scheduler_runs = count_scheduler_runs(connection)
            result = _run_cli(
                [
                    "scheduler",
                    "run",
                    "--db",
                    str(db_path),
                    "--job-type",
                    "dashboard_render_preview",
                    "--date",
                    SOURCE_DATE,
                    "--timezone",
                    DEFAULT_TIMEZONE,
                    "--json",
                ]
            )
            with _sqlite_connection(db_path) as connection:
                after_scheduler_runs = count_scheduler_runs(connection)

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(after_scheduler_runs - before_scheduler_runs, 1)
        self.assertIn("output_file", payload["workflow_report"]["reason"])
        self.assertFalse(payload["completion_report"]["external_mutation"])
        self.assertFalse(payload["completion_report"]["scheduler_activation"])


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
        self.assertIn("Read-only except explicit local synthesis preview creation", html)
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


def _enable_synthesis_apply_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SYNTHESIS_APPLY_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_APPLY_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_APPLY_APPLY_PERMISSION)


def _enable_side_effect_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SIDE_EFFECT_LEDGER_READ_PERMISSION)
    _set_permission(connection, SIDE_EFFECT_LEDGER_WRITE_PERMISSION)
    _set_permission(connection, SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION)


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


def _side_effect_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "external_write_intents": count_external_write_intents(connection),
        "external_write_attempts": count_external_write_attempts(connection),
        "idempotency_records": count_idempotency_records(connection),
    }


def _synthesis_apply_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "synthesis_apply_runs": count_synthesis_apply_runs(connection),
        "priorities": count_priorities(connection),
        "projects": count_projects(connection),
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


def _synthesis_payload_with_project() -> dict[str, object]:
    payload = _synthesis_payload(summary="Structured ChatGPT synthesis for apply.")
    candidates = dict(payload["candidates"])
    candidates["projects"] = [
        {
            "title": "Synthesis apply CLI project",
            "summary": "Apply a safe project candidate into internal SQLite state.",
            "source_type": "chatgpt_synthesis",
            "source_id": "phase-13a-cli",
            "risk_level": "low",
            "approval_mode": "auto_allowed",
            "status": "active",
            "review_note": "No external writes.",
        }
    ]
    candidates["todoist_tasks"] = []
    candidates["calendar_blocks"] = []
    candidates["clarity_notes"] = []
    candidates["review_questions"] = []
    payload["candidates"] = candidates
    return payload


def _side_effect_payload() -> dict[str, object]:
    return {
        "intent": {
            "source_type": "fake_fixture",
            "source_id": "phase-12b-cli",
            "target_system": "todoist",
            "operation_type": "create",
            "risk_level": "low",
            "approval_mode": "auto_allowed",
            "payload": {
                "title": "Review side-effect ledger",
                "project": "Personal OS",
                "labels": ["review"],
            },
            "validation_report": {
                "validated_by": "tests",
                "no_external_writes": True,
                "no_send_mode": True,
            },
            "created_at": "2026-06-15T10:00:00+00:00",
            "updated_at": "2026-06-15T10:00:00+00:00",
        },
        "attempt": {
            "mode": "dry_run",
            "adapter_name": "phase_12b_fake_adapter",
            "status": "succeeded",
            "response_summary": {
                "result": "would_create",
                "external_mutation": False,
            },
            "created_at": "2026-06-15T10:01:00+00:00",
        },
    }

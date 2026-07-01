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
from personalos.openclaw_model_strategy import (
    OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
    OPENCLAW_MODEL_SMOKE_MISSING_CLIENT,
    OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG,
)
from personalos.phase14c_connectivity_setup import (
    PHASE14C_CONNECTIVITY_SETUP_ENV_FILE,
    PHASE14C_CONNECTIVITY_SETUP_ENTRY_NAMES,
)
from personalos.phase14c_gmail_live_smoke import (
    PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
)
from personalos.phase14c_todoist_live_smoke import next_upcoming_monday
from personalos.permissions import PermissionMode
from personalos.phase14c_supervised_smoke import (
    LIVE_RUN_MODE,
    PHASE14C_SUPERVISED_SMOKE_TEMPLATE_RECIPIENT,
    REQUIRED_CONFIG_ENTRY_NAMES,
    build_default_phase14c_supervised_smoke_request,
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
    def test_cli_help_renders(self) -> None:
        result = _run_cli(["--help"])

        self.assertEqual(result.code, 0)
        self.assertIn("Safe local operator CLI", result.stdout)
        self.assertIn("inert/no-send", result.stdout)
        self.assertIn("workflows", result.stdout)
        self.assertIn("status", result.stdout)
        self.assertIn("readiness", result.stdout)
        self.assertIn("briefing", result.stdout)
        self.assertIn("synthesis", result.stdout)
        self.assertIn("side-effects", result.stdout)
        self.assertIn("dashboard", result.stdout)
        self.assertIn("scheduler", result.stdout)
        self.assertIn("phase14c", result.stdout)

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

    def test_synthesis_input_file_path_safety_rejects_protected_sensitive_and_var_paths(
        self,
    ) -> None:
        protected_personalos = Path.home() / "PersonalOS" / "structured-synthesis.json"
        protected_openclaw = Path.home() / ".openclaw" / "structured-synthesis.json"
        credential_path = Path(tempfile.gettempdir()) / "oauth-token-synthesis.json"
        production_path = Path(tempfile.gettempdir()) / "production" / "synthesis.json"
        repo_var_path = REPO_ROOT / "var" / "structured-synthesis.json"

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_permissions(connection)
                before = count_synthesis_import_previews(connection)

            for input_path in (
                protected_personalos,
                protected_openclaw,
                credential_path,
                production_path,
                repo_var_path,
            ):
                with self.subTest(input_path=input_path):
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
                    self.assertEqual(result.code, 1)
                    self.assertIn("error:", result.stderr)

            with _sqlite_connection(db_path) as connection:
                after = count_synthesis_import_previews(connection)

        self.assertEqual(after, before)

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

    def test_synthesis_approval_file_path_safety_rejects_protected_sensitive_and_var_paths(
        self,
    ) -> None:
        protected_personalos = Path.home() / "PersonalOS" / "approval.json"
        protected_openclaw = Path.home() / ".openclaw" / "approval.json"
        credential_path = Path(tempfile.gettempdir()) / "oauth-token-approval.json"
        production_path = Path(tempfile.gettempdir()) / "production" / "approval.json"
        repo_var_path = REPO_ROOT / "var" / "approval.json"

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                before = count_synthesis_apply_runs(connection)

            for approval_path in (
                protected_personalos,
                protected_openclaw,
                credential_path,
                production_path,
                repo_var_path,
            ):
                with self.subTest(approval_path=approval_path):
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
                    self.assertIn("error:", result.stderr)

            with _sqlite_connection(db_path) as connection:
                after = count_synthesis_apply_runs(connection)

        self.assertEqual(after, before)


class OperatorCliReadAndPreviewWorkflowTest(unittest.TestCase):
    def test_workflows_command_lists_safe_local_and_blocked_live_actions(self) -> None:
        result = _run_cli(["workflows"])

        self.assertEqual(result.code, 0)
        self.assertIn("Workflow complete: No-send workflow catalog", result.stdout)
        self.assertIn("Mode: inert / no-send / report-only", result.stdout)
        self.assertIn("DB target: not applicable - no DB opened", result.stdout)
        self.assertIn("Local SQLite read: no", result.stdout)
        self.assertIn("Local SQLite changes: none", result.stdout)
        self.assertIn("External writes: none", result.stdout)
        self.assertIn("Credentials: not loaded", result.stdout)
        self.assertIn("Available safe local workflows:", result.stdout)
        for workflow_name in (
            "readiness status",
            "operator status JSON export",
            "ChatGPT synthesis import preview",
            "approved synthesis apply to local SQLite only",
            "no-send briefing preview/export",
            "Today View/status preview",
            "side-effect/idempotency ledger inspection",
            "simulated scheduler preview",
            "Phase 14-C connectivity setup",
            "Phase 14-C supervised smoke-test runbook",
            "Phase 14-C supervised smoke dry-run rehearsal",
            "Phase 14-C Todoist Inbox/default smoke gate",
            "Phase 14-C OpenClaw model readiness",
            "Phase 14-C OpenRouter model smoke gate",
            "Phase 14-C live-smoke diagnostics",
            "Phase 14-C connected rehearsal plan",
            "Phase 14-C connected rehearsal gate",
        ):
            with self.subTest(workflow_name=workflow_name):
                self.assertIn(f"- {workflow_name}", result.stdout)
        self.assertIn("Command: personalos readiness status [--json]", result.stdout)
        self.assertIn("Blocked until explicit Phase 14/live approval:", result.stdout)
        self.assertIn("- Send Gmail", result.stdout)
        self.assertIn("- Write Todoist", result.stdout)
        self.assertIn("- Write Google Calendar", result.stdout)
        self.assertIn("- Load credentials", result.stdout)
        self.assertIn("- Call OpenClaw runtime", result.stdout)

    def test_workflows_command_json_is_stable_operator_status_compatible(self) -> None:
        result = _run_cli(["workflows", "--json"])

        payload = json.loads(result.stdout)
        workflow_names = {workflow["name"] for workflow in payload["safe_local_workflows"]}
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "workflows")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["readiness_status"], "not_ready")
        self.assertTrue(payload["inert_report_only"])
        self.assertFalse(payload["live_rails_activated"])
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertEqual(payload["external_writes"], "none")
        self.assertEqual(payload["credentials"], "not_loaded")
        self.assertEqual(payload["operator_status"]["schema_version"], "operator_status.v1")
        self.assertEqual(payload["operator_status"]["readiness_status"], "not_ready")
        self.assertTrue(payload["operator_status"]["inert_report_only"])
        self.assertFalse(payload["operator_status"]["live_rails_activated"])
        self.assertEqual(payload["operator_status"]["credential_status"]["status"], "not_loaded")
        self.assertEqual(payload["operator_status"]["external_write_status"]["status"], "none")
        self.assertIn("ChatGPT synthesis import preview", workflow_names)
        self.assertIn("simulated scheduler preview", workflow_names)
        self.assertIn("Phase 14-C connectivity setup", workflow_names)
        self.assertIn("Phase 14-C supervised smoke-test runbook", workflow_names)
        self.assertIn("Phase 14-C supervised smoke request template", workflow_names)
        self.assertIn("Phase 14-C supervised smoke dry-run rehearsal", workflow_names)
        self.assertIn("Phase 14-C supervised smoke request validation", workflow_names)
        self.assertIn(
            "Phase 14-C supervised smoke credential preflight",
            workflow_names,
        )
        self.assertIn("Phase 14-C supervised smoke live readiness", workflow_names)
        self.assertIn("Phase 14-C Gmail SMTP self-send smoke gate", workflow_names)
        self.assertIn("Phase 14-C Todoist Inbox/default smoke gate", workflow_names)
        self.assertIn("Send Gmail", payload["blocked_actions"])
        self.assertIn("Call live model/API", payload["blocked_actions"])
        self.assertIn("Phase 14-C OpenRouter model smoke gate", workflow_names)
        self.assertIn("Phase 14-C live-smoke diagnostics", workflow_names)
        self.assertIn("Phase 14-C connected rehearsal plan", workflow_names)
        self.assertIn("Phase 14-C connected rehearsal gate", workflow_names)

    def test_phase14c_connectivity_setup_missing_names_only(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "todoist-secret-value",
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "openrouter-secret-provider",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "connectivity-setup", "--json"])

        payload = json.loads(result.stdout)
        setup = payload["connectivity_setup"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c connectivity-setup")
        self.assertEqual(payload["status"], "connectivity_config_names_missing")
        self.assertEqual(
            payload["workflow_mode"],
            "repo-local setup report / no values / no live clients",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertEqual(setup["env_file"]["path"], PHASE14C_CONNECTIVITY_SETUP_ENV_FILE)
        self.assertTrue(setup["env_file"]["gitignored"])
        self.assertFalse(setup["env_file"]["created_by_this_command"])
        self.assertTrue(setup["setup_script"]["prompts_for_secret_values_without_echo"])
        self.assertTrue(
            setup["setup_script"]["plain_controlled_recipient_prompt_echoes_for_typo_check"]
        )
        self.assertTrue(setup["setup_script"]["writes_via_temp_file_before_final_move"])
        self.assertTrue(setup["setup_script"]["refuses_to_overwrite_existing_env_file"])
        self.assertIn(
            "gmail-smtp-smoke --json",
            " ".join(setup["verification_commands"]),
        )
        self.assertIn(
            "todoist-inbox-smoke --json",
            " ".join(setup["verification_commands"]),
        )
        self.assertIn(
            "openrouter-model-smoke --json",
            " ".join(setup["verification_commands"]),
        )
        self.assertEqual(
            setup["rails"]["todoist"]["missing_config_entry_names"],
            [],
        )
        self.assertEqual(
            setup["rails"]["gmail"]["missing_config_entry_names"],
            [
                "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS",
                "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD",
                "PHASE14C_GMAIL_CONTROLLED_RECIPIENT",
            ],
        )
        self.assertEqual(
            setup["rails"]["openrouter"]["missing_config_entry_names"],
            [
                "PERSONALOS_OPENCLAW_MODEL_API_KEY",
                "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
                "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
            ],
        )
        self.assertFalse(setup["safety_assertions"]["credential_values_read"])
        self.assertFalse(setup["safety_assertions"]["present_config_entry_names_reported"])
        self.assertNotIn("todoist-secret-value", result.stdout)
        self.assertNotIn("openrouter-secret-provider", result.stdout)
        self.assertNotIn("PERSONALOS_PHASE14C_TODOIST_TOKEN", result.stdout)
        self.assertNotIn("PERSONALOS_OPENCLAW_MODEL_PROVIDER", result.stdout)

    def test_phase14c_connectivity_setup_complete_config_redacts_present_names(
        self,
    ) -> None:
        required_names = {
            name
            for names in PHASE14C_CONNECTIVITY_SETUP_ENTRY_NAMES.values()
            for name in names
        }
        secret_environment = {
            name: f"secret-connectivity-value-{index}"
            for index, name in enumerate(sorted(required_names))
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "connectivity-setup", "--json"])

        payload = json.loads(result.stdout)
        setup = payload["connectivity_setup"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "connectivity_config_names_present")
        self.assertEqual(setup["missing_config_entry_names_by_rail"], {})
        for rail in setup["rails"].values():
            self.assertEqual(rail["status"], "config_names_present")
            self.assertEqual(rail["missing_config_entry_names"], [])
            self.assertFalse(rail["present_config_entry_names_reported"])
            self.assertFalse(rail["credential_values_read"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, result.stdout)
        for present_name in required_names:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_connectivity_setup_script_is_gitignored_safe_setup(self) -> None:
        script_path = REPO_ROOT / "scripts" / "phase14c_connectivity_setup.sh"
        script_text = script_path.read_text(encoding="utf-8")
        gitignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".env", gitignore_text)
        self.assertIn(".env.*", gitignore_text)
        self.assertIn("read -r -s", script_text)
        self.assertIn("tmp_env_file", script_text)
        self.assertIn('if [[ -e "$env_file" ]]', script_text)
        self.assertIn('mv "$tmp_env_file" "$env_file"', script_text)
        self.assertIn("trap cleanup EXIT HUP INT TERM", script_text)
        self.assertIn("trap - EXIT HUP INT TERM", script_text)
        self.assertIn('prompt_plain \\', script_text)
        self.assertIn("chmod 600", script_text)
        self.assertIn(PHASE14C_CONNECTIVITY_SETUP_ENV_FILE, script_text)
        self.assertIn("PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS", script_text)
        self.assertIn("PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD", script_text)
        self.assertIn("PERSONALOS_OPENCLAW_MODEL_API_KEY", script_text)
        self.assertNotIn("0123456789abcdef", script_text)
        self.assertNotIn("sk-", script_text)

    def test_phase14c_supervised_smoke_runbook_command_is_read_only(self) -> None:
        result = _run_cli(["phase14c", "supervised-smoke-runbook", "--json"])

        payload = json.loads(result.stdout)
        runbook = payload["runbook"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c supervised-smoke-runbook")
        self.assertEqual(payload["workflow_mode"], "repo-local runbook / no live clients")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertEqual(runbook["status"], "supervised_smoke_test_prepared_not_executed")
        self.assertFalse(runbook["repo_prep_safety"]["todoist_task_created"])
        self.assertFalse(runbook["repo_prep_safety"]["calendar_event_created"])
        self.assertFalse(runbook["repo_prep_safety"]["gmail_email_created_or_sent"])
        self.assertFalse(runbook["repo_prep_safety"]["openclaw_invoked"])
        self.assertFalse(runbook["repo_prep_safety"]["credential_values_read"])

    def test_phase14c_supervised_smoke_request_template_is_not_authorization(
        self,
    ) -> None:
        with mock.patch.dict(os.environ, {"SECRET_ENV": "secret-value"}, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-request-template",
                    "--mode",
                    "live_run",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        template_report = payload["template_report"]
        request = template_report["request"]
        safety = template_report["safety_assertions"]
        self.assertEqual(result.code, 0)
        self.assertEqual(
            payload["command"], "phase14c supervised-smoke-request-template"
        )
        self.assertEqual(
            payload["status"], "request_template_generated_not_authorized"
        )
        self.assertEqual(
            payload["workflow_mode"],
            "repo-local request template / no live clients / no execution",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_environment_read"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(template_report["template_only_not_authorization"])
        self.assertFalse(template_report["ready_for_live_execution"])
        self.assertEqual(request["mode"], "live_run")
        self.assertFalse(request["live_run_requested"])
        self.assertIsNone(request["approval_reference"])
        self.assertEqual(
            request["controlled_test_recipients"],
            [PHASE14C_SUPERVISED_SMOKE_TEMPLATE_RECIPIENT],
        )
        self.assertFalse(template_report["validation_preview"]["accepted"])
        self.assertFalse(safety["live_run_executed"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["file_write"])
        self.assertFalse(safety["live_clients_initialized"])
        self.assertTrue(safety["template_only_not_authorization"])
        self.assertFalse(safety["ready_for_live_execution"])
        self.assertNotIn("normalized_request", template_report["validation_preview"])
        self.assertNotIn("secret-value", result.stdout)

    def test_phase14c_supervised_smoke_dry_run_command_writes_safe_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "phase14c-smoke-dry-run"

            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-dry-run",
                    "--output-dir",
                    str(output_dir),
                    "--json",
                ]
            )

            payload = json.loads(result.stdout)
            completion = payload["completion_report"]
            self.assertEqual(result.code, 0)
            self.assertEqual(payload["command"], "phase14c supervised-smoke-dry-run")
            self.assertEqual(
                payload["workflow_mode"],
                "repo-local dry-run / fake clients / no live clients",
            )
            self.assertEqual(payload["status"], "completed")
            self.assertFalse(payload["database_write"])
            self.assertFalse(payload["external_mutation"])
            self.assertTrue(payload["file_write"])
            self.assertTrue(payload["no_external_writes"])
            self.assertTrue(payload["no_credentials_loaded"])
            self.assertTrue(payload["no_live_clients_initialized"])
            self.assertTrue(payload["no_live_rails_activated"])
            self.assertTrue(payload["fake_clients_used"])
            self.assertFalse(payload["live_clients_called"])
            self.assertFalse(payload["local_sqlite_read"])
            self.assertFalse(payload["local_sqlite_changed"])
            self.assertEqual(payload["credentials"], "not_loaded")
            self.assertFalse(payload["production_db_active"])
            self.assertEqual(payload["database_target"]["path"], None)
            self.assertEqual(payload["output_target"]["kind"], "safe_temp_output_dir")
            self.assertEqual(payload["output_dir"], str(output_dir.resolve(strict=False)))

            self.assertEqual(completion["status"], "dry_run_rehearsal_completed")
            self.assertTrue(completion["validation"]["accepted"])
            self.assertNotIn("normalized_request", completion["validation"])
            self.assertIn("normalized_request_summary", completion["validation"])
            self.assertTrue(
                all(
                    completion["validation"]["normalized_request_summary"][
                        "boundaries_remain_false"
                    ].values()
                )
            )
            self.assertFalse(completion["safety_assertions"]["live_run_executed"])
            self.assertFalse(completion["safety_assertions"]["external_mutation"])
            self.assertFalse(completion["safety_assertions"]["credential_values_read"])
            self.assertFalse(completion["safety_assertions"]["production_db_active"])
            self.assertFalse(completion["safety_assertions"]["scheduler_activated"])
            self.assertTrue(completion["safety_assertions"]["writes_only_output_dir"])
            for rail in ("todoist", "google_calendar", "gmail", "openclaw"):
                fake_result = completion["fake_client_results"][rail]
                self.assertFalse(fake_result["network_called"])
                self.assertFalse(fake_result["credentials_read"])
                self.assertFalse(fake_result["external_mutation"])

            for path in payload["artifact_paths"].values():
                self.assertTrue(Path(path).is_file(), path)
                self.assertNotIn(
                    "self.phase14c.test@example.test",
                    Path(path).read_text(encoding="utf-8"),
                )
            self.assertNotIn("self.phase14c.test@example.test", result.stdout)

    def test_phase14c_supervised_smoke_dry_run_rejects_repo_output_dir(self) -> None:
        result = _run_cli(
            [
                "phase14c",
                "supervised-smoke-dry-run",
                "--output-dir",
                str(REPO_ROOT / "phase14c-smoke-output"),
                "--json",
            ]
        )

        self.assertEqual(result.code, 1)
        self.assertIn("error:", result.stderr)
        self.assertIn("must not be inside the repository", result.stderr)

    def test_phase14c_supervised_smoke_validate_command_redacts_request(self) -> None:
        private_recipient = "private.phase14c@example.test"
        request = build_default_phase14c_supervised_smoke_request(
            controlled_test_recipient=private_recipient
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "phase14c-request.json"
            input_file.write_text(json.dumps(request), encoding="utf-8")

            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-validate",
                    "--input-file",
                    str(input_file),
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        validation_report = payload["validation_report"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c supervised-smoke-validate")
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(
            payload["workflow_mode"],
            "repo-local validation / redacted report / no live clients",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(validation_report["accepted"])
        self.assertEqual(
            validation_report["input_request_summary"]["rails"]["gmail"]["to_count"],
            1,
        )
        self.assertNotIn("normalized_request", validation_report["validation"])
        self.assertIn(
            "normalized_request_summary",
            validation_report["validation"],
        )
        self.assertNotIn(private_recipient, result.stdout)

    def test_phase14c_supervised_smoke_validate_blocks_without_echo(self) -> None:
        unsafe = "secret-token-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request()
        request["test_marker"] = unsafe
        request["rails"]["gmail"]["emails"][0]["to"] = [unsafe]
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "phase14c-request.json"
            input_file.write_text(json.dumps(request), encoding="utf-8")

            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-validate",
                    "--input-file",
                    str(input_file),
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        validation_report = payload["validation_report"]
        self.assertEqual(result.code, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(validation_report["accepted"])
        self.assertFalse(validation_report["validation"]["accepted"])
        self.assertNotIn("normalized_request", validation_report["validation"])
        self.assertIsNone(
            validation_report["validation"]["normalized_request_summary"]
        )
        self.assertNotIn(unsafe, result.stdout)
        self.assertNotIn(unsafe, result.stderr)

    def test_phase14c_supervised_smoke_validate_rejects_sensitive_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "oauth-request.json"
            input_file.write_text("{}", encoding="utf-8")

            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-validate",
                    "--input-file",
                    str(input_file),
                    "--json",
                ]
            )

        self.assertEqual(result.code, 1)
        self.assertIn("error:", result.stderr)
        self.assertIn("credential or authorization path", result.stderr)

    def test_phase14c_supervised_smoke_live_readiness_rejects_sensitive_input_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "oauth-request.json"
            input_file.write_text("{}", encoding="utf-8")

            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-live-readiness",
                    "--input-file",
                    str(input_file),
                    "--json",
                ]
            )

        self.assertEqual(result.code, 1)
        self.assertIn("error:", result.stderr)
        self.assertIn("credential or authorization path", result.stderr)

    def test_phase14c_supervised_smoke_credential_preflight_missing_names_only(
        self,
    ) -> None:
        with mock.patch.dict(
            os.environ,
            {"PERSONALOS_PHASE14C_TODOIST_TOKEN": "todoist-secret-value"},
            clear=True,
        ):
            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-credential-preflight",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        preflight = payload["credential_preflight"]
        self.assertEqual(result.code, 0)
        self.assertEqual(
            payload["command"],
            "phase14c supervised-smoke-credential-preflight",
        )
        self.assertEqual(payload["status"], "missing_required_config_names")
        self.assertEqual(
            payload["workflow_mode"],
            "repo-local credential-name preflight / no values / no live clients",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertEqual(
            preflight["required_config_entry_count"],
            len(REQUIRED_CONFIG_ENTRY_NAMES),
        )
        self.assertEqual(
            preflight["missing_config_entry_names"],
            [
                "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL",
                "PERSONALOS_PHASE14C_GMAIL_CREDENTIAL",
                "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS",
                "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD",
                "PHASE14C_GMAIL_CONTROLLED_RECIPIENT",
                "PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE",
            ],
        )
        self.assertFalse(preflight["all_required_config_entry_names_present"])
        self.assertTrue(preflight["reports_missing_names_only"])
        self.assertFalse(preflight["available_config_entry_names_reported"])
        self.assertFalse(preflight["credential_values_read"])
        self.assertFalse(preflight["credential_values_logged"])
        self.assertNotIn("todoist-secret-value", result.stdout)
        self.assertNotIn("PERSONALOS_PHASE14C_TODOIST_TOKEN", result.stdout)

    def test_phase14c_supervised_smoke_credential_preflight_complete_redacts_values(
        self,
    ) -> None:
        secret_environment = {
            name: f"secret-value-for-{index}"
            for index, name in enumerate(REQUIRED_CONFIG_ENTRY_NAMES)
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "supervised-smoke-credential-preflight",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        preflight = payload["credential_preflight"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "all_required_config_names_present")
        self.assertEqual(preflight["missing_config_entry_names"], [])
        self.assertTrue(preflight["all_required_config_entry_names_present"])
        self.assertFalse(preflight["available_config_entry_names_reported"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, result.stdout)
        for present_name in REQUIRED_CONFIG_ENTRY_NAMES:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_supervised_smoke_live_readiness_reports_without_execution(
        self,
    ) -> None:
        private_recipient = "private.phase14c@example.test"
        approval_reference = "approval-reference-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request(
            mode=LIVE_RUN_MODE,
            controlled_test_recipient=private_recipient,
            live_run_requested=True,
            approval_reference=approval_reference,
        )
        secret_environment = {
            name: f"secret-value-for-{index}"
            for index, name in enumerate(REQUIRED_CONFIG_ENTRY_NAMES)
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "phase14c-request.json"
            input_file.write_text(json.dumps(request), encoding="utf-8")
            with mock.patch.dict(os.environ, secret_environment, clear=True):
                result = _run_cli(
                    [
                        "phase14c",
                        "supervised-smoke-live-readiness",
                        "--input-file",
                        str(input_file),
                        "--json",
                    ]
                )

        payload = json.loads(result.stdout)
        live_readiness = payload["live_readiness"]
        validation_report = payload["validation_report"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c supervised-smoke-live-readiness")
        self.assertEqual(
            payload["status"],
            "separate_manual_live_step_prerequisites_met_not_executed",
        )
        self.assertEqual(
            payload["workflow_mode"],
            "repo-local live-readiness report / no live clients / no execution",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(validation_report["accepted"])
        self.assertNotIn("normalized_request", validation_report["validation"])
        self.assertEqual(
            validation_report["validation"]["checked_config_entry_count"],
            len(REQUIRED_CONFIG_ENTRY_NAMES),
        )
        self.assertNotIn("checked_config_entry_names", validation_report["validation"])
        self.assertEqual(payload["credential_preflight"]["missing_config_entry_names"], [])
        self.assertTrue(live_readiness["request_guardrails_accepted"])
        self.assertTrue(live_readiness["live_mode_requested"])
        self.assertTrue(live_readiness["live_run_requested"])
        self.assertTrue(live_readiness["approval_reference_present"])
        self.assertTrue(live_readiness["all_required_config_entry_names_present"])
        self.assertTrue(live_readiness["separate_manual_live_step_prerequisites_met"])
        self.assertFalse(live_readiness["ready_for_live_execution_in_this_cli"])
        self.assertFalse(live_readiness["live_run_executed"])
        self.assertFalse(live_readiness["external_mutation"])
        self.assertFalse(live_readiness["live_clients_initialized"])
        self.assertTrue(live_readiness["live_clients_required_for_future_step"])
        self.assertTrue(live_readiness["live_run_approved_flag_required_for_future_step"])
        self.assertNotIn(private_recipient, result.stdout)
        self.assertNotIn(approval_reference, result.stdout)
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, result.stdout)
        for present_name in REQUIRED_CONFIG_ENTRY_NAMES:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_supervised_smoke_live_readiness_blocks_without_echo(
        self,
    ) -> None:
        unsafe = "unsafe-live-readiness-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request(
            mode=LIVE_RUN_MODE,
            controlled_test_recipient=unsafe,
            live_run_requested=True,
            approval_reference=unsafe,
        )
        request["test_marker"] = unsafe
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "phase14c-request.json"
            input_file.write_text(json.dumps(request), encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                result = _run_cli(
                    [
                        "phase14c",
                        "supervised-smoke-live-readiness",
                        "--input-file",
                        str(input_file),
                        "--json",
                    ]
                )

        payload = json.loads(result.stdout)
        live_readiness = payload["live_readiness"]
        validation_report = payload["validation_report"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "blocked_before_live_step")
        self.assertFalse(validation_report["accepted"])
        self.assertFalse(live_readiness["request_guardrails_accepted"])
        self.assertTrue(live_readiness["live_mode_requested"])
        self.assertTrue(live_readiness["live_run_requested"])
        self.assertTrue(live_readiness["approval_reference_present"])
        self.assertFalse(live_readiness["all_required_config_entry_names_present"])
        self.assertFalse(live_readiness["separate_manual_live_step_prerequisites_met"])
        self.assertFalse(live_readiness["ready_for_live_execution_in_this_cli"])
        self.assertFalse(live_readiness["live_run_executed"])
        self.assertFalse(live_readiness["external_mutation"])
        self.assertNotIn("normalized_request", validation_report["validation"])
        self.assertIsNone(
            validation_report["validation"]["normalized_request_summary"]
        )
        self.assertNotIn(unsafe, result.stdout)
        self.assertNotIn(unsafe, result.stderr)

    def test_phase14c_openclaw_model_readiness_missing_config_names_only(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"PERSONALOS_OPENCLAW_MODEL_PROVIDER": "secret-provider-value"},
            clear=True,
        ):
            result = _run_cli(
                [
                    "phase14c",
                    "openclaw-model-readiness",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        readiness = payload["openclaw_model_readiness"]
        provider_config = readiness["provider_config"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c openclaw-model-readiness")
        self.assertEqual(payload["status"], OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG)
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertEqual(provider_config["required_config_entry_count"], 4)
        self.assertEqual(
            provider_config["missing_config_entry_names"],
            [
                "PERSONALOS_OPENCLAW_MODEL_API_KEY",
                "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
                "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
            ],
        )
        self.assertFalse(readiness["model_smoke_probe_executed"])
        self.assertTrue(provider_config["reports_missing_names_only"])
        self.assertFalse(provider_config["available_config_entry_names_reported"])
        self.assertFalse(provider_config["credential_values_read"])
        self.assertNotIn("secret-provider-value", result.stdout)
        self.assertNotIn("PERSONALOS_OPENCLAW_MODEL_PROVIDER", result.stdout)

    def test_phase14c_openclaw_model_readiness_complete_config_still_needs_client(
        self,
    ) -> None:
        secret_environment = {
            name: f"secret-model-value-for-{index}"
            for index, name in enumerate(OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES)
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "openclaw-model-readiness",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        readiness = payload["openclaw_model_readiness"]
        provider_config = readiness["provider_config"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], OPENCLAW_MODEL_SMOKE_MISSING_CLIENT)
        self.assertEqual(provider_config["missing_config_entry_names"], [])
        self.assertFalse(provider_config["available_config_entry_names_reported"])
        self.assertFalse(readiness["client"]["available"])
        self.assertFalse(readiness["model_smoke_probe_executed"])
        self.assertEqual(readiness["routing"]["primary_alias"], "nemotron_super")
        self.assertEqual(readiness["routing"]["fallback_alias"], "glm_5_2")
        for secret_value in (
            secret_environment["PERSONALOS_OPENCLAW_MODEL_API_KEY"],
            secret_environment["PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL"],
            secret_environment["PERSONALOS_OPENCLAW_GLM_5_2_MODEL"],
        ):
            self.assertNotIn(secret_value, result.stdout)
        for present_name in OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_gmail_smtp_smoke_default_is_no_send_gate(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS": "chris@example.com",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-app-password",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT": "chris@example.com",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "gmail-smtp-smoke", "--json"])

        payload = json.loads(result.stdout)
        smoke = payload["gmail_smoke"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c gmail-smtp-smoke")
        self.assertEqual(payload["status"], "gmail_not_run_missing_execute_live_flag")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertFalse(smoke["gmail_email_sent"])
        self.assertEqual(smoke["mutation_state"], "not_attempted")
        self.assertEqual(smoke["call_limits"]["email_send_calls"], 0)
        self.assertIsNone(smoke["sender_masked"])
        self.assertIsNone(smoke["recipient_masked"])
        self.assertNotIn("secret-gmail-app-password", result.stdout)
        self.assertNotIn("chris@example.com", result.stdout)
        for present_name in PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_gmail_smtp_smoke_execute_requires_approval_first(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS": "chris@example.com",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-app-password",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT": "chris@example.com",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "gmail-smtp-smoke",
                    "--execute-live",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        smoke = payload["gmail_smoke"]
        self.assertEqual(result.code, 1)
        self.assertEqual(payload["status"], "gmail_not_run_missing_approval_reference")
        self.assertFalse(smoke["gmail_email_sent"])
        self.assertEqual(smoke["call_limits"]["email_send_calls"], 0)
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertNotIn("secret-gmail-app-password", result.stdout)
        self.assertNotIn("chris@example.com", result.stdout)

    def test_phase14c_todoist_inbox_smoke_default_is_no_execute_gate(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "todoist-inbox-smoke", "--json"])

        payload = json.loads(result.stdout)
        smoke = payload["todoist_smoke"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c todoist-inbox-smoke")
        self.assertEqual(payload["status"], "todoist_not_run_missing_execute_live_flag")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertFalse(smoke["todoist_task_created"])
        self.assertEqual(smoke["call_limits"]["task_create_calls"], 0)
        self.assertEqual(
            smoke["due_date"],
            next_upcoming_monday(date.today()).isoformat(),
        )
        self.assertTrue(
            smoke["task_payload_summary"]["project_id_omitted_for_inbox_default"]
        )
        self.assertNotIn("secret-todoist-token", result.stdout)
        self.assertNotIn("PERSONALOS_PHASE14C_TODOIST_TOKEN", result.stdout)

    def test_phase14c_todoist_inbox_smoke_execute_requires_approval_first(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "todoist-inbox-smoke",
                    "--execute-live",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        smoke = payload["todoist_smoke"]
        self.assertEqual(result.code, 1)
        self.assertEqual(payload["status"], "todoist_not_run_missing_approval_reference")
        self.assertFalse(smoke["todoist_task_created"])
        self.assertEqual(smoke["call_limits"]["task_create_calls"], 0)
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertNotIn("secret-todoist-token", result.stdout)
        self.assertNotIn("PERSONALOS_PHASE14C_TODOIST_TOKEN", result.stdout)

    def test_phase14c_openrouter_model_smoke_default_is_no_provider_call(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "openrouter",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL": "secret-nemotron-model",
            "PERSONALOS_OPENCLAW_GLM_5_2_MODEL": "secret-glm-model",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "openrouter-model-smoke", "--json"])

        payload = json.loads(result.stdout)
        smoke = payload["openrouter_model_smoke"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c openrouter-model-smoke")
        self.assertEqual(
            payload["status"],
            "openclaw_model_smoke_not_run_missing_execute_live_flag",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertFalse(smoke["model_smoke_probe_executed"])
        self.assertTrue(smoke["client"]["available"])
        for secret_value in (
            secret_environment["PERSONALOS_OPENCLAW_MODEL_API_KEY"],
            secret_environment["PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL"],
            secret_environment["PERSONALOS_OPENCLAW_GLM_5_2_MODEL"],
        ):
            self.assertNotIn(secret_value, result.stdout)
        for present_name in OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES:
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_openrouter_model_smoke_execute_requires_approval_first(
        self,
    ) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "openrouter",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL": "secret-nemotron-model",
            "PERSONALOS_OPENCLAW_GLM_5_2_MODEL": "secret-glm-model",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "openrouter-model-smoke",
                    "--execute-live",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        smoke = payload["openrouter_model_smoke"]
        self.assertEqual(result.code, 1)
        self.assertEqual(
            payload["status"],
            "openclaw_model_smoke_not_run_missing_approval_reference",
        )
        self.assertFalse(smoke["model_smoke_probe_executed"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_model_provider_call"])
        for secret_value in (
            secret_environment["PERSONALOS_OPENCLAW_MODEL_API_KEY"],
            secret_environment["PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL"],
            secret_environment["PERSONALOS_OPENCLAW_GLM_5_2_MODEL"],
        ):
            self.assertNotIn(secret_value, result.stdout)

    def test_phase14c_live_smoke_diagnostics_is_no_live_report(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "secret-provider-value",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL": "secret-nemotron-model",
            "PERSONALOS_OPENCLAW_GLM_5_2_MODEL": "secret-glm-model",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "live-smoke-diagnostics", "--json"])

        payload = json.loads(result.stdout)
        diagnostics = payload["live_smoke_diagnostics"]
        todoist = diagnostics["todoist_manual_check"]
        openrouter = diagnostics["openrouter_next_probe_diagnostics"]
        safety = diagnostics["safety_assertions"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c live-smoke-diagnostics")
        self.assertEqual(payload["status"], "phase14c_live_smoke_diagnostics_ready")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertEqual(
            todoist["status"],
            "todoist_manual_outcome_check_required",
        )
        self.assertTrue(todoist["manual_check_required"])
        self.assertTrue(todoist["do_not_rerun_create_without_manual_check"])
        self.assertEqual(todoist["due_date"], "2026-07-06")
        self.assertEqual(
            openrouter["status"],
            "openrouter_next_probe_diagnostics_ready",
        )
        self.assertEqual(openrouter["new_safe_failure_fields"], [
            "error_kind",
            "http_status",
        ])
        self.assertTrue(openrouter["next_probe_requires_new_explicit_approval"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["external_mutation"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, result.stdout)
        for present_name in (
            "PERSONALOS_PHASE14C_TODOIST_TOKEN",
            *OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
        ):
            self.assertNotIn(present_name, result.stdout)

    def test_phase14c_connected_rehearsal_plan_is_no_live_report(self) -> None:
        secret_environment = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "connected-rehearsal-plan", "--json"])

        payload = json.loads(result.stdout)
        plan = payload["connected_rehearsal_plan"]
        safety = plan["safety_assertions"]
        budgets = plan["live_call_budgets"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c connected-rehearsal-plan")
        self.assertEqual(payload["status"], "phase14c_connected_rehearsal_plan_ready")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertFalse(plan["ready_for_live_execution"])
        self.assertTrue(plan["template_only_not_authorization"])
        self.assertEqual(budgets["openrouter_primary_calls"], 1)
        self.assertEqual(budgets["todoist_task_creates"], 1)
        self.assertEqual(budgets["gmail_emails_sent"], 1)
        self.assertEqual(budgets["calendar_event_creates"], 0)
        self.assertEqual(budgets["protected_openclaw_runtime_invocations"], 0)
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["todoist_task_created"])
        self.assertFalse(safety["gmail_sent_or_drafted"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertFalse(safety["protected_openclaw_runtime_called"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, result.stdout)

    def test_phase14c_connected_rehearsal_default_is_no_live_gate(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "openrouter",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL": "secret-nemotron-model",
            "PERSONALOS_OPENCLAW_GLM_5_2_MODEL": "secret-glm-model",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS": "chris@example.com",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT": "chris@example.com",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(["phase14c", "connected-rehearsal", "--json"])

        payload = json.loads(result.stdout)
        rehearsal = payload["connected_rehearsal"]
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["command"], "phase14c connected-rehearsal")
        self.assertEqual(
            payload["status"],
            "phase14c_connected_rehearsal_not_run_missing_execute_live_flag",
        )
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertFalse(payload["file_write"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_credential_values_logged"])
        self.assertTrue(payload["no_live_clients_initialized"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertEqual(rehearsal["call_limits"]["openrouter_primary_calls"], 0)
        self.assertEqual(rehearsal["call_limits"]["todoist_task_create_calls"], 0)
        self.assertEqual(rehearsal["call_limits"]["gmail_email_send_calls"], 0)
        for secret_value in _connected_rehearsal_secret_values(secret_environment):
            self.assertNotIn(secret_value, result.stdout)

    def test_phase14c_connected_rehearsal_execute_requires_exact_approval(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "openrouter",
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL": "secret-nemotron-model",
            "PERSONALOS_OPENCLAW_GLM_5_2_MODEL": "secret-glm-model",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS": "chris@example.com",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT": "chris@example.com",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            result = _run_cli(
                [
                    "phase14c",
                    "connected-rehearsal",
                    "--execute-live",
                    "--approval-reference",
                    "wrong-reference",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        rehearsal = payload["connected_rehearsal"]
        self.assertEqual(result.code, 1)
        self.assertEqual(
            payload["status"],
            "phase14c_connected_rehearsal_not_run_unapproved_reference",
        )
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_credential_values_read"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertTrue(payload["no_model_provider_call"])
        self.assertEqual(rehearsal["call_limits"]["openrouter_primary_calls"], 0)
        for secret_value in _connected_rehearsal_secret_values(secret_environment):
            self.assertNotIn(secret_value, result.stdout)

    def test_readiness_status_command_reports_default_not_ready_without_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            before = sorted(Path(temp_dir).iterdir())
            result = _run_cli(["readiness", "status", "--json"])
            after = sorted(Path(temp_dir).iterdir())

        payload = json.loads(result.stdout)
        readiness = payload["readiness"]
        operator_status = payload["operator_status"]
        self.assertEqual(result.code, 0)
        self.assertEqual(before, after)
        self.assertEqual(payload["status"], "completed")
        self.assertFalse(payload["database_write"])
        self.assertFalse(payload["file_write"])
        self.assertFalse(payload["external_mutation"])
        self.assertTrue(payload["no_external_writes"])
        self.assertTrue(payload["no_credentials_loaded"])
        self.assertTrue(payload["no_live_rails_activated"])
        self.assertEqual(readiness["status"], "not_ready")
        self.assertTrue(readiness["inert_report_only"])
        self.assertTrue(readiness["read_only"])
        self.assertFalse(readiness["live_rails_activated"])
        self.assertFalse(readiness["credentials_loaded"])
        self.assertFalse(readiness["credentials_read"])
        self.assertFalse(readiness["files_created"])
        self.assertFalse(readiness["runtime_state_mutated"])
        self.assertFalse(readiness["scheduler_activated"])
        self.assertFalse(readiness["openclaw_called"])
        self.assertFalse(readiness["production_db_path_active"])
        self.assertIn("Missing readiness config fails closed.", readiness["reasons"])
        self.assertGreater(readiness["blocked_or_missing_gate_count"], 0)
        self.assertEqual(readiness["blocked_or_non_disabled_rail_count"], 0)
        self.assertEqual(operator_status["readiness_status"], "not_ready")
        self.assertTrue(operator_status["inert_report_only"])
        self.assertFalse(operator_status["live_rails_activated"])
        self.assertEqual(operator_status["scheduler_status"]["status"], "inactive")
        self.assertEqual(operator_status["production_db_status"]["status"], "not_active")
        self.assertEqual(operator_status["credential_status"]["status"], "not_loaded")
        self.assertEqual(operator_status["external_write_status"]["status"], "none")
        self.assertIn("Run readiness report", operator_status["safe_local_actions"])
        self.assertIn("Call live model/API", operator_status["blocked_actions"])

    def test_readiness_status_command_lists_disabled_live_rails_and_gate_reasons(self) -> None:
        result = _run_cli(["readiness", "status"])

        self.assertEqual(result.code, 0)
        self.assertIn("Personal OS status: NOT READY", result.stdout)
        self.assertIn("Mode: inert / report-only", result.stdout)
        self.assertIn("Live rails: disabled", result.stdout)
        self.assertIn("Scheduler: inactive", result.stdout)
        self.assertIn("Production DB: not active", result.stdout)
        self.assertIn("Credentials: not loaded", result.stdout)
        self.assertIn("External writes: none", result.stdout)
        self.assertIn("Safe local actions:", result.stdout)
        self.assertIn("- Preview ChatGPT synthesis import", result.stdout)
        self.assertIn("Blocked until explicit Phase 14/live approval:", result.stdout)
        self.assertIn("- Send Gmail", result.stdout)
        self.assertIn("Evidence:", result.stdout)
        self.assertIn("- inert_report_only=true", result.stdout)
        self.assertIn("command: readiness status", result.stdout)
        self.assertIn("readiness_status: not_ready", result.stdout)
        self.assertIn("inert_report_only: true", result.stdout)
        self.assertIn("live_rails_activated: false", result.stdout)
        self.assertIn("Missing readiness config fails closed.", result.stdout)
        for rail in (
            "gmail",
            "todoist",
            "google_calendar",
            "personalos_markdown",
            "openclaw_runtime_workflows",
            "scheduler_launchagent_background_loop",
            "live_model_api_calls",
            "production_sqlite_state",
        ):
            with self.subTest(rail=rail):
                self.assertIn(f"{rail}: disabled, active=false", result.stdout)

    def test_status_command_works_against_temp_bootstrapped_db(self) -> None:
        with _seeded_runtime_db() as db_path:
            result = _run_cli(["status", "--db", str(db_path), "--json"])

        payload = json.loads(result.stdout)
        self.assertEqual(result.code, 0)
        self.assertEqual(payload["status"], "completed")
        self.assertFalse(payload["database_write"])
        self.assertTrue(payload["local_sqlite_read"])
        self.assertFalse(payload["local_sqlite_changed"])
        self.assertEqual(
            payload["database_target"]["path_classification"],
            "temporary_test_local_safe_db",
        )
        self.assertEqual(payload["external_writes"], "none")
        self.assertEqual(payload["credentials"], "not_loaded")
        self.assertTrue(payload["no_external_writes"])
        self.assertIn("routines", payload["summary"]["counts"])
        readiness = payload["summary"]["pre_live_readiness"]
        operator_status = payload["operator_status"]
        self.assertEqual(readiness["status"], "not_ready")
        self.assertTrue(readiness["inert_report_only"])
        self.assertTrue(readiness["no_live_rails_activated"])
        self.assertEqual(readiness["blocked_or_non_disabled_rail_count"], 0)
        self.assertEqual(operator_status["readiness_status"], "not_ready")
        self.assertEqual(
            operator_status["production_db_status"]["path_classification"],
            "temp_dev_test_sqlite",
        )
        self.assertEqual(operator_status["external_write_status"]["status"], "none")

    def test_status_command_human_output_includes_readiness_surface(self) -> None:
        with _seeded_runtime_db() as db_path:
            result = _run_cli(["status", "--db", str(db_path)])

        self.assertEqual(result.code, 0)
        self.assertIn("Workflow complete: Local status preview", result.stdout)
        self.assertIn("Mode: inert / no-send / report-only", result.stdout)
        self.assertIn("DB target: temporary/test/local safe DB", result.stdout)
        self.assertIn("Local SQLite read: yes", result.stdout)
        self.assertIn("Local SQLite changes: none", result.stdout)
        self.assertIn("External writes: none", result.stdout)
        self.assertIn("Credentials: not loaded", result.stdout)
        self.assertIn("Personal OS status: NOT READY", result.stdout)
        self.assertIn("Safe local actions:", result.stdout)
        self.assertIn("Blocked until explicit Phase 14/live approval:", result.stdout)
        self.assertIn("readiness_status: not_ready", result.stdout)
        self.assertIn("inert_report_only: true", result.stdout)
        self.assertIn("live_rails_activated: false", result.stdout)
        self.assertIn("gmail: disabled, active=false", result.stdout)

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
        self.assertIn("Blocked:", result.stdout)
        self.assertIn("- Send Gmail", result.stdout)
        self.assertIn("- Write Todoist", result.stdout)

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
            "input paths",
            "no live model/api calls",
            "no scheduler activation",
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
                (REPO_ROOT / "src" / "personalos" / "scheduler.py").read_text(
                    encoding="utf-8"
                ),
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


def _connected_rehearsal_secret_values(
    secret_environment: dict[str, str],
) -> tuple[str, ...]:
    return (
        secret_environment["PERSONALOS_OPENCLAW_MODEL_API_KEY"],
        secret_environment["PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL"],
        secret_environment["PERSONALOS_OPENCLAW_GLM_5_2_MODEL"],
        secret_environment["PERSONALOS_PHASE14C_TODOIST_TOKEN"],
        secret_environment["PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS"],
        secret_environment["PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD"],
        secret_environment["PHASE14C_GMAIL_CONTROLLED_RECIPIENT"],
    )


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

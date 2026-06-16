import json
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
from personalos.briefings import (
    BRIEFING_LOOP_READ_PERMISSION,
    BRIEFING_LOOP_RUN_PERMISSION,
    BRIEFING_LOOP_WRITE_PERMISSION,
    generate_no_send_briefing_preview,
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
    count_daily_plans,
    count_followups,
    count_priorities,
    count_routines,
    count_synthesis_import_previews,
    create_calendar_block,
    create_todoist_task,
    count_todoist_tasks,
    upsert_permission_setting,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
)
from personalos.today import create_today_view_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATE = "2026-06-15"
RUN_AT = "2026-06-15T14:00:00+00:00"


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
        self.assertEqual(summary["briefing_loop_summary"]["latest_briefing_output_count"], 0)
        self.assertEqual(summary["briefing_loop_summary"]["source_date_briefing_output_count"], 0)
        self.assertTrue(summary["briefing_loop_summary"]["no_send_mode"])
        self.assertEqual(summary["briefing_output_summary"]["source_date_briefing_output_count"], 0)
        self.assertEqual(summary["briefing_output_summary"]["source_date_daily_plan_count"], 0)
        self.assertEqual(summary["briefing_output_summary"]["latest_briefing_outputs"], [])
        self.assertEqual(summary["briefing_output_summary"]["manual_export_excerpt"], "")
        self.assertEqual(summary["briefing_output_summary"]["failed_briefing_count"], 0)
        self.assertEqual(summary["briefing_output_summary"]["warning_count"], 0)
        self.assertTrue(summary["briefing_output_summary"]["no_external_writes"])
        self.assertTrue(summary["briefing_output_summary"]["no_send_mode"])
        self.assertFalse(summary["synthesis_import_preview_summary"]["available"])
        self.assertEqual(
            summary["synthesis_import_preview_summary"]["permission_required"],
            SYNTHESIS_IMPORT_READ_PERMISSION,
        )
        self.assertGreaterEqual(summary["permission_summary"]["total_count"], 1)
        self.assertIn("counts", summary["system_status_summary"])

    def test_today_view_summary_includes_briefing_output_details(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(connection, briefing_window_name="morning")
                before_counts = _table_counts(connection)

                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )
                after_counts = _table_counts(connection)

        briefing_summary = summary["briefing_output_summary"]
        latest_output = briefing_summary["latest_briefing_outputs"][0]
        latest_report = briefing_summary["latest_completion_report_summary"]
        safety_flags = briefing_summary["safety_flags"]

        self.assertEqual(before_counts, after_counts)
        self.assertEqual(briefing_summary["source_date_briefing_output_count"], 1)
        self.assertEqual(briefing_summary["source_date_daily_plan_count"], 1)
        self.assertEqual(briefing_summary["failed_briefing_count"], 0)
        self.assertEqual(latest_output["briefing_window_name"], "morning")
        self.assertEqual(latest_output["status"], "generated")
        self.assertIn("Personal OS Morning Brief Preview", briefing_summary["manual_export_excerpt"])
        self.assertIn("No-send preview", briefing_summary["latest_manual_export_preview"])
        self.assertEqual(latest_report["status"], "generated")
        self.assertFalse(latest_report["network_called"])
        self.assertTrue(latest_report["fake_composer_adapter"])
        for flag in (
            "no_external_writes",
            "no_send_mode",
            "no_live_model_call",
            "no_todoist_writes",
            "no_calendar_writes",
            "no_gmail_send",
        ):
            with self.subTest(flag=flag):
                self.assertIs(safety_flags[flag], True)

    def test_today_view_summary_surfaces_failed_briefing_warnings(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(
                    connection,
                    briefing_window_name="evening",
                    adapter=FakeComposerAdapter(should_fail=True),
                )

                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

        briefing_summary = summary["briefing_output_summary"]
        self.assertEqual(briefing_summary["failed_briefing_count"], 1)
        self.assertGreater(briefing_summary["warning_count"], 0)
        self.assertEqual(briefing_summary["latest_briefing_outputs"][0]["status"], "failed")
        self.assertEqual(briefing_summary["latest_completion_report_summary"]["status"], "failed")
        self.assertTrue(
            any(
                "Fake Composer adapter run failed" in warning
                for warning in briefing_summary["warnings"]
            )
        )

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
        self.assertIn("Briefing Loop", html)
        self.assertIn("Briefing Outputs", html)
        self.assertIn("ChatGPT Synthesis Import Preview", html)
        self.assertIn("/synthesis-import/preview", html)
        self.assertIn("Synthesis Import Previews", html)
        self.assertIn("/today.json", html)
        self.assertIn("Permissions", html)
        self.assertIn("System Status", html)
        self.assertIn("Warnings", html)

    def test_dashboard_html_render_includes_briefing_output_preview_and_flags(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(connection, briefing_window_name="morning")

                html = dashboard.render_today_view_html_from_connection(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

        self.assertIn("Briefing Outputs", html)
        self.assertIn("Latest Manual Export Preview", html)
        self.assertIn("Personal OS Morning Brief Preview", html)
        self.assertIn("Completion Report Safety Flags", html)
        self.assertIn("no_external_writes=true", html)
        self.assertIn("no_send_mode=true", html)
        self.assertIn("no_live_model_call=true", html)
        self.assertIn("no_todoist_writes=true", html)
        self.assertIn("no_calendar_writes=true", html)
        self.assertIn("no_gmail_send=true", html)

    def test_dashboard_html_render_surfaces_failed_briefing_warning(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(
                    connection,
                    briefing_window_name="evening",
                    adapter=FakeComposerAdapter(should_fail=True),
                )

                html = dashboard.render_today_view_html_from_connection(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )

        self.assertIn("Failed briefing output warning", html)
        self.assertIn("Fake Composer adapter run failed", html)

    def test_dashboard_json_render_includes_briefing_output_summary(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(connection, briefing_window_name="midday")

            rendered_json = dashboard.render_today_view_json_from_db_path(
                db_path,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
            )

        payload = json.loads(rendered_json)
        briefing_summary = payload["briefing_output_summary"]
        self.assertEqual(briefing_summary["source_date_briefing_output_count"], 1)
        self.assertEqual(
            briefing_summary["latest_briefing_outputs"][0]["briefing_window_name"],
            "midday",
        )
        self.assertIn("Personal OS Midday Brief Preview", briefing_summary["manual_export_excerpt"])
        self.assertIs(briefing_summary["safety_flags"]["no_external_writes"], True)

    def test_dashboard_has_only_synthesis_preview_form_and_no_external_action_routes(
        self,
    ) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _insert_dashboard_fixture_rows(connection)
                _generate_no_send_briefing_output(connection, briefing_window_name="morning")
                html = dashboard.render_today_view_html_from_connection(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                ).lower()

        source = inspect.getsource(dashboard)
        buttons = re.findall(r"<button[^>]*>(.*?)</button>", html)
        self.assertEqual(buttons, ["preview import"])
        self.assertIn("<form", html)
        self.assertIn('method="post"', html)
        self.assertIn('action="/synthesis-import/preview"', html)
        self.assertNotIn("generate briefing", html)
        self.assertNotIn("apply import", html)
        self.assertNotIn("save to state", html)
        self.assertNotIn("create tasks", html)
        self.assertNotIn("write files", html)
        self.assertIn("def do_POST", source)
        self.assertIn('"/synthesis-import/preview"', source)
        for forbidden_route in ('"/apply', '"/send', '"/tasks', '"/calendar'):
            with self.subTest(forbidden_route=forbidden_route):
                self.assertNotIn(forbidden_route, source)
        self.assertNotIn("generate_no_send_briefing_preview", source)

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


class DashboardSynthesisImportPreviewTest(unittest.TestCase):
    def test_synthesis_import_form_renders_safety_fields_and_preview_button(self) -> None:
        html = dashboard.render_synthesis_import_preview_form_html()
        lowered = html.lower()

        self.assertIn("ChatGPT Synthesis Import Preview", html)
        self.assertIn("Preview-only", html)
        self.assertIn("No core state mutation", html)
        self.assertIn("No PersonalOS Markdown writes", html)
        self.assertIn("No Todoist/Calendar/Gmail writes", html)
        self.assertIn("No live model/API calls", html)
        self.assertIn('name="structured_synthesis"', html)
        self.assertIn("<textarea", lowered)
        self.assertIn('name="source_type"', html)
        self.assertIn("chatgpt_synthesis", html)
        self.assertIn("manual_structured_import", html)
        self.assertNotIn("fake_fixture", html)
        self.assertIn('name="source_reference"', html)
        self.assertIn('name="source_timestamp"', html)
        buttons = re.findall(r"<button[^>]*>(.*?)</button>", html)
        self.assertEqual(buttons, ["Preview import"])
        self.assertNotIn("Apply", buttons)
        self.assertNotIn("Save to state", buttons)
        self.assertNotIn("Create tasks", buttons)
        self.assertNotIn("Write files", buttons)
        self.assertNotIn("Send", buttons)

    def test_synthesis_import_preview_db_path_route_helper_creates_one_preview_record(
        self,
    ) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_import_permissions(connection)
                before = count_synthesis_import_previews(connection)

            result = dashboard.create_dashboard_synthesis_import_preview_from_db_path(
                db_path,
                {
                    "structured_synthesis": json.dumps(_synthesis_payload()),
                    "source_type": "chatgpt_synthesis",
                },
            )
            body = dashboard.render_synthesis_import_preview_result_html(result)

            with _sqlite_connection(db_path) as connection:
                after = count_synthesis_import_previews(connection)

        self.assertEqual(result["status"], "created")
        self.assertEqual(before, 0)
        self.assertEqual(after, 1)
        self.assertIn("Preview Result", body)
        self.assertIn("accepted candidates", body)
        self.assertIn("no_external_writes", body)
        self.assertIn("questions_for_review", body)

    def test_synthesis_import_preview_helper_renders_candidate_buckets_and_flags(self) -> None:
        payload = _synthesis_payload(
            candidates={
                **_empty_synthesis_candidates(),
                "priorities": [
                    _synthesis_priority(),
                    {
                        **_synthesis_priority(),
                        "title": "Review medium-risk synthesis item",
                        "risk_level": "medium",
                        "approval_mode": "approval_required",
                    },
                ],
                "todoist_tasks": [
                    {
                        **_synthesis_todoist(),
                        "task_title": "Buy crypto for portfolio rebalance",
                        "description": "Execute BTC allocation change.",
                    },
                    {
                        **_synthesis_todoist(),
                        "priority": 5,
                    },
                ],
                "calendar_blocks": [
                    {
                        **_synthesis_calendar(),
                        "duration_minutes": 45,
                    }
                ],
                "review_questions": [_synthesis_question()],
            }
        )

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_import_permissions(connection)
                result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": json.dumps(payload),
                        "source_type": "chatgpt_synthesis",
                    },
                )
                preview_count = count_synthesis_import_previews(connection)

        report = result["preview_report"]
        html = dashboard.render_synthesis_import_preview_result_html(result)

        self.assertEqual(result["status"], "created")
        self.assertEqual(preview_count, 1)
        self.assertEqual(len(report["accepted_candidates"]), 1)
        self.assertEqual(len(report["blocked_candidates"]), 1)
        self.assertEqual(len(report["rejected_candidates"]), 2)
        self.assertEqual(len(report["review_required_candidates"]), 1)
        self.assertEqual(len(report["questions_for_review"]), 1)
        self.assertIn("accepted candidates", html)
        self.assertIn("blocked candidates", html)
        self.assertIn("rejected candidates", html)
        self.assertIn("review-required candidates", html)
        self.assertIn("questions_for_review", html)
        self.assertIn("no_state_mutation", html)
        self.assertIn("no_personalos_writes", html)
        self.assertIn("no_todoist_writes", html)
        self.assertIn("no_calendar_writes", html)
        self.assertIn("no_gmail_send", html)
        self.assertIn("no_live_model_call", html)

    def test_synthesis_import_preview_result_escapes_untrusted_content(self) -> None:
        payload = _synthesis_payload(
            candidates={
                **_empty_synthesis_candidates(),
                "priorities": [
                    {
                        **_synthesis_priority(),
                        "title": "<script>alert(1)</script>",
                    }
                ],
            }
        )

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_import_permissions(connection)
                result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": json.dumps(payload),
                        "source_type": "chatgpt_synthesis",
                    },
                )

        html = dashboard.render_synthesis_import_preview_result_html(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_synthesis_import_preview_rejects_raw_prose_raw_notes_and_credentials(
        self,
    ) -> None:
        raw_notes_payload = json.dumps(_synthesis_payload(source_type="raw_notes"))
        credential_payload = json.dumps(
            {
                **_synthesis_payload(),
                "summary": "This includes token.json and must be rejected.",
            }
        )

        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_import_permissions(connection)
                prose_result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": "Please turn these raw notes into tasks.",
                        "source_type": "chatgpt_synthesis",
                    },
                )
                raw_notes_result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": raw_notes_payload,
                        "source_type": "chatgpt_synthesis",
                    },
                )
                credential_result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": credential_payload,
                        "source_type": "chatgpt_synthesis",
                    },
                )
                preview_count = count_synthesis_import_previews(connection)

        self.assertEqual(prose_result["status"], "rejected")
        self.assertEqual(raw_notes_result["status"], "rejected")
        self.assertEqual(credential_result["status"], "rejected")
        self.assertEqual(preview_count, 0)

    def test_synthesis_import_preview_post_fails_closed_without_write_and_preview(
        self,
    ) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": json.dumps(_synthesis_payload()),
                        "source_type": "chatgpt_synthesis",
                    },
                )
                count_without_permissions = count_synthesis_import_previews(connection)

            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
                preview_missing = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": json.dumps(_synthesis_payload()),
                        "source_type": "chatgpt_synthesis",
                    },
                )
                count_preview_missing = count_synthesis_import_previews(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn(SYNTHESIS_IMPORT_PREVIEW_PERMISSION, result["reason"])
        self.assertEqual(count_without_permissions, 0)
        self.assertEqual(preview_missing["status"], "blocked")
        self.assertIn(SYNTHESIS_IMPORT_PREVIEW_PERMISSION, preview_missing["reason"])
        self.assertEqual(count_preview_missing, 0)

    def test_synthesis_import_preview_summary_requires_read_permission(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
                _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)
                result = dashboard.create_dashboard_synthesis_import_preview(
                    connection,
                    {
                        "structured_synthesis": json.dumps(_synthesis_payload()),
                        "source_type": "chatgpt_synthesis",
                    },
                )
                blocked_summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )["synthesis_import_preview_summary"]

                _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
                readable_summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )["synthesis_import_preview_summary"]

        self.assertEqual(result["status"], "created")
        self.assertFalse(blocked_summary["available"])
        self.assertEqual(blocked_summary["synthesis_import_preview_count"], 0)
        self.assertTrue(readable_summary["available"])
        self.assertEqual(readable_summary["synthesis_import_preview_count"], 1)
        self.assertEqual(readable_summary["latest_preview_status"], "validated")
        self.assertEqual(readable_summary["latest_rejected_count"], 0)
        self.assertEqual(readable_summary["latest_blocked_count"], 0)
        self.assertEqual(readable_summary["latest_warnings_count"], 1)

    def test_dashboard_synthesis_import_smoke_keeps_core_state_deltas_zero(self) -> None:
        with _seeded_runtime_db() as db_path:
            with _sqlite_connection(db_path) as connection:
                _enable_synthesis_import_permissions(connection)
                baseline = _synthesis_import_core_counts(connection)

            result = dashboard.create_dashboard_synthesis_import_preview_from_db_path(
                db_path,
                {
                    "structured_synthesis": json.dumps(
                        _synthesis_payload(source_type="fake_fixture")
                    ),
                    "source_type": "fake_fixture",
                },
            )

            with _sqlite_connection(db_path) as connection:
                after = _synthesis_import_core_counts(connection)
                preview_count = count_synthesis_import_previews(connection)
                summary = create_today_view_summary(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                )["synthesis_import_preview_summary"]

        self.assertEqual(result["status"], "created")
        self.assertEqual(preview_count, 1)
        self.assertEqual(after, baseline)
        self.assertEqual(summary["synthesis_import_preview_count"], 1)
        self.assertEqual(summary["latest_preview_status"], "validated")

    def test_no_synthesis_import_apply_permission_exists(self) -> None:
        from personalos import synthesis_import

        permission_names = [
            name
            for name in dir(synthesis_import)
            if name.startswith("SYNTHESIS_IMPORT") and "PERMISSION" in name
        ]

        self.assertEqual(
            sorted(permission_names),
            [
                "SYNTHESIS_IMPORT_PREVIEW_PERMISSION",
                "SYNTHESIS_IMPORT_READ_PERMISSION",
                "SYNTHESIS_IMPORT_WRITE_PERMISSION",
            ],
        )


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

    def test_docs_describe_phase_10c_dashboard_briefing_boundary(self) -> None:
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
            "phase 10c dashboard briefing integration",
            "briefing outputs section",
            "manual export preview is read-only",
            "completion report safety flags",
            "no generation button",
            "no scheduler",
            "no gmail/model/todoist/calendar writes",
            "future real-content redaction",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_docs_describe_phase_11b_dashboard_synthesis_import_boundary(self) -> None:
        docs_text = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "SAFETY_POLICY.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "CODEX_WORKFLOW.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "PRD.md").read_text(encoding="utf-8"),
            ]
        ).lower()

        required_phrases = (
            "phase 11b dashboard synthesis import preview ui",
            "chatgpt synthesis import preview",
            "preview import",
            "/synthesis-import/preview",
            "synthesis_import_dev_test_write",
            "synthesis_import_dev_test_preview",
            "synthesis_import_dev_test_read",
            "only `synthesis_import_previews`",
            "no apply permission",
            "no apply/save",
            "no personalos markdown writes",
            "no todoist/calendar/gmail writes",
            "no live model/api calls",
            "localhost-only",
            "no lan/public bind relaxation",
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
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _generate_no_send_briefing_output(
    connection: sqlite3.Connection,
    *,
    briefing_window_name: str,
    adapter: FakeComposerAdapter | None = None,
) -> dict[str, object]:
    _enable_briefing_loop_permissions(connection)
    _enable_composer_permissions(connection)
    return generate_no_send_briefing_preview(
        connection,
        source_date=SOURCE_DATE,
        timezone=DEFAULT_TIMEZONE,
        briefing_window_name=briefing_window_name,
        adapter=adapter,
        run_at=RUN_AT,
    )


def _enable_briefing_loop_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, BRIEFING_LOOP_READ_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_WRITE_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_RUN_PERMISSION)


def _enable_composer_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)


def _enable_synthesis_import_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)


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


def _synthesis_import_core_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "priorities": count_priorities(connection),
        "routines": count_routines(connection),
        "followups": count_followups(connection),
        "todoist_tasks": count_todoist_tasks(connection),
        "calendar_blocks": count_calendar_blocks(connection),
        "daily_plans": count_daily_plans(connection),
        "briefing_outputs": count_briefing_outputs(connection),
    }


def _synthesis_payload(
    *,
    source_type: str = "chatgpt_synthesis",
    candidates: dict[str, list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "synthesis_import.v1",
        "source_type": source_type,
        "source_timestamp": "2026-06-15T10:00:00+00:00",
        "source_reference": "chatgpt-dashboard-thread",
        "summary": "Structured ChatGPT synthesis for dashboard preview.",
        "candidates": candidates if candidates is not None else _default_synthesis_candidates(),
        "warnings": ["Preview only; no writes."],
    }


def _empty_synthesis_candidates() -> dict[str, list[dict[str, object]]]:
    return {
        "priorities": [],
        "projects": [],
        "followups": [],
        "routine_changes": [],
        "todoist_tasks": [],
        "calendar_blocks": [],
        "clarity_notes": [],
        "review_questions": [],
    }


def _default_synthesis_candidates() -> dict[str, list[dict[str, object]]]:
    candidates = _empty_synthesis_candidates()
    candidates["priorities"] = [_synthesis_priority()]
    candidates["todoist_tasks"] = [_synthesis_todoist()]
    candidates["calendar_blocks"] = [_synthesis_calendar()]
    candidates["review_questions"] = [_synthesis_question()]
    return candidates


def _synthesis_priority() -> dict[str, object]:
    return {
        "title": "Review dashboard synthesis imports",
        "summary": "Keep dashboard imports preview-only until apply gates exist.",
        "source_type": "chatgpt_synthesis",
        "source_id": "dashboard-synth-1",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "active",
    }


def _synthesis_todoist() -> dict[str, object]:
    return {
        "task_title": "Review dashboard synthesis import preview",
        "description": "Check accepted and blocked candidates.",
        "source_type": "chatgpt_synthesis",
        "source_id": "dashboard-synth-1",
        "project": "Admin",
        "labels": ["synthesis", "dashboard"],
        "due_date_or_due_string": "2026-06-16",
        "priority": 2,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "dedupe_key": "dashboard synthesis import preview",
        "status": "proposed",
    }


def _synthesis_calendar() -> dict[str, object]:
    return {
        "title": "Review dashboard synthesis import preview",
        "description": "Self-only review block.",
        "source_type": "chatgpt_synthesis",
        "source_id": "dashboard-synth-1",
        "start_time": "2026-06-16T10:00:00-05:00",
        "end_time": "2026-06-16T10:30:00-05:00",
        "duration_minutes": 30,
        "calendar_id": "primary",
        "timezone": DEFAULT_TIMEZONE,
        "approval_mode": "auto_allowed",
        "risk_level": "low",
        "dedupe_key": "dashboard synthesis import calendar review",
        "status": "proposed",
    }


def _synthesis_question() -> dict[str, object]:
    return {
        "question": "Should Phase 11C add explicit apply gates?",
        "reason": "Phase 11B is preview-only.",
        "candidate_refs": ["todoist_tasks[0]", "calendar_blocks[0]"],
        "status": "open",
    }

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
    build_phase14c_wide_net_rehearsal_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"
README = REPO_ROOT / "README.md"


class Phase14CWideNetRehearsalTest(unittest.TestCase):
    def test_wide_net_plan_is_inert_and_bounded(self) -> None:
        plan = build_phase14c_wide_net_rehearsal_plan()

        self.assertEqual(plan["status"], "phase14c_wide_net_rehearsal_plan_ready")
        self.assertEqual(plan["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            plan["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertFalse(plan["ready_for_live_execution"])
        self.assertTrue(plan["template_only_not_authorization"])
        self.assertTrue(plan["executable_gate_available"])
        self.assertTrue(plan["calendar_bridge_scaffold_available"])
        self.assertTrue(plan["calendar_app_bridge_payload_command_available"])
        self.assertFalse(plan["calendar_client_bridge_available"])
        self.assertTrue(plan["calendar_duplicate_precheck_enforced_by_runner"])
        self.assertTrue(plan["calendar_precheck_unrecognized_response_fails_closed"])
        self.assertEqual(
            plan["preconditions"]["ssl_cert_file"],
            PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        )
        self.assertTrue(plan["preconditions"]["requires_new_explicit_live_approval"])
        self.assertTrue(
            plan["preconditions"]["requires_claude_code_audit_before_live_run"]
        )
        self.assertTrue(
            plan["preconditions"][
                "requires_google_calendar_connector_duplicate_precheck"
            ]
        )

        budgets = plan["live_call_budgets"]
        self.assertEqual(budgets["openrouter_primary_calls"], 1)
        self.assertEqual(budgets["openrouter_fallback_calls_max"], 1)
        self.assertEqual(budgets["todoist_task_creates"], 1)
        self.assertEqual(budgets["gmail_emails_sent"], 1)
        self.assertEqual(budgets["calendar_event_creates"], 1)
        self.assertEqual(budgets["protected_openclaw_runtime_invocations"], 0)
        self.assertEqual(budgets["openclaw_local_harness_invocations"], 0)
        self.assertEqual(budgets["scheduler_or_background_jobs"], 0)

        safety = plan["safety_assertions"]
        self.assertFalse(safety["live_run_executed"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["todoist_task_created"])
        self.assertFalse(safety["gmail_sent_or_drafted"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertFalse(safety["calendar_connector_called"])
        self.assertFalse(safety["protected_openclaw_runtime_called"])
        self.assertFalse(safety["dynamic_cleaning_triggered"])
        self.assertFalse(safety["broad_live_activation"])

    def test_wide_net_sequence_adds_calendar_without_model_text_dependency(self) -> None:
        plan = build_phase14c_wide_net_rehearsal_plan()
        sequence = plan["proposed_live_sequence"]

        self.assertEqual(
            [step["rail"] for step in sequence],
            ["google_calendar", "openrouter", "todoist", "gmail", "google_calendar"],
        )
        self.assertTrue(sequence[0]["duplicate_marker_precheck_required"])
        self.assertTrue(
            sequence[0]["stop_before_model_todoist_gmail_or_calendar_create_on_match"]
        )
        self.assertTrue(sequence[0]["requires_bridge_normalized_matching_event_count"])
        self.assertTrue(sequence[0]["unrecognized_precheck_response_fails_closed"])
        self.assertFalse(sequence[0]["external_mutation"])
        self.assertTrue(sequence[1]["diagnostic_only"])
        self.assertFalse(sequence[1]["external_write_dependency"])
        self.assertFalse(sequence[1]["output_policy"]["generated_text_used_for_task_or_email"])
        self.assertFalse(sequence[1]["output_policy"]["raw_provider_response_logged"])
        self.assertEqual(sequence[2]["title"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(sequence[2]["due_date_policy"], "next_upcoming_monday_at_runtime")
        self.assertEqual(sequence[3]["subject"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(sequence[3]["attachments"], 0)
        self.assertEqual(sequence[4]["title"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(sequence[4]["duration_minutes"], 15)
        self.assertEqual(sequence[4]["attendees"], 0)
        self.assertTrue(sequence[4]["duplicate_marker_precheck_required"])
        self.assertFalse(sequence[4]["conference_link"])

    def test_wide_net_plan_does_not_read_or_echo_environment(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            plan = build_phase14c_wide_net_rehearsal_plan()

        serialized = json.dumps(plan, sort_keys=True)
        self.assertTrue(plan["preconditions"]["no_env_read_by_this_plan"])
        self.assertTrue(plan["preconditions"]["no_calendar_connector_call_by_this_plan"])
        self.assertFalse(plan["preconditions"]["config_values_reported"])
        self.assertFalse(plan["preconditions"]["present_config_names_reported"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, serialized)

    def test_wide_net_approval_text_is_explicitly_bounded(self) -> None:
        plan = build_phase14c_wide_net_rehearsal_plan()
        approval_text = plan["suggested_approval_text"].lower()

        self.assertIn(PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE, approval_text)
        self.assertIn(PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE, approval_text)
        self.assertIn("one openrouter diagnostic model call", approval_text)
        self.assertIn("one todoist inbox/default task", approval_text)
        self.assertIn("one gmail controlled self-send", approval_text)
        self.assertIn("one self-only google calendar event", approval_text)
        self.assertIn(PHASE14C_WIDE_NET_REHEARSAL_MARKER.lower(), approval_text)
        self.assertIn("do not run protected openclaw runtime", approval_text)
        self.assertIn("scheduler/background", approval_text)
        self.assertIn("dynamic cleaning", approval_text)

    def test_wide_net_doc_records_bounded_plan(self) -> None:
        text = _normalized_doc_text(WIDE_NET_DOC)

        required_phrases = (
            "phase14c wide-net-rehearsal-plan --json",
            "phase14c wide-net-rehearsal --json",
            "does not read `.env.local`",
            "does not authorize or run live rails",
            "fails closed before credential values are read",
            "phase14c_wide_net_rehearsal_not_run_missing_calendar_connector_or_client",
            "phase14c wide-net-calendar-bridge-payloads --json",
            "phase14c wide-net-calendar-transcript-template --json",
            "phase14c wide-net-calendar-transcript-validate --input-file",
            "phase14c wide-net-execution-handoff --json",
            "phase14c wide-net-evidence-template --json",
            "phase14c wide-net-evidence-validate --input-file",
            "phase14c wide-net-evidence-crosscheck --calendar-transcript-file",
            "phase14c wide-net-evidence-rehearsal --json",
            "redacted evidence validator",
            "does not wire or inject a calendar client",
            "does not call the google calendar app connector",
            "template payload is not evidence",
            "expected to fail the evidence validator until a separately approved live run",
            "does not echo raw evidence",
            "oversized local evidence files before json parsing",
            "shared bounded redaction checks",
            "explicit depth and node limits",
            "sanitized calendar transcript evidence and sanitized wide-net evidence agree",
            "without echoing raw inputs",
            "marker, duplicate-precheck count, calendar event create count",
            "synthetic evidence rehearsal command",
            "without returning raw fixture payloads or producing live evidence",
            "not live evidence",
            "one openrouter diagnostic model probe",
            "one todoist inbox/default marker task",
            "one gmail controlled self-email",
            "one self-only google calendar marker event",
            "read the primary/self calendar for the exact marker",
            "diagnostic-only",
            "model text must not be used as task/email/event content",
            "calendar event creates: 1",
            "protected openclaw runtime invocations: 0",
            "phase14c-2026-07-01-wide-net-live-test",
            "[phase 14-c wide test] evening reset coordination",
            "duplicate-marker precheck",
            "precheck before model, todoist, gmail, or calendar create",
            "stop before every write if a duplicate marker exists",
            "unrecognized precheck response",
            "explicit precheck contract",
            "unrecognized precheck response shapes fail closed",
            "google calendar app connector payloads",
            "sanitized calendar connector transcripts",
            "without calling the connector or echoing raw event details",
            "if glm returns another `http_status=402`",
            "future human gate, not reusable authorization",
            "live_rails_activated` remains `false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_readme_links_wide_net_rehearsal_doc(self) -> None:
        text = _normalized_doc_text(README)

        self.assertIn("docs/phase_14c_wide_net_rehearsal.md", text)
        self.assertIn("phase14c wide-net-rehearsal-plan --json", text)
        self.assertIn("phase14c wide-net-calendar-bridge-payloads --json", text)
        self.assertIn("phase14c wide-net-calendar-transcript-template", text)
        self.assertIn("phase14c wide-net-calendar-transcript-validate", text)
        self.assertIn("phase14c wide-net-execution-handoff --json", text)
        self.assertIn("phase14c wide-net-evidence-template --json", text)
        self.assertIn("phase14c wide-net-evidence-validate --input-file", text)
        self.assertIn("phase14c wide-net-evidence-crosscheck", text)
        self.assertIn("phase14c wide-net-evidence-rehearsal", text)
        self.assertIn("one self-only calendar event", text)
        self.assertIn("unrecognized precheck response shapes", text)
        self.assertIn("oversized files before json parsing", text)
        self.assertIn("shared bounded redaction checks", text)
        self.assertIn("raw inputs", text)
        self.assertIn("synthetic sanitized inputs", text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

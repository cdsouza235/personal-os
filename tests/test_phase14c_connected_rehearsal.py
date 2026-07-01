import json
import os
import unittest
from pathlib import Path
from unittest import mock

from personalos.phase14c_connected_rehearsal import (
    PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_CONNECTED_REHEARSAL_MARKER,
    PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE,
    build_phase14c_connected_rehearsal_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTED_REHEARSAL_DOC = REPO_ROOT / "docs" / "PHASE_14C_CONNECTED_REHEARSAL.md"
README = REPO_ROOT / "README.md"


class Phase14CConnectedRehearsalTest(unittest.TestCase):
    def test_connected_rehearsal_plan_is_inert_and_bounded(self) -> None:
        plan = build_phase14c_connected_rehearsal_plan()

        self.assertEqual(plan["status"], "phase14c_connected_rehearsal_plan_ready")
        self.assertEqual(plan["marker"], PHASE14C_CONNECTED_REHEARSAL_MARKER)
        self.assertEqual(
            plan["approval_reference_to_request"],
            PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertFalse(plan["ready_for_live_execution"])
        self.assertTrue(plan["template_only_not_authorization"])
        self.assertEqual(
            plan["preconditions"]["ssl_cert_file"],
            PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE,
        )
        self.assertTrue(plan["preconditions"]["requires_new_explicit_live_approval"])
        self.assertTrue(
            plan["preconditions"]["requires_claude_code_audit_before_live_run"]
        )

        budgets = plan["live_call_budgets"]
        self.assertEqual(budgets["openrouter_primary_calls"], 1)
        self.assertEqual(budgets["openrouter_fallback_calls_max"], 1)
        self.assertEqual(budgets["todoist_task_creates"], 1)
        self.assertEqual(budgets["gmail_emails_sent"], 1)
        self.assertEqual(budgets["calendar_event_creates"], 0)
        self.assertEqual(budgets["protected_openclaw_runtime_invocations"], 0)
        self.assertEqual(budgets["scheduler_or_background_jobs"], 0)

        excluded = plan["rails_excluded"]
        self.assertTrue(excluded["google_calendar"]["excluded"])
        self.assertTrue(excluded["protected_openclaw_runtime"]["excluded"])
        safety = plan["safety_assertions"]
        self.assertFalse(safety["live_run_executed"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["todoist_task_created"])
        self.assertFalse(safety["gmail_sent_or_drafted"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertFalse(safety["protected_openclaw_runtime_called"])
        self.assertFalse(safety["broad_live_activation"])

    def test_connected_rehearsal_sequence_links_model_task_and_email(self) -> None:
        plan = build_phase14c_connected_rehearsal_plan()
        sequence = plan["proposed_live_sequence"]

        self.assertEqual([step["rail"] for step in sequence], [
            "openrouter",
            "todoist",
            "gmail",
        ])
        self.assertTrue(
            sequence[0]["fallback_allowed_only_if_primary_fails_validation"]
        )
        self.assertFalse(sequence[0]["prompt_policy"]["credential_values_in_prompt"])
        self.assertFalse(sequence[0]["prompt_policy"]["protected_paths_in_prompt"])
        self.assertFalse(sequence[0]["prompt_policy"]["full_prompt_logged"])
        self.assertFalse(sequence[0]["output_policy"]["raw_provider_response_logged"])
        self.assertEqual(sequence[1]["title"], PHASE14C_CONNECTED_REHEARSAL_MARKER)
        self.assertEqual(sequence[1]["due_date"], "2026-07-06")
        self.assertEqual(
            sequence[2]["subject"],
            PHASE14C_CONNECTED_REHEARSAL_MARKER,
        )
        self.assertEqual(sequence[2]["attachments"], 0)
        self.assertFalse(sequence[2]["reply_or_forward"])

    def test_connected_rehearsal_plan_does_not_read_or_echo_environment(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            plan = build_phase14c_connected_rehearsal_plan()

        serialized = json.dumps(plan, sort_keys=True)
        self.assertTrue(plan["preconditions"]["no_env_read_by_this_plan"])
        self.assertFalse(plan["preconditions"]["config_values_reported"])
        self.assertFalse(plan["preconditions"]["present_config_names_reported"])
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, serialized)

    def test_connected_rehearsal_approval_text_is_explicitly_bounded(self) -> None:
        plan = build_phase14c_connected_rehearsal_plan()
        approval_text = plan["suggested_approval_text"].lower()

        self.assertIn(PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE, approval_text)
        self.assertIn(PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE, approval_text)
        self.assertIn("one openrouter model call", approval_text)
        self.assertIn("one todoist inbox/default task", approval_text)
        self.assertIn("one gmail controlled self-send", approval_text)
        self.assertIn("do not run calendar", approval_text)
        self.assertIn("protected openclaw runtime", approval_text)

    def test_connected_rehearsal_doc_records_bounded_plan(self) -> None:
        text = _normalized_doc_text(CONNECTED_REHEARSAL_DOC)

        required_phrases = (
            "phase14c connected-rehearsal-plan --json",
            "phase14c connected-rehearsal --json",
            "connected-rehearsal --execute-live --approval-reference",
            "does not read `.env.local`",
            "reads environment key names only",
            "one openrouter brief",
            "one todoist inbox/default task",
            "one gmail controlled self-send",
            "calendar event creates: 0",
            "protected openclaw runtime invocations: 0",
            "ssl_cert_file=/opt/homebrew/etc/ca-certificates/cert.pem",
            "phase14c-2026-07-01-connected-rehearsal",
            "rolls a stale planned date forward to the next upcoming monday",
            "model-generated brief text",
            "stop before todoist and gmail",
            "not authorization embedded in this document or the cli report",
            "live_rails_activated` remains `false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_readme_links_connected_rehearsal_doc(self) -> None:
        text = _normalized_doc_text(README)

        self.assertIn("docs/phase_14c_connected_rehearsal.md", text)
        self.assertIn("phase14c connected-rehearsal-plan --json", text)
        self.assertIn("phase14c connected-rehearsal --json", text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_DOC = REPO_ROOT / "docs" / "PHASE_14C_SUPERVISED_SMOKE_TEST.md"
CONNECTIVITY_DOC = REPO_ROOT / "docs" / "PHASE_14C_CONNECTIVITY_READINESS.md"


class Phase14CSupervisedSmokeDocsTest(unittest.TestCase):
    def test_runbook_records_source_contract_and_cli(self) -> None:
        text = _normalized_doc_text(SMOKE_DOC)

        required_phrases = (
            "src/personalos/phase14c_supervised_smoke.py",
            "build_phase14c_supervised_smoke_runbook",
            "build_default_phase14c_supervised_smoke_request",
            "build_phase14c_supervised_live_smoke_status",
            "build_phase14c_gmail_self_send_readiness_report",
            "build_phase14c_gmail_self_send_smoke_request",
            "resolve_phase14c_todoist_due_date",
            "run_phase14c_openclaw_local_sandbox_smoke",
            "build_phase14c_supervised_smoke_request_template_report",
            "build_phase14c_credential_preflight_report",
            "build_phase14c_supervised_smoke_request_validation_report",
            "validate_phase14c_supervised_smoke_request",
            "execute_phase14c_supervised_smoke_request",
            "run_phase14c_supervised_smoke_dry_run_rehearsal",
            "src/personalos/phase14c_wide_net_rehearsal.py",
            "build_phase14c_wide_net_rehearsal_plan",
            "personalos.cli phase14c supervised-smoke-runbook --json",
            "personalos.cli phase14c supervised-smoke-request-template",
            "personalos.cli phase14c supervised-smoke-validate --input-file",
            "personalos.cli phase14c supervised-smoke-credential-preflight --json",
            "personalos.cli phase14c supervised-smoke-live-readiness --input-file",
            "personalos.cli phase14c supervised-smoke-dry-run --output-dir",
            "personalos.cli phase14c openclaw-model-readiness --json",
            "personalos.cli phase14c gmail-smtp-smoke --json",
            "personalos.cli phase14c todoist-inbox-smoke --json",
            "personalos.cli phase14c openrouter-model-smoke --json",
            "personalos.cli phase14c live-smoke-diagnostics --json",
            "personalos.cli phase14c connected-rehearsal-plan --json",
            "personalos.cli phase14c connected-rehearsal --json",
            "personalos.cli phase14c wide-net-rehearsal-plan --json",
            "does not load credentials",
            "does not initialize live clients",
            "does not initialize a model client",
            "request-template report",
            "template_only_not_authorization",
            "redacted validation report",
            "redacted missing-name report",
            "redacted live-readiness report",
            "must not include raw `normalized_request`",
            "raw controlled test recipients",
            "present non-required environment names",
            "ready_for_live_execution_in_this_cli",
            "live_run_executed=false",
            "fake-client dry-run rehearsal",
            "request.json",
            "validation.json",
            "fake_client_results.json",
            "completion_report.json",
            "summary.md",
            "executor reports",
            "must not include a raw `normalized_request` payload",
            "direct in-memory validation may still retain normalized data",
            "one supervised google calendar external write has already passed",
            "memu6fhql6stl71auv05e1a6d0",
            "gmail self-send readiness",
            "todoist defaults to inbox/default",
            "run_phase14c_openclaw_local_sandbox_smoke",
            "openclaw model lane strategy",
            "nemotron super primary with glm 5.2 fallback",
            "glm 5.2 primary with nemotron super fallback",
            "openclaw_model_smoke_not_run_missing_provider_config",
            "openclaw_model_smoke_not_run_missing_client",
            "openclaw_model_smoke_passed",
            "openclaw_model_smoke_validation_failed",
            "todoist_not_run_missing_execute_live_flag",
            "gmail_not_run_missing_execute_live_flag",
            "openclaw_model_smoke_not_run_missing_execute_live_flag",
            "one openrouter diagnostic model probe",
            "one self-only google calendar marker event",
            "model-generated text must not be used as task/email/event content",
            "no executable live runner in this packet",
            "mutation_state=unconfirmed_after_task_create_attempt",
            "mutation_state=unconfirmed_after_send_attempt",
            "due_date",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_records_remaining_live_smoke_evidence(self) -> None:
        text = _normalized_doc_text(SMOKE_DOC)

        required_phrases = (
            "phase14c-2026-06-30-connectivity-live-smoke",
            "gmail smtp self-send passed with `gmail_self_send_smoke_passed`",
            "masked sender `c***@gmail.com`",
            "masked recipient `c***@gmail.com`",
            "todoist inbox/default made exactly one create attempt",
            "todoist_inbox_default_task_smoke_failed",
            "do not rerun todoist without a new explicit duplicate-risk approval",
            "openrouter returned `openclaw_model_smoke_validation_failed`",
            "transport_or_parse_error",
            "approved primary/fallback call budget is exhausted",
            "phase14c-2026-06-30-connectivity-ca-retry",
            "ssl_cert_file=/opt/homebrew/etc/ca-certificates/cert.pem",
            "manual todoist outcome check after the first remaining-rail run returned `not_found`",
            "todoist_inbox_default_task_smoke_passed",
            "mutation_state=confirmed_task_created",
            "openclaw_model_smoke_passed",
            "fallback_calls=0",
            "one controlled gmail smtp self-send passed",
            "one first-run todoist inbox/default create attempt was unconfirmed",
            "one first-run openrouter primary/fallback model smoke failed validation",
            "one separately approved ca-bundle todoist retry created the bounded inbox/default task",
            "one separately approved ca-bundle openrouter retry passed on the nemotron super primary call",
            "phase14c live-smoke-diagnostics",
            "phase_14c_connected_rehearsal.md",
            "model-to-task-to-email rehearsal",
            "phase14c connected-rehearsal",
            "exact approval reference",
            "phase14c-2026-07-01-connected-rehearsal",
            "phase14c_connected_rehearsal_model_validation_failed",
            "todoist_task_create_calls=0",
            "gmail_email_send_calls=0",
            "protected_openclaw_runtime_invocation_calls=0",
            "error_kind",
            "http_status",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_records_allowed_bounded_rails(self) -> None:
        text = _normalized_doc_text(SMOKE_DOC)

        required_phrases = (
            "[phase 14-c test] clean kitchen countertops and stovetop",
            "todoist",
            "google calendar",
            "gmail",
            "openclaw",
            "not categorically blocked",
            "allowed only inside this bounded manually supervised test envelope",
            "1 task",
            "1 event",
            "1 email",
            "1 invocation",
            "gmail_not_run_missing_sender_or_controlled_recipient",
            "phase14c_smoke_test",
            "openclaw_local_harness_passed",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_records_guardrails_and_credential_boundary(self) -> None:
        text = _normalized_doc_text(SMOKE_DOC)

        required_phrases = (
            "max one todoist task",
            "max one calendar event",
            "max one gmail email",
            "max one openclaw invocation",
            "required test marker",
            "no calendar attendees/invites except the self test identity",
            "no calendar recurrence",
            "no gmail to uncontrolled recipients",
            "no gmail cc or bcc",
            "no gmail attachments",
            "no gmail forwarding",
            "no gmail reply to an existing real thread",
            "no scheduler/background loop",
            "no production db",
            "no dynamic cleaning",
            "no bulk writes",
            "no protected path access",
            "no broad openclaw runtime handoff",
            "reports may include missing names",
            "reports must not include credential values",
            "openclaw invocation name must be `phase14c_smoke_test`",
            "openclaw production operation, scheduler/background behavior, and external mutation must remain false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_is_linked_from_current_surfaces(self) -> None:
        runbook_link = "PHASE_14C_SUPERVISED_SMOKE_TEST.md"
        related_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "LIVE_RAIL_ACTIVATION_POLICY.md",
            REPO_ROOT / "docs" / "OPENCLAW_MODEL_STRATEGY.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(runbook_link, path.read_text(encoding="utf-8"))

    def test_connectivity_doc_records_live_smoke_evidence(self) -> None:
        text = _normalized_doc_text(CONNECTIVITY_DOC)

        required_phrases = (
            "phase14c-2026-06-30-connectivity-live-smoke",
            "gmail_self_send_smoke_passed",
            "sender masked: `c***@gmail.com`",
            "recipient masked: `c***@gmail.com`",
            "todoist_inbox_default_task_smoke_failed",
            "unconfirmed_after_task_create_attempt",
            "do not rerun this rail without a new explicit duplicate-risk approval",
            "openclaw_model_smoke_validation_failed",
            "primary_calls=1",
            "fallback_calls=1",
            "transport_or_parse_error",
            "phase14c-2026-06-30-connectivity-ca-retry",
            "ssl_cert_file=/opt/homebrew/etc/ca-certificates/cert.pem",
            "todoist_inbox_default_task_smoke_passed",
            "confirmed_task_created",
            "openclaw_model_smoke_passed",
            "fallback_calls=0",
            "do not rerun any of those three live commands",
            "do not rerun either ca-bundle live command without a new explicit approval",
            "phase14c-2026-07-01-connected-rehearsal",
            "phase14c_connected_rehearsal_model_validation_failed",
            "failure_category=http_error",
            "todoist_task_create_calls=0",
            "gmail_email_send_calls=0",
            "protected_openclaw_runtime_invocation_calls=0",
            "do not rerun this connected rehearsal command without a new explicit",
            "exactly one gmail email was sent and accepted by gmail smtp",
            "exactly one ca-bundle todoist retry task was created",
            "exactly one ca-bundle openrouter retry primary call was made",
            "exactly one connected rehearsal nemotron super primary call",
            "live-smoke follow-up diagnostics",
            "manual todoist outcome check",
            "`error_kind`",
            "`http_status`",
            "phase14c wide-net-rehearsal-plan --json",
            "one openrouter diagnostic model probe",
            "one self-only google calendar marker event",
            "has no executable live runner in this packet",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

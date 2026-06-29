import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_DOC = REPO_ROOT / "docs" / "PHASE_14C_SUPERVISED_SMOKE_TEST.md"


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
            "personalos.cli phase14c supervised-smoke-runbook --json",
            "personalos.cli phase14c supervised-smoke-request-template",
            "personalos.cli phase14c supervised-smoke-validate --input-file",
            "personalos.cli phase14c supervised-smoke-credential-preflight --json",
            "personalos.cli phase14c supervised-smoke-live-readiness --input-file",
            "personalos.cli phase14c supervised-smoke-dry-run --output-dir",
            "personalos.cli phase14c openclaw-model-readiness --json",
            "personalos.cli phase14c todoist-inbox-smoke --json",
            "personalos.cli phase14c openrouter-model-smoke --json",
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
            "todoist_not_run_missing_execute_live_flag",
            "openclaw_model_smoke_not_run_missing_execute_live_flag",
            "mutation_state=unconfirmed_after_task_create_attempt",
            "due_date",
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


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

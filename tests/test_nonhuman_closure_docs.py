import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLOSURE_DOC = REPO_ROOT / "docs" / "NON_HUMAN_CLOSURE_PLAN.md"


class NonhumanClosureDocsTest(unittest.TestCase):
    def test_closure_doc_records_source_contract(self) -> None:
        text = _normalized_doc_text(CLOSURE_DOC)

        required_phrases = (
            "src/personalos/nonhuman_closure.py",
            "build_nonhuman_closure_plan_report",
            "validate_nonhuman_closure_plan_report_contract",
            "nonhuman_closure_schema_version",
            "nonhuman_closure_status",
            "nonhuman_closure_top_level_fields",
            "nonhuman_closure_packet_plan",
            "human_required_gates",
            "blocked_live_rails",
            "non_authorization_false_fields",
            "the builder accepts no caller input",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_closure_doc_records_accelerated_packet_model(self) -> None:
        text = _normalized_doc_text(CLOSURE_DOC)

        required_phrases = (
            "three to five large packets",
            "each followed by claude code read-only audit",
            "mvp readiness gap report",
            "non-human closure plan",
            "weekend test readiness runbook",
            "dry-run evidence bundle",
            "final non-human handoff",
            "wide-net blocked gate summary",
            "exact human gate checklist",
            "`claude_code_audit_required=true`",
            "`contains_human_decision=false`",
            "`contains_live_access=false`",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_closure_doc_preserves_blocked_human_gate_posture(self) -> None:
        text = _normalized_doc_text(CLOSURE_DOC)

        required_phrases = (
            "`status=blocked_by_human_gates`",
            "`nonhuman_closure_complete=false`",
            "`live_mvp_ready=false`",
            "`human_gates_remaining=true`",
            "`readiness.status=not_ready`",
            "`inert_report_only=true`",
            "`live_rails_activated=false`",
            "`wide_net_rollup_contract_valid=true`",
            "`wide_net_ready_for_live_execution=false`",
            "`wide_net_live_run_authorized_by_this_report=false`",
            "`wide_net_calendar_cli_connector_wiring_present=false`",
            "`wide_net_credential_values_read=false`",
            "`wide_net_external_mutation=false`",
            "`wide_net_readiness_status=not_ready`",
            "`wide_net_live_rails_activated=false`",
            "status evidence only",
            "do not authorize the future wide-net live run",
            "it never emits ready, approved, authorized, activated, executed, or live status",
            "candidate approval remains a separate human decision",
            "phase 14-c authorization remains a separate human decision",
            "actual live-service testing remains a separate human-gated activity",
            "go/no-go launch approval remains a separate human decision",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_closure_doc_lists_blocked_rails_and_non_authorization(self) -> None:
        text = _normalized_doc_text(CLOSURE_DOC)
        raw_text = CLOSURE_DOC.read_text(encoding="utf-8").lower()

        required_phrases = (
            "gmail",
            "todoist",
            "google calendar",
            "personalos markdown",
            "openclaw",
            "credentials",
            "production db",
            "scheduler/background",
            "live model/api",
            "protected paths",
            "dynamic cleaning",
            "watch tower",
            "`.agent`",
            "`claude.md`",
            "runtime/operator scaffolding",
            "`repo_merge_is_not_live_authorization=true`",
            "`nonhuman_closure_is_not_product_approval=true`",
            "this document records the accelerated codex/fable + claude code operating plan",
            "does not approve phase 14-c",
            "does not approve a candidate",
            "authorize live-service access",
            "calendar app connector use",
            "handle credentials",
            "activate production db",
            "invoke openclaw",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("live_mvp_ready=true", raw_text)
        self.assertNotIn("candidate_approved=true", raw_text)
        self.assertFalse((REPO_ROOT / ".agent").exists())
        self.assertFalse((REPO_ROOT / "CLAUDE.md").exists())

    def test_closure_doc_is_linked_from_core_docs(self) -> None:
        closure_link = "NON_HUMAN_CLOSURE_PLAN.md"
        related_docs = (
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "CODEX_WORKFLOW.md",
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(closure_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DOC = REPO_ROOT / "docs" / "FINAL_NONHUMAN_HANDOFF.md"


class FinalNonhumanHandoffDocsTest(unittest.TestCase):
    def test_handoff_doc_records_source_contract(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)

        required_phrases = (
            "src/personalos/final_nonhuman_handoff.py",
            "build_final_nonhuman_handoff_report",
            "validate_final_nonhuman_handoff_report_contract",
            "final_nonhuman_handoff_schema_version",
            "final_nonhuman_handoff_status",
            "final_nonhuman_handoff_top_level_fields",
            "final_nonhuman_closure_packet_statuses",
            "nonhuman_closure_payload_fields",
            "wide_net_human_gate_packet_payload_fields",
            "human_gate_checklist",
            "next_human_work_plan",
            "non_authorization_false_fields",
            "the builder accepts no caller input",
            "it never emits ready, approved, authorized, activated, executed, or live status",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_handoff_doc_records_inert_default_posture(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)
        raw_text = HANDOFF_DOC.read_text(encoding="utf-8").lower()

        required_phrases = (
            "`status=nonhuman_handoff_recorded_human_gates_remain`",
            "`safe_nonhuman_packet_artifacts_complete=true`",
            "`final_packet_claude_code_audit_passed=true`",
            "`live_mvp_ready=false`",
            "`human_gates_remaining=true`",
            "`readiness.status=not_ready`",
            "`inert_report_only=true`",
            "`live_rails_activated=false`",
            "does not approve phase 14-c",
            "does not approve a candidate",
            "does not authorize live-service access",
            "does not start live-service testing",
            "does not handle credentials",
            "does not activate production db",
            "does not invoke openclaw",
            "does not make a go/no-go launch decision",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("live_mvp_ready=true", raw_text)
        self.assertNotIn("candidate_approved=true", raw_text)
        self.assertNotIn("live_testing_authorized=true", raw_text)

    def test_handoff_doc_records_packet_and_dry_run_boundaries(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)

        required_phrases = (
            "mvp readiness gap report",
            "non-human closure plan",
            "weekend test readiness runbook",
            "dry-run evidence bundle",
            "final non-human handoff",
            "merged on `main` after claude code audit",
            "`claude_code_audit_required=true`",
            "`contains_human_decision=false`",
            "`contains_live_access=false`",
            "`status=dry_run_contract_recorded_not_live`",
            "`contract_valid=true`",
            "`dry_run_execution_started=false`",
            "`repo_evidence_bundle_written=false`",
            "`temp_only_smoke_supported=true`",
            "does not execute the dry run",
            "does not write a repo evidence bundle by default",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_handoff_doc_records_nonhuman_closure_wide_net_boundaries(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)

        required_phrases = (
            "non-human closure and wide-net summary",
            "`status=blocked_by_human_gates`",
            "`contract_valid=true`",
            "`nonhuman_closure_complete=false`",
            "`wide_net_rollup_contract_valid=true`",
            "`wide_net_ready_for_live_execution=false`",
            "`wide_net_live_run_authorized_by_this_report=false`",
            "`wide_net_calendar_cli_connector_wiring_present=false`",
            "`wide_net_calendar_operator_packet_available=true`",
            "`wide_net_calendar_operator_packet_contract_valid=true`",
            "`wide_net_credential_values_read=false`",
            "`wide_net_external_mutation=false`",
            "`wide_net_readiness_status=not_ready`",
            "`wide_net_live_rails_activated=false`",
            "blocked-status evidence only",
            "do not authorize the future wide-net live run",
            "calendar app connector use",
            "credential handling",
            "external mutation",
            "any live-service call",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_handoff_doc_records_wide_net_human_gate_packet_boundaries(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)

        required_phrases = (
            "wide-net human-gate packet summary",
            "`ready_for_live_execution=false`",
            "`wide_net_live_run_authorized_by_this_report=false`",
            "`human_live_approval_still_required=true`",
            "`claude_code_audit_required_before_live_run=true`",
            "`calendar_cli_connector_wiring_present=false`",
            "`credential_values_read=false`",
            "`external_mutation=false`",
            "`approval_request_template_is_not_approval=true`",
            "`fresh_human_message_required=true`",
            "phase14c wide-net-human-gate-packet --json",
            "phase14c wide-net-human-gate-packet-contract --json",
            "approval request template is not approval",
            "does not clear any human gate by itself",
            "calendar connector wiring remains required",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_handoff_doc_records_human_gates_and_non_authorization(self) -> None:
        text = _normalized_doc_text(HANDOFF_DOC)

        required_phrases = (
            "candidate approval remains a separate human decision",
            "phase 14-c authorization remains a separate human decision",
            "live-service access remains a separate human decision",
            "credential/auth handling remains a separate human decision",
            "production db activation remains a separate human decision",
            "scheduler/background activation remains a separate human decision",
            "openclaw handoff or invocation remains a separate human decision",
            "actual live-service testing remains a separate human-gated activity",
            "go/no-go launch approval remains a separate human decision",
            "`status=pending_human_decision`",
            "`blocked_until_human_decision=true`",
            "`live_action_allowed_by_this_report=false`",
            "`credential_access_allowed_by_this_report=false`",
            "`handoff_is_not_live_authorization=true`",
            "`repo_merge_is_not_live_authorization=true`",
            "`safe_nonhuman_completion_is_not_product_approval=true`",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_handoff_doc_is_linked_from_core_docs(self) -> None:
        handoff_link = "FINAL_NONHUMAN_HANDOFF.md"
        related_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "NON_HUMAN_CLOSURE_PLAN.md",
            REPO_ROOT / "docs" / "DRY_RUN_EVIDENCE_BUNDLE.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(handoff_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

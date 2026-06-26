import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_DOC = REPO_ROOT / "docs" / "WEEKEND_TEST_READINESS_RUNBOOK.md"


class WeekendTestReadinessDocsTest(unittest.TestCase):
    def test_runbook_doc_records_source_contract(self) -> None:
        text = _normalized_doc_text(RUNBOOK_DOC)

        required_phrases = (
            "src/personalos/weekend_test_readiness.py",
            "build_weekend_test_readiness_report",
            "validate_weekend_test_readiness_report_contract",
            "weekend_test_readiness_schema_version",
            "weekend_test_readiness_status",
            "weekend_test_readiness_top_level_fields",
            "source_documents",
            "manual_test_categories",
            "evidence_templates",
            "no_go_criteria",
            "rollback_rehearsal_templates",
            "non_authorization_false_fields",
            "the builder accepts no caller input",
            "it never emits ready, approved, authorized, activated, executed, or live status",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_doc_records_source_documents_and_test_categories(self) -> None:
        text = _normalized_doc_text(RUNBOOK_DOC)

        required_phrases = (
            "pre_live_readiness.md",
            "activation_checklist.md",
            "first_live_pilot_protocol.md",
            "live_rail_activation_policy.md",
            "operator_handoff_contract.md",
            "non_human_closure_plan.md",
            "repo validation capture",
            "readiness status capture",
            "activation checklist review",
            "first-live pilot protocol review",
            "live rail policy review",
            "operator handoff boundary review",
            "no-go and halt review",
            "rollback tabletop review",
            "`contains_human_decision=false`",
            "`contains_live_access=false`",
            "`credentials_required=false`",
            "`production_db_required=false`",
            "`scheduler_required=false`",
            "`openclaw_required=false`",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_doc_preserves_non_live_readiness_posture(self) -> None:
        text = _normalized_doc_text(RUNBOOK_DOC)
        raw_text = RUNBOOK_DOC.read_text(encoding="utf-8").lower()

        required_phrases = (
            "`status=test_plan_recorded_not_live`",
            "`weekend_testing_started=false`",
            "`live_testing_authorized=false`",
            "`live_mvp_ready=false`",
            "`human_gates_remaining=true`",
            "`inert_report_only=true`",
            "`readiness.status=not_ready`",
            "`live_rails_activated=false`",
            "does not start weekend testing",
            "does not authorize live-service testing",
            "does not approve phase 14-c",
            "does not approve a candidate",
            "does not authorize a candidate",
            "does not activate production db",
            "does not activate scheduler/background behavior",
            "does not invoke openclaw",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("live_testing_authorized=true", raw_text)
        self.assertNotIn("weekend_testing_started=true", raw_text)
        self.assertNotIn("live_mvp_ready=true", raw_text)

    def test_runbook_doc_records_evidence_no_go_and_rollback_boundaries(self) -> None:
        text = _normalized_doc_text(RUNBOOK_DOC)

        required_phrases = (
            "validation evidence",
            "readiness evidence",
            "dry-run preview evidence",
            "rollback tabletop evidence",
            "`captures_secret_values=false`",
            "`records_live_object_ids=false`",
            "`authorizes_live_access=false`",
            "any credential, oauth token, api key, or secret handling is required",
            "any production db path is needed or inferred",
            "any scheduler, launchagent, crontab, daemon, watcher, or background loop is needed",
            "openclaw handoff or invocation is requested without a separate approved handoff",
            "go/no-go launch approval is missing",
            "todoist rollback",
            "google calendar rollback",
            "gmail draft recovery",
            "production db restore",
            "`rehearsal_only=true`",
            "`live_action_authorized=false`",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runbook_doc_is_linked_from_core_docs(self) -> None:
        runbook_link = "WEEKEND_TEST_READINESS_RUNBOOK.md"
        related_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "NON_HUMAN_CLOSURE_PLAN.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(runbook_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MVP_DOC = REPO_ROOT / "docs" / "MVP_READINESS_GAP_REPORT.md"


class MvpReadinessDocsTest(unittest.TestCase):
    def test_mvp_readiness_doc_records_source_contract(self) -> None:
        text = _normalized_doc_text(MVP_DOC)

        required_phrases = (
            "src/personalos/mvp_readiness.py",
            "build_mvp_readiness_gap_report",
            "validate_mvp_readiness_gap_report_contract",
            "mvp_readiness_schema_version",
            "mvp_readiness_status",
            "mvp_readiness_top_level_fields",
            "completed_inert_capabilities",
            "pending_human_decisions",
            "blocked_live_rails",
            "non_authorization_false_fields",
            "the builder accepts no caller input",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_mvp_readiness_doc_preserves_not_ready_posture(self) -> None:
        text = _normalized_doc_text(MVP_DOC)

        required_phrases = (
            "`readiness.status=not_ready`",
            "`inert_report_only=true`",
            "`live_rails_activated=false`",
            "`live_mvp_ready=false`",
            "`candidate_review_tracking_only=true`",
            "`phase14_c_blocked=true`",
            "it never emits ready, approved, authorized, activated, or executed status",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_mvp_readiness_doc_lists_pending_human_decisions_and_blocked_rails(
        self,
    ) -> None:
        text = _normalized_doc_text(MVP_DOC)

        required_phrases = (
            "candidate approval remains a separate human decision",
            "phase 14-c authorization remains a separate human decision",
            "live-service access remains a separate human decision",
            "credential/auth handling remains a separate human decision",
            "production db activation remains a separate human decision",
            "scheduler/background activation remains a separate human decision",
            "openclaw handoff or invocation remains a separate human decision",
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
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_mvp_readiness_doc_is_non_authorizing(self) -> None:
        text = _normalized_doc_text(MVP_DOC)
        raw_text = MVP_DOC.read_text(encoding="utf-8").lower()

        required_phrases = (
            "these entries are blockers, not grants",
            "a repo merge is not live authorization",
            "this packet does not approve phase 14-c",
            "approve a candidate",
            "authorize a candidate",
            "activate or run a candidate",
            "authorize live service access",
            "handle credentials",
            "activate production db",
            "activate scheduler/background behavior",
            "invoke openclaw",
            "touch protected paths",
            "implement dynamic cleaning",
            "adopt watch tower",
            "add `.agent/`",
            "add `claude.md`",
            "add runtime/operator scaffolding",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("live_mvp_ready=true", raw_text)
        self.assertNotIn("candidate_approved=true", raw_text)
        self.assertFalse((REPO_ROOT / ".agent").exists())
        self.assertFalse((REPO_ROOT / "CLAUDE.md").exists())

    def test_mvp_readiness_doc_is_linked_from_core_docs(self) -> None:
        mvp_link = "MVP_READINESS_GAP_REPORT.md"
        related_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(mvp_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

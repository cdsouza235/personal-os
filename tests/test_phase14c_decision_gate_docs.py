import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = REPO_ROOT / "docs" / "PHASE_14C_DECISION_GATE.md"


class Phase14CDecisionGateDocsTest(unittest.TestCase):
    def test_gate_records_candidate_context_without_approval(self) -> None:
        text = _normalized_doc_text(GATE_DOC)

        required_phrases = (
            "clean kitchen countertops and stovetop",
            "weekday: `monday`",
            "area: `kitchen`",
            "status: candidate-review tracking only",
            "candidate is not approved",
            "candidate is not authorized",
            "candidate is not activated or run",
            "phase 14-c remains blocked",
            "future explicit human approval",
            "does not authorize execution",
            "does not authorize live service access",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_gate_preserves_non_live_non_runtime_exclusions(self) -> None:
        text = _normalized_doc_text(GATE_DOC)

        required_phrases = (
            "no todoist/gmail/calendar/openclaw access",
            "no credentials",
            "no production db",
            "no scheduler/background/daemon/service activation",
            "no dynamic cleaning implementation",
            "no 15-task cleaning import",
            "no skip/push/bump behavior",
            "no automatic rescheduling",
            "no watch tower adoption",
            "no `.agent/`",
            "no `claude.md`",
            "no runtime/operator scaffolding",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertFalse((REPO_ROOT / ".agent").exists())
        self.assertFalse((REPO_ROOT / "CLAUDE.md").exists())

    def test_decision_record_template_defaults_to_unfilled_and_false(self) -> None:
        text = _normalized_doc_text(GATE_DOC)

        required_phrases = (
            "this template is inert and unfilled by default",
            "it does not approve anything",
            "decision_status: unfilled",
            "decision_option: unselected",
            "allowed_next_packet: none",
            "phase14_c_approved: false",
            "candidate_approved: false",
            "candidate_authorized: false",
            "candidate_activated_or_run: false",
            "candidate_execution_authorized: false",
            "todoist_access_authorized: false",
            "todoist_write_authorized: false",
            "openclaw_handoff_or_invocation_authorized: false",
            "runtime_operator_scaffolding_authorized: false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_gate_is_linked_from_related_phase_docs(self) -> None:
        gate_link = "PHASE_14C_DECISION_GATE.md"
        related_docs = (
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "PHASE_14_CANDIDATE_SELECTION_PREP.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(gate_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

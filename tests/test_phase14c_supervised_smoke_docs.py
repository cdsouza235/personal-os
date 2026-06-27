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
            "build_phase14c_credential_preflight_report",
            "validate_phase14c_supervised_smoke_request",
            "execute_phase14c_supervised_smoke_request",
            "personalos.cli phase14c supervised-smoke-runbook --json",
            "does not load credentials",
            "does not initialize live clients",
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
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(runbook_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

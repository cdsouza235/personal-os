import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexWorkflowDocsTest(unittest.TestCase):
    def test_agents_prefers_larger_bounded_packets_without_watch_tower(self) -> None:
        text = _normalized_doc_text(REPO_ROOT / "AGENTS.md")

        required_phrases = (
            "prefer larger bounded work packets",
            "repo-local, inert, testable",
            "multiple approved repo-local substeps",
            "not watch tower adoption",
            "does not authorize `.agent/`",
            "`claude.md`",
            "scheduler/background activation",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_codex_workflow_records_long_run_gates_and_reports(self) -> None:
        text = _normalized_doc_text(REPO_ROOT / "docs" / "CODEX_WORKFLOW.md")

        required_phrases = (
            "mandatory stop gates",
            "live gmail/todoist/calendar writes",
            "credential/api/oauth/secrets/token handling",
            "production db activation",
            "protected path access",
            "openclaw runtime handoff or invocation",
            "launchagent, crontab, daemon, watcher, or service changes",
            "major product direction choices",
            "merge approval",
            "any test failure requiring architectural or product judgment",
            "real human gates",
            "acceptable larger packets",
            "scope completed",
            "subphases completed",
            "validation commands and results",
            "safety assertions",
            "deviations",
            "open questions",
            "next human decision required",
            "human-review excerpt",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_packet_protocol_preserves_non_live_non_watch_tower_boundary(self) -> None:
        text = _normalized_doc_text(
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md"
        )

        required_phrases = (
            "this protocol is not watch tower adoption",
            "does not authorize `.agent/`",
            "`claude.md`",
            "runtime/operator scaffolding",
            "live todoist/gmail/calendar access",
            "credential handling",
            "scheduler/background activation",
            "real human gates",
            "scope completed",
            "test counts",
            "human-review excerpt",
            "what approval or merge would not mean",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

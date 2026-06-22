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
            "claude code audit recommendation",
            "required / recommended / not needed",
            "if codex/fable says audit is not needed, it must explain why",
            "must stop after opening the pr and must not merge",
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

    def test_pr_opening_reports_require_claude_audit_recommendation(self) -> None:
        agents_text = _normalized_doc_text(REPO_ROOT / "AGENTS.md")
        workflow_text = _normalized_doc_text(REPO_ROOT / "docs" / "CODEX_WORKFLOW.md")
        protocol_text = _normalized_doc_text(
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md"
        )

        required_phrases = (
            "claude code audit recommendation",
            "required",
            "recommended",
            "not needed",
            "the report must include the reason",
            "if the recommendation is `not needed`",
        )
        for text in (agents_text, workflow_text, protocol_text):
            for phrase in required_phrases:
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, text)

    def test_packet_protocol_requires_pre_merge_audit_for_audit_worthy_prs(
        self,
    ) -> None:
        text = _normalized_doc_text(
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md"
        )

        required_phrases = (
            "claude code audit required before merge",
            "if claude code audit is required or recommended, the pr must not be merged",
            "safety policy",
            "readiness posture",
            "live rails",
            "phase 14 or future live-pilot preparation",
            "candidate selection or candidate tracking",
            "todoist/gmail/calendar boundaries",
            "openclaw boundaries",
            "credential, secret, oauth, api-key, or token boundaries",
            "production db paths",
            "protected paths",
            "scheduler, background, launchagent, crontab, daemon, watcher, or service boundaries",
            "live model/api-call boundaries",
            "agent workflow, codex workflow, chatgpt workflow, or repo governance",
            "authorization wording that could be misread as approval, activation, or live execution",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_packet_protocol_records_recommended_and_skip_conditions(self) -> None:
        text = _normalized_doc_text(
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md"
        )

        required_phrases = (
            "claude code audit recommended",
            "medium-sized docs/test prs with safety-adjacent wording",
            "new tests that enforce safety or workflow invariants",
            "broad documentation reorganizations",
            "claude code audit usually not needed",
            "typo fixes",
            "formatting-only changes",
            "narrow checkpoint/status refreshes after already-audited work",
            "small docs-only updates that do not affect safety, authorization, runtime behavior, or agent workflow",
            "mechanical line, hash, or status updates",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_claude_code_audits_are_read_only_and_watch_tower_is_not_adopted(
        self,
    ) -> None:
        text = _normalized_doc_text(
            REPO_ROOT / "docs" / "AGENT_WORK_PACKET_PROTOCOL.md"
        )

        required_phrases = (
            "claude code audits are read-only by default",
            "no file modifications",
            "no commits",
            "no pushes",
            "no pr approval, close, or merge",
            "no live services",
            "no credentials, secrets, oauth files, api keys, or token handling",
            "no openclaw invocation",
            "no protected path access",
            "this protocol is not watch tower adoption",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertFalse((REPO_ROOT / ".agent").exists())
        self.assertFalse((REPO_ROOT / "CLAUDE.md").exists())


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_DOC = REPO_ROOT / "docs" / "PHASE_14C_CANDIDATE_DECISION_SUPPORT.md"


class Phase14CCandidateDecisionSupportDocsTest(unittest.TestCase):
    def test_support_doc_records_candidate_context_without_approval(self) -> None:
        text = _normalized_doc_text(SUPPORT_DOC)

        required_phrases = (
            "clean kitchen countertops and stovetop",
            "weekday: `monday`",
            "area: `kitchen`",
            "status: candidate-review tracking only",
            "candidate approved: no",
            "candidate authorized: no",
            "candidate activated or run: no",
            "phase 14-c remains blocked",
            "future explicit human approval required",
            "does not authorize execution",
            "does not authorize live service access",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_support_doc_preserves_non_live_non_runtime_exclusions(self) -> None:
        text = _normalized_doc_text(SUPPORT_DOC)

        required_phrases = (
            "todoist access or writes",
            "gmail access or writes",
            "calendar access or writes",
            "openclaw handoff or invocation",
            "credentials/auth handling",
            "production db activation",
            "scheduler/background activation",
            "protected path access",
            "external writes",
            "live model/api calls",
            "dynamic cleaning implementation",
            "15-task cleaning import",
            "skip/push/bump behavior",
            "automatic rescheduling",
            "watch tower adoption",
            "`.agent/`",
            "`claude.md`",
            "runtime/operator scaffolding",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertFalse((REPO_ROOT / ".agent").exists())
        self.assertFalse((REPO_ROOT / "CLAUDE.md").exists())

    def test_support_doc_records_options_checklists_and_stop_conditions(self) -> None:
        text = _normalized_doc_text(SUPPORT_DOC)

        required_phrases = (
            "approve for a later bounded repo-local prep packet",
            "reject candidate",
            "defer / keep blocked",
            "scope clarity",
            "household usefulness",
            "safety boundaries",
            "ambiguity risks",
            "expected manual validation",
            "before future approval",
            "separately gated even after approval",
            "failure-mode / risk checklist",
            "required future approval wording",
            "src/personalos/phase14c_candidate_decision_support.py",
            "blank_phase14c_candidate_decision_support_record",
            "validate_phase14c_candidate_decision_record",
            "build_phase14c_candidate_decision_support_report",
            "render_phase14c_candidate_decision_support_checklist",
            "unknown schema field",
            "extra top-level key",
            "nested payload under a known fillable field",
            "table-driven invariant coverage",
            "do not echo unsafe input values",
            "default report timestamps remain deterministic",
            "report shape contract coverage",
            "raw decision-record echo fields are absent",
            "missing-field matrix coverage",
            "required text default",
            "required false field",
            "unfilled fillable decision field",
            "fails closed as `decision_needed`",
            "blocked-reason sanitization",
            "caller-supplied decision and drift values",
            "blocked report json",
            "unknown schema key-name sanitization",
            "caller-supplied unknown keys",
            "failing closed on unknown schema fields",
            "blocked report sanitization matrix coverage",
            "nested-fillable payload inputs",
            "caller-controlled tokens",
            "nested prohibited-field coverage",
            "nested live/api and credential/secret values",
            "strict required-false-field coverage",
            "non-boolean false-like values",
            "unfilled false-default template",
            "strict required-text-default coverage",
            "case/spacing variants",
            "strict readiness.status coverage",
            "`readiness.status=not_ready`",
            "caller-controlled readiness drift values",
            "required readiness.status coverage",
            "missing readiness status",
            "required unfilled decision-field coverage",
            "missing fillable field",
            "strict unfilled decision-field coverage",
            "whitespace-only values",
            "expected an empty unfilled value",
            "required-field drift non-echo matrix coverage",
            "required text default drift value",
            "required false-field non-boolean value",
            "stop conditions",
            "missing, ambiguous, or unsafe evidence means defer / keep blocked",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_decision_record_template_defaults_to_unfilled_and_false(self) -> None:
        raw_text = SUPPORT_DOC.read_text(encoding="utf-8").lower()
        text = " ".join(raw_text.split())

        required_phrases = (
            "this template is inert and unfilled by default",
            "it does not approve anything",
            "decision_status: unfilled",
            "decision_option: unselected",
            "current_status: candidate-review tracking only",
            "readiness.status: not_ready",
            "approval_wording_provided: false",
            "evidence_review_complete: false",
            "manual_validation_complete: false",
            "phase14_c_approved: false",
            "candidate_approved: false",
            "candidate_authorized: false",
            "candidate_activated: false",
            "candidate_run: false",
            "candidate_execution_authorized: false",
            "live_rails_activated: false",
            "todoist_write_authorized: false",
            "openclaw_authorized: false",
            "credentials_auth_handling_authorized: false",
            "production_db_activation_authorized: false",
            "scheduler_background_activation_authorized: false",
            "protected_path_access_authorized: false",
            "external_writes_authorized: false",
            "live_model_api_calls_authorized: false",
            "dynamic_cleaning_authorized: false",
            "fifteen_task_import_authorized: false",
            "skip_push_bump_behavior_authorized: false",
            "automatic_rescheduling_authorized: false",
            "watch_tower_adoption_authorized: false",
            "agent_directory_authorized: false",
            "claude_md_authorized: false",
            "runtime_operator_scaffolding_authorized: false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        affirmative_keys = (
            "phase14_c_approved",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated",
            "candidate_run",
            "live_rails_activated",
            "todoist_write_authorized",
            "openclaw_authorized",
        )
        for key in affirmative_keys:
            with self.subTest(key=key):
                self.assertNotIn(f"{key}: true", raw_text)

    def test_support_doc_is_linked_from_related_phase_docs(self) -> None:
        support_link = "PHASE_14C_CANDIDATE_DECISION_SUPPORT.md"
        related_docs = (
            REPO_ROOT / "STATUS.md",
            REPO_ROOT / "docs" / "PRD.md",
            REPO_ROOT / "docs" / "ROADMAP.md",
            REPO_ROOT / "docs" / "SAFETY_POLICY.md",
            REPO_ROOT / "docs" / "PHASE_14C_DECISION_GATE.md",
            REPO_ROOT / "docs" / "PHASE_14_CANDIDATE_SELECTION_PREP.md",
        )

        for path in related_docs:
            with self.subTest(path=path.name):
                self.assertIn(support_link, path.read_text(encoding="utf-8"))


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

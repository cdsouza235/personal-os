import unittest

from personalos.phase14_candidate_selection_prep import (
    blank_phase14_candidate_selection_template,
    build_phase14_candidate_selection_report,
    validate_phase14_candidate_selection_candidate,
)
from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus


class Phase14CandidateSelectionPrepTest(unittest.TestCase):
    def test_blank_template_does_not_select_anything(self) -> None:
        template = blank_phase14_candidate_selection_template()
        report = build_phase14_candidate_selection_report([template])

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIsNone(report["selected_candidate"])
        self.assertIsNone(report["candidate_proposed_for_human_review"])
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["live_pilot_authorized"])
        self.assertFalse(report["live_pilot_run"])
        self.assertTrue(report["phase14_c_blocked"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertEqual(report["safety_posture"], SAFETY_POSTURE)

    def test_no_candidate_records_require_decision(self) -> None:
        report = build_phase14_candidate_selection_report()

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertIn("No candidate records were supplied.", report["reasons"])
        self.assertFalse(report["candidate_selected"])
        self.assertTrue(report["phase13e_d_synthetic_todoist_fixture_rejected"])
        self.assertTrue(report["activation_requires_later_packet"])

    def test_missing_required_fields_do_not_select_candidate(self) -> None:
        candidate = _valid_candidate()
        del candidate["low_risk_reason"]

        validation = validate_phase14_candidate_selection_candidate(candidate)
        report = build_phase14_candidate_selection_report([candidate])

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.accepted_for_human_review)
        self.assertIn(
            "Candidate required field is missing: low_risk_reason.",
            validation.reasons,
        )
        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertFalse(report["candidate_selected"])

    def test_multiple_candidates_do_not_auto_select(self) -> None:
        first = _valid_candidate()
        second = {**_valid_candidate(), "candidate_label": "routine-window-check"}

        report = build_phase14_candidate_selection_report([first, second])

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIsNone(report["selected_candidate"])
        self.assertIn("Multiple candidate records were supplied.", report["reasons"])

    def test_live_todoist_id_or_api_field_is_blocked(self) -> None:
        candidate = {
            **_valid_candidate(),
            "todoist_task_id": "1234567890",
            "live_api_config": {"blocked": "must-not-exist"},
        }

        report = build_phase14_candidate_selection_report([candidate])
        validation = report["candidate_validations"][0]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIn(
            "Candidate contains prohibited live Todoist/API field: todoist_task_id.",
            validation["reasons"],
        )
        self.assertIn(
            "Candidate contains prohibited live Todoist/API field: live_api_config.",
            validation["reasons"],
        )

    def test_credential_token_oauth_api_key_or_secret_field_is_blocked(self) -> None:
        candidate = {
            **_valid_candidate(),
            "metadata": {
                "token": "must-not-exist",
                "oauth": "must-not-exist",
                "api_key": "must-not-exist",
                "secret": "must-not-exist",
            },
        }

        report = build_phase14_candidate_selection_report([candidate])
        validation = report["candidate_validations"][0]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIn(
            "Candidate contains prohibited credential/secret field: token.",
            validation["reasons"],
        )
        self.assertIn(
            "Candidate contains prohibited credential/secret field: oauth.",
            validation["reasons"],
        )
        self.assertIn(
            "Candidate contains prohibited credential/secret field: api_key.",
            validation["reasons"],
        )
        self.assertIn(
            "Candidate contains prohibited credential/secret field: secret.",
            validation["reasons"],
        )

    def test_candidate_marked_approved_or_authorized_by_default_is_blocked(self) -> None:
        candidate = {
            **_valid_candidate(),
            "approved": True,
            "authorized": True,
            "live_pilot_run": True,
        }

        report = build_phase14_candidate_selection_report([candidate])
        reasons = report["candidate_validations"][0]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertTrue(any("approved" in reason for reason in reasons))
        self.assertTrue(any("authorized" in reason for reason in reasons))
        self.assertTrue(any("live_pilot_run" in reason for reason in reasons))

    def test_scheduler_background_openclaw_or_protected_path_dependency_is_blocked(self) -> None:
        candidate = {
            **_valid_candidate(),
            "requires_scheduler": True,
            "requires_background": True,
            "requires_openclaw": True,
            "protected_path": "/not/inspected/by/test",
        }

        report = build_phase14_candidate_selection_report([candidate])
        reasons = report["candidate_validations"][0]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIn(
            "Candidate declares prohibited dependency or boundary crossing: "
            "requires_scheduler.",
            reasons,
        )
        self.assertIn(
            "Candidate declares prohibited dependency or boundary crossing: "
            "requires_background.",
            reasons,
        )
        self.assertIn(
            "Candidate declares prohibited dependency or boundary crossing: "
            "requires_openclaw.",
            reasons,
        )
        self.assertIn(
            "Candidate declares prohibited dependency or boundary crossing: "
            "protected_path.",
            reasons,
        )

    def test_high_stakes_candidate_is_blocked(self) -> None:
        candidate = {**_valid_candidate(), "domain": "legal"}

        report = build_phase14_candidate_selection_report([candidate])

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIn(
            "Candidate domain is prohibited for first selection: legal.",
            report["candidate_validations"][0]["reasons"],
        )

    def test_one_valid_inert_candidate_is_proposed_only(self) -> None:
        report = build_phase14_candidate_selection_report([_valid_candidate()])
        proposed = report["candidate_proposed_for_human_review"]

        self.assertEqual(report["status"], PilotPrepStatus.PROPOSED_ONLY.value)
        self.assertFalse(report["candidate_selected"])
        self.assertIsNone(report["selected_candidate"])
        self.assertIsNotNone(proposed)
        self.assertEqual(proposed["candidate_label"], "routine-plan-review")
        self.assertTrue(proposed["proposed_only"])
        self.assertFalse(proposed["selected"])
        self.assertFalse(proposed["approved"])
        self.assertFalse(proposed["authorized"])
        self.assertFalse(proposed["live_pilot_run"])
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["live_pilot_authorized"])
        self.assertFalse(report["live_pilot_run"])
        self.assertEqual(report["readiness"]["status"], "not_ready")

    def test_live_external_and_service_flags_remain_false(self) -> None:
        report = build_phase14_candidate_selection_report([_valid_candidate()])

        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["external_services_contacted"])
        self.assertFalse(report["external_mutation"])
        self.assertFalse(report["readiness"]["live_rails_activated"])
        self.assertTrue(report["readiness"]["inert_report_only"])
        self.assertFalse(report["safety_posture"]["credentials_loaded"])
        self.assertFalse(report["safety_posture"]["credentials_read"])
        self.assertFalse(report["safety_posture"]["scheduler_activated"])
        self.assertFalse(report["safety_posture"]["openclaw_called"])
        self.assertFalse(report["safety_posture"]["gmail_touched"])
        self.assertFalse(report["safety_posture"]["todoist_touched"])
        self.assertFalse(report["safety_posture"]["calendar_touched"])

    def test_checklist_preserves_phase_boundary(self) -> None:
        report = build_phase14_candidate_selection_report()
        checklist = "\n".join(report["preflight_checklist"])

        self.assertIn("No candidate is currently selected.", checklist)
        self.assertIn("Phase 13E-D synthetic Todoist fixture remains rejected.", checklist)
        self.assertIn("Phase 14-C remains blocked.", checklist)
        self.assertIn("Candidate selection does not equal live authorization.", checklist)
        self.assertIn("Live activation requires a later explicit packet.", checklist)


def _valid_candidate() -> dict[str, object]:
    return {
        "candidate_label": "routine-plan-review",
        "routine_task_description": "Review tomorrow's routine plan.",
        "intended_future_window": "A future morning review window selected by Chris.",
        "self_only_reason": "The task is only for Chris and has no recipients.",
        "low_risk_reason": "The task is a reversible personal planning reminder.",
        "foreground_only_reason": "It would only run from a later explicit foreground action.",
        "future_only_reason": "It refers to a future routine review, not a past action.",
        "no_sensitive_domain_confirmation": True,
        "no_external_dependency_confirmation": True,
        "no_gmail_or_calendar_dependency_confirmation": True,
        "no_credentials_or_live_ids_confirmation": True,
        "no_protected_path_interaction_confirmation": True,
        "no_scheduler_background_or_openclaw_confirmation": True,
        "safe_to_dry_run_inertly_confirmation": True,
        "abort_criteria": "Abort if any live rail, credential, or ambiguity is required.",
        "evidence_required_before_live_authorization": (
            "A later dry-run, idempotency, ledger, rollback, and completion-report packet."
        ),
        "selected": False,
        "approved": False,
        "authorized": False,
        "live_pilot_run": False,
        "readiness.status": "not_ready",
    }

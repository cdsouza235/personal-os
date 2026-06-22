import unittest

from personalos.phase14_candidate_selection_prep import (
    CANDIDATE_REVIEW_TRACKING_STATUS,
    blank_phase14_candidate_selection_template,
    build_phase14_candidate_selection_report,
    phase14_cleaning_candidate_review_tracking_record,
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
        self.assertEqual(report["candidate_record_count"], 0)
        self.assertEqual(report["candidate_review_tracking"]["candidate_count"], 0)
        self.assertFalse(report["candidate_review_tracking"]["exactly_one_candidate_recorded"])
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
        self.assertEqual(report["candidate_record_count"], 1)
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

    def test_recorded_cleaning_candidate_is_review_tracking_only(self) -> None:
        report = build_phase14_candidate_selection_report(
            [phase14_cleaning_candidate_review_tracking_record()]
        )
        tracking = report["candidate_review_tracking"]
        candidate = tracking["candidate"]

        self.assertEqual(report["status"], PilotPrepStatus.PROPOSED_ONLY.value)
        self.assertEqual(report["candidate_record_count"], 1)
        self.assertEqual(tracking["candidate_count"], 1)
        self.assertTrue(tracking["exactly_one_candidate_recorded"])
        self.assertEqual(tracking["status"], CANDIDATE_REVIEW_TRACKING_STATUS)
        self.assertEqual(candidate["candidate_name"], "Clean Kitchen Countertops and Stovetop")
        self.assertEqual(candidate["task_title"], "Clean Kitchen Countertops and Stovetop")
        self.assertEqual(candidate["weekday"], "Monday")
        self.assertEqual(candidate["home_area"], "Kitchen")
        self.assertEqual(candidate["candidate_type"], "household_cleaning_routine_task")
        self.assertEqual(
            candidate["candidate_scope"],
            "one recurring self-only Todoist routine-task candidate",
        )
        self.assertEqual(
            candidate["candidate_review_tracking_status"],
            CANDIDATE_REVIEW_TRACKING_STATUS,
        )
        self.assertTrue(candidate["review_tracking_only"])
        self.assertFalse(candidate["selected"])
        self.assertFalse(candidate["approved"])
        self.assertFalse(candidate["authorized"])
        self.assertFalse(candidate["live_pilot_run"])
        self.assertFalse(report["candidate_selected"])
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["candidate_approved_for_execution"])
        self.assertFalse(report["candidate_activated"])
        self.assertFalse(report["live_pilot_authorized"])
        self.assertFalse(report["live_pilot_run"])
        self.assertTrue(report["phase14_c_blocked"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertTrue(report["readiness"]["inert_report_only"])
        self.assertFalse(report["readiness"]["live_rails_activated"])

    def test_live_external_and_service_flags_remain_false(self) -> None:
        report = build_phase14_candidate_selection_report(
            [phase14_cleaning_candidate_review_tracking_record()]
        )

        self.assertFalse(report["gmail_touched"])
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["calendar_touched"])
        self.assertFalse(report["openclaw_called"])
        self.assertFalse(report["scheduler_activated"])
        self.assertFalse(report["background_loop_activated"])
        self.assertFalse(report["launch_agent_installed"])
        self.assertFalse(report["crontab_modified"])
        self.assertFalse(report["daemon_started"])
        self.assertFalse(report["credentials_loaded"])
        self.assertFalse(report["credentials_read"])
        self.assertFalse(report["production_db_path_active"])
        self.assertFalse(report["personalos_markdown_written"])
        self.assertFalse(report["protected_paths_touched"])
        self.assertFalse(report["live_model_api_called"])
        self.assertFalse(report["watch_tower_adopted_or_merged"])
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

    def test_dynamic_cleaning_context_is_not_implemented(self) -> None:
        report = build_phase14_candidate_selection_report(
            [phase14_cleaning_candidate_review_tracking_record()]
        )
        context = report["future_dynamic_cleaning_system_context"]
        exclusions = report["candidate_exclusions"]

        self.assertTrue(context["context_only"])
        self.assertFalse(context["implemented"])
        self.assertEqual(context["rough_total_cleaning_task_count"], "roughly_15")
        self.assertFalse(context["fifteen_task_imported"])
        self.assertFalse(context["dynamic_rotation_implemented"])
        self.assertFalse(context["automatic_skip_push_bump_implemented"])
        self.assertFalse(context["automatic_rescheduling_implemented"])
        self.assertFalse(context["scheduler_logic_created"])
        self.assertFalse(context["openclaw_source_imported"])
        self.assertIn("No 15-task import.", exclusions)
        self.assertIn("No dynamic cleaning rotation implementation.", exclusions)
        self.assertIn("No automatic skip/push/bump behavior.", exclusions)
        self.assertIn("No automatic rescheduling.", exclusions)
        self.assertIn("No OpenClaw access.", exclusions)
        self.assertIn("No Todoist writes.", exclusions)
        self.assertIn("No Gmail access.", exclusions)
        self.assertIn("No Calendar access.", exclusions)
        self.assertIn("No production DB activation.", exclusions)
        self.assertIn("No scheduler/background activation.", exclusions)
        self.assertIn("No live model/API calls.", exclusions)
        self.assertIn("No Watch Tower adoption or merge.", exclusions)

    def test_required_boundary_language_remains_true(self) -> None:
        report = build_phase14_candidate_selection_report(
            [phase14_cleaning_candidate_review_tracking_record()]
        )
        boundaries = report["boundary_assertions"]

        self.assertTrue(boundaries["this_is_not_phase_14_c"])
        self.assertTrue(boundaries["this_is_not_live_activation"])
        self.assertTrue(boundaries["this_is_not_todoist_access"])
        self.assertTrue(boundaries["this_is_not_todoist_write_authorization"])
        self.assertTrue(boundaries["this_is_not_credential_oauth_api_token_handling"])
        self.assertTrue(boundaries["this_is_not_candidate_approval_for_execution"])
        self.assertFalse(boundaries["readiness_status_changed_to_ready"])
        self.assertTrue(boundaries["phase14_c_remains_blocked"])
        self.assertTrue(boundaries["candidate_selection_and_live_activation_remain_separate"])

    def test_checklist_preserves_phase_boundary(self) -> None:
        report = build_phase14_candidate_selection_report()
        checklist = "\n".join(report["preflight_checklist"])

        self.assertIn("No candidate is selected for live execution.", checklist)
        self.assertIn("Phase 13E-D synthetic Todoist fixture remains rejected.", checklist)
        self.assertIn("Phase 14-C remains blocked.", checklist)
        self.assertIn("Candidate selection does not equal live authorization.", checklist)
        self.assertIn(
            "A recorded candidate-review tracking candidate is not approved for execution.",
            checklist,
        )
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

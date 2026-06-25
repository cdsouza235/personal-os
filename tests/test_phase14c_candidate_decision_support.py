import unittest

from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus
from personalos.phase14c_candidate_decision_support import (
    PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
    blank_phase14c_candidate_decision_support_record,
    build_phase14c_candidate_decision_support_report,
    validate_phase14c_candidate_decision_record,
)


class Phase14CCandidateDecisionSupportRecordTest(unittest.TestCase):
    def test_blank_template_is_unfilled_and_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        validation = validate_phase14c_candidate_decision_record(record)
        report = build_phase14c_candidate_decision_support_report(record)

        self.assertEqual(record["schema_version"], PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION)
        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertTrue(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertTrue(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertFalse(report["decision_option_selected"])
        self.assertEqual(report["decision_option"], "unselected")

    def test_default_report_uses_unfilled_false_default_record(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertTrue(report["decision_record_validated_as_unfilled"])
        self.assertTrue(validation["record_accepted_as_unfilled_template"])
        self.assertEqual(report["decision_record_template"]["decision_status"], "unfilled")
        self.assertEqual(report["decision_record_template"]["decision_option"], "unselected")
        self.assertFalse(report["decision_record_template"]["candidate_approved"])

    def test_missing_record_requires_false_default_template(self) -> None:
        validation = validate_phase14c_candidate_decision_record(None)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "No decision-support record was supplied; the false-default template remains required.",
            validation.reasons,
        )

    def test_selected_decision_option_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "decision_status": "recorded",
            "decision_option": "approve for later bounded repo-local prep packet",
            "decision_date": "2026-06-25",
            "decision_maker": "Chris",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertTrue(validation.human_decision_recorded)
        self.assertIn(
            "Decision record selects decision_status=recorded; this packet cannot record a human decision.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record selects decision_option=approve for later bounded repo-local prep packet; this packet cannot select approve, reject, or defer.",
            validation.reasons,
        )

    def test_approval_authorization_and_execution_flags_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "phase14_c_approved": True,
            "candidate_approved": True,
            "candidate_authorized": True,
            "candidate_activated": True,
            "candidate_run": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["candidate_activated"])
        self.assertFalse(report["candidate_run"])
        for field in (
            "phase14_c_approved",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated",
            "candidate_run",
        ):
            with self.subTest(field=field):
                self.assertTrue(any(field in reason for reason in reasons))

    def test_live_service_and_runtime_authorization_flags_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "todoist_write_authorized": True,
            "gmail_access_authorized": True,
            "calendar_write_authorized": True,
            "openclaw_authorized": True,
            "scheduler_background_activation_authorized": True,
            "production_db_activation_authorized": True,
            "protected_path_access_authorized": True,
            "live_model_api_calls_authorized": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["gmail_touched"])
        self.assertFalse(report["calendar_touched"])
        self.assertFalse(report["openclaw_called"])
        self.assertFalse(report["scheduler_activated"])
        for field in (
            "todoist_write_authorized",
            "gmail_access_authorized",
            "calendar_write_authorized",
            "openclaw_authorized",
            "scheduler_background_activation_authorized",
            "production_db_activation_authorized",
            "protected_path_access_authorized",
            "live_model_api_calls_authorized",
        ):
            with self.subTest(field=field):
                self.assertTrue(any(field in reason for reason in reasons))

    def test_dynamic_cleaning_watch_tower_agent_and_runtime_scaffolding_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "dynamic_cleaning_authorized": True,
            "fifteen_task_import_authorized": True,
            "skip_push_bump_behavior_authorized": True,
            "automatic_rescheduling_authorized": True,
            "watch_tower_adoption_authorized": True,
            "agent_directory_authorized": True,
            "claude_md_authorized": True,
            "runtime_operator_scaffolding_authorized": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["watch_tower_adopted_or_merged"])
        self.assertFalse(report["agent_directory_created"])
        self.assertFalse(report["claude_md_created"])
        self.assertFalse(report["runtime_operator_scaffolding_created"])
        self.assertTrue(any("dynamic_cleaning_authorized" in reason for reason in reasons))
        self.assertTrue(any("watch_tower_adoption_authorized" in reason for reason in reasons))
        self.assertTrue(any("agent_directory_authorized" in reason for reason in reasons))
        self.assertTrue(any("claude_md_authorized" in reason for reason in reasons))

    def test_live_ids_credentials_and_secret_fields_are_blocked_even_when_nested(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "metadata": {
                "todoist_task_id": "1234567890",
                "oauth_token": "must-not-exist",
                "api_key": "must-not-exist",
                "secret": "must-not-exist",
            },
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertIn(
            "Decision record contains prohibited live/API field: todoist_task_id.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: oauth_token.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: api_key.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: secret.",
            validation.reasons,
        )

    def test_unknown_top_level_schema_field_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "session_token": "novel-field-name-must-not-pass",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision record contains unknown schema field: session_token.",
            validation.reasons,
        )

    def test_nested_unknown_container_is_blocked_before_acceptance(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "metadata": {"session_token": "must-not-pass"},
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision record contains unknown schema field: metadata.",
            validation.reasons,
        )

    def test_candidate_context_drift_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "candidate": "Different Candidate",
            "weekday": "Tuesday",
            "area": "Garage",
            "current_status": "approved",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertIn(
            "Decision record changes candidate; expected 'Clean Kitchen Countertops and Stovetop', got 'Different Candidate'.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record changes current_status; expected 'candidate-review tracking only', got 'approved'.",
            validation.reasons,
        )

    def test_missing_required_false_field_fails_closed_as_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        del record["candidate_approved"]

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision-support record required false field is missing: candidate_approved.",
            validation.reasons,
        )

    def test_report_preserves_inert_safety_posture_and_candidate_tracking_only(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        tracking = report["candidate_review_tracking"]

        self.assertTrue(report["candidate_review_tracking_only"])
        self.assertEqual(tracking["candidate"]["candidate_name"], "Clean Kitchen Countertops and Stovetop")
        self.assertEqual(tracking["candidate"]["weekday"], "Monday")
        self.assertEqual(tracking["candidate"]["home_area"], "Kitchen")
        self.assertTrue(tracking["candidate"]["review_tracking_only"])
        self.assertFalse(tracking["candidate"]["selected"])
        self.assertFalse(tracking["candidate"]["approved"])
        self.assertFalse(tracking["candidate"]["authorized"])
        self.assertFalse(tracking["candidate"]["live_pilot_run"])
        self.assertTrue(report["phase14_c_blocked"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertTrue(report["readiness"]["inert_report_only"])
        self.assertFalse(report["readiness"]["live_rails_activated"])
        self.assertEqual(report["safety_posture"], SAFETY_POSTURE)

    def test_report_live_external_and_runtime_flags_remain_false(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

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
        self.assertFalse(report["external_services_contacted"])
        self.assertFalse(report["external_mutation"])

    def test_checklist_preserves_non_authorization_boundary(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        checklist = "\n".join(report["preflight_checklist"])

        self.assertIn("Decision record is unfilled by default.", checklist)
        self.assertIn("Decision option remains unselected.", checklist)
        self.assertIn("No approve, reject, or defer decision is recorded.", checklist)
        self.assertIn("Phase 14-C remains blocked.", checklist)
        self.assertIn("Candidate is not approved, authorized, activated, or run.", checklist)
        self.assertIn("Todoist, Gmail, Calendar, OpenClaw", checklist)

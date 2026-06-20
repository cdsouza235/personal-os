import unittest

from personalos.demo.fixtures import build_synthesis_payload
from personalos.phase14_pilot_prep import (
    SAFETY_POSTURE,
    PilotPrepStatus,
    build_phase14_ab_pilot_preparation,
    guard_phase14_ab_live_execution,
    validate_phase13g_todoist_candidate,
)


class Phase14PilotPreparationTest(unittest.TestCase):
    def test_missing_candidate_requires_human_selection_and_stays_inert(self) -> None:
        report = build_phase14_ab_pilot_preparation()

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertFalse(report["candidate_source"]["phase13g_validated_candidate_found"])
        self.assertIsNone(report["selected_candidate"])
        self.assertFalse(report["pilot_authorized"])
        self.assertFalse(report["pilot_approved"])
        self.assertFalse(report["pilot_run"])
        self.assertFalse(report["execution_allowed"])
        self.assertTrue(report["stop_before_live_activation"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertEqual(report["safety_posture"], SAFETY_POSTURE)
        self.assertIn(
            "No exact validated Phase 13G candidate is selected.",
            report["activation_blockers"],
        )

    def test_phase_13e_d_todoist_fixture_is_not_promoted_to_phase_14_candidate(self) -> None:
        phase13e_candidate = build_synthesis_payload()["candidates"]["todoist_tasks"][0]

        validation = validate_phase13g_todoist_candidate(phase13e_candidate)
        report = build_phase14_ab_pilot_preparation([phase13e_candidate])

        self.assertFalse(validation.accepted)
        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertIn(
            "Candidate is not recorded as a Phase 13G candidate.",
            validation.reasons,
        )
        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertIsNone(report["selected_candidate"])
        self.assertFalse(report["candidate_source"]["phase13g_validated_candidate_found"])

    def test_one_validated_phase_13g_candidate_is_proposed_only_not_approved(self) -> None:
        report = build_phase14_ab_pilot_preparation([_valid_phase13g_candidate()])

        self.assertEqual(report["status"], PilotPrepStatus.PROPOSED_ONLY.value)
        self.assertTrue(report["candidate_source"]["phase13g_validated_candidate_found"])
        self.assertEqual(
            report["selected_candidate"]["candidate_ref"],
            "phase-13g-routine-task-review-plan-2026-06-22",
        )
        self.assertEqual(report["selected_candidate"]["source_phase"], "Phase 13G")
        self.assertTrue(report["selected_candidate"]["self_only"])
        self.assertTrue(report["selected_candidate"]["foreground_only"])
        self.assertTrue(report["selected_candidate"]["future_only"])
        self.assertFalse(report["selected_candidate"]["approved"])
        self.assertFalse(report["pilot_authorized"])
        self.assertFalse(report["pilot_approved"])
        self.assertFalse(report["execution_allowed"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertEqual(report["pilot_design"]["live_write_state"], "not_attempted")
        self.assertFalse(report["pilot_design"]["instructions_that_would_cause_live_write"])
        self.assertEqual(report["pilot_design"]["real_todoist_task_ids"], [])
        self.assertIsNone(report["pilot_design"]["credential_configuration"])

    def test_live_execution_guard_always_fails_closed_for_preparation_report(self) -> None:
        report = build_phase14_ab_pilot_preparation([_valid_phase13g_candidate()])

        guard = guard_phase14_ab_live_execution(report)

        self.assertEqual(guard["status"], "blocked")
        self.assertFalse(guard["live_action_attempted"])
        self.assertFalse(guard["todoist_touched"])
        self.assertFalse(guard["external_services_contacted"])
        self.assertFalse(guard["external_mutation"])
        self.assertFalse(guard["scheduler_activated"])
        self.assertFalse(guard["openclaw_called"])
        self.assertIn("readiness.status=not_ready", guard["blockers"][0])
        self.assertIn("Pilot is not authorized.", guard["blockers"])
        self.assertIn("Pilot is not approved.", guard["blockers"])
        self.assertEqual(guard["safety_posture"], SAFETY_POSTURE)

    def test_multiple_valid_candidates_require_human_choice(self) -> None:
        first = _valid_phase13g_candidate()
        second = {
            **_valid_phase13g_candidate(),
            "candidate_ref": "phase-13g-routine-task-evening-check-2026-06-22",
            "task_title": "Review evening shutdown checklist",
        }

        report = build_phase14_ab_pilot_preparation([first, second])

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertIsNone(report["selected_candidate"])
        self.assertIn(
            "Multiple validated Phase 13G candidates were supplied.",
            report["candidate_source"]["reasons"],
        )

    def test_candidate_with_live_fields_is_blocked_and_never_selected(self) -> None:
        candidate = {
            **_valid_phase13g_candidate(),
            "todoist_task_id": "live-task-id-that-must-not-be-used",
        }

        report = build_phase14_ab_pilot_preparation([candidate])
        validation = report["candidate_validations"][0]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertIsNone(report["selected_candidate"])
        self.assertEqual(validation["status"], PilotPrepStatus.BLOCKED.value)
        self.assertIn(
            "Candidate contains prohibited live field: todoist_task_id.",
            validation["reasons"],
        )

    def test_non_selected_rails_stay_disabled_without_clients_or_mutation(self) -> None:
        report = build_phase14_ab_pilot_preparation([_valid_phase13g_candidate()])

        for rail in report["non_selected_rails"]:
            with self.subTest(rail=rail["rail"]):
                self.assertEqual(rail["status"], "disabled")
                self.assertFalse(rail["credentials_loaded"])
                self.assertFalse(rail["client_initialized"])
                self.assertFalse(rail["external_mutation"])

        self.assertFalse(report["safety_posture"]["gmail_touched"])
        self.assertFalse(report["safety_posture"]["todoist_touched"])
        self.assertFalse(report["safety_posture"]["calendar_touched"])

    def test_preflight_checklist_preserves_stop_boundary(self) -> None:
        report = build_phase14_ab_pilot_preparation()

        checklist_text = "\n".join(report["preflight_checklist"])

        self.assertIn("Pilot is proposed only; it is not authorized.", checklist_text)
        self.assertIn("Stop before live activation.", checklist_text)
        self.assertIn("Todoist credentials, clients, API calls, and task IDs", checklist_text)


def _valid_phase13g_candidate() -> dict[str, object]:
    return {
        "candidate_ref": "phase-13g-routine-task-review-plan-2026-06-22",
        "source_phase": "Phase 13G",
        "validation_status": "validated",
        "rail": "todoist",
        "operation": "create_routine_task",
        "candidate_type": "routine_todoist_task",
        "task_title": "Review tomorrow's routine plan",
        "risk_level": "low",
        "self_only": True,
        "foreground_only": True,
        "future_only": True,
        "routine_task_oriented": True,
        "approved": False,
    }

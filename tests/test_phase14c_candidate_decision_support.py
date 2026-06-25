import json
import unittest

from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus
from personalos.phase14c_candidate_decision_support import (
    FILLABLE_DECISION_FIELDS,
    KNOWN_DECISION_RECORD_FIELDS,
    PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
    REQUIRED_FALSE_FIELDS,
    REQUIRED_TEXT_DEFAULTS,
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
        self.assertEqual(record["readiness.status"], "not_ready")
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

    def test_report_top_level_shape_remains_explicit_and_inert(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        self.assertEqual(
            set(report),
            {
                "schema_version",
                "generated_at_utc",
                "phase_label",
                "status",
                "decision_record_validated_as_unfilled",
                "human_decision_recorded",
                "decision_option_selected",
                "decision_option",
                "candidate_review_tracking_only",
                "candidate_review_tracking",
                "phase14_c_blocked",
                "candidate_approved",
                "candidate_authorized",
                "candidate_activated",
                "candidate_run",
                "candidate_execution_authorized",
                "live_pilot_authorized",
                "live_pilot_run",
                "approval_to_merge_docs_is_not_live_authorization",
                "gmail_touched",
                "todoist_touched",
                "calendar_touched",
                "openclaw_called",
                "scheduler_activated",
                "background_loop_activated",
                "launch_agent_installed",
                "crontab_modified",
                "daemon_started",
                "credentials_loaded",
                "credentials_read",
                "production_db_path_active",
                "personalos_markdown_written",
                "protected_paths_touched",
                "live_model_api_called",
                "watch_tower_adopted_or_merged",
                "agent_directory_created",
                "claude_md_created",
                "runtime_operator_scaffolding_created",
                "external_services_contacted",
                "external_mutation",
                "readiness",
                "decision_record_validation",
                "decision_record_template",
                "preflight_checklist",
                "safety_posture",
            },
        )
        self.assertNotIn("raw_decision_record", report)
        self.assertNotIn("input_record", report)
        self.assertNotIn("unsafe_input", report)

    def test_validation_payload_shape_remains_explicit(self) -> None:
        validation = validate_phase14c_candidate_decision_record(
            blank_phase14c_candidate_decision_support_record()
        ).to_dict()

        self.assertEqual(
            set(validation),
            {
                "status",
                "record_accepted_as_unfilled_template",
                "human_decision_recorded",
                "reasons",
                "normalized_record",
            },
        )
        self.assertEqual(validation["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertEqual(
            set(validation["normalized_record"]),
            set(REQUIRED_TEXT_DEFAULTS)
            | set(REQUIRED_FALSE_FIELDS)
            | set(FILLABLE_DECISION_FIELDS)
            | {
                "phase14_c_blocked",
                "candidate_review_tracking_only",
                "human_decision_recorded",
                "readiness.status",
            },
        )

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
            "Decision record selects decision_status; this packet cannot record a human decision.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record selects decision_option; this packet cannot select approve, reject, or defer.",
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
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
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
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
            validation.reasons,
        )

    def test_blocked_report_does_not_echo_unknown_schema_key_names(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "secret-unknown-key-must-not-leak": (
                    "secret-unknown-value-must-not-leak"
                ),
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertIn(
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
            validation["reasons"],
        )
        self.assertNotIn("secret-unknown-key-must-not-leak", serialized_report)
        self.assertNotIn("secret-unknown-value-must-not-leak", serialized_report)

    def test_nested_payload_under_known_fillable_field_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "notes": {"session_token": "must-not-pass"},
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertTrue(validation.human_decision_recorded)
        self.assertIn(
            "Decision record fills notes; recording a human decision is out of scope.",
            validation.reasons,
        )

    def test_every_fillable_decision_field_blocks_and_marks_human_decision(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: "filled outside this packet",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertTrue(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record fills {field}; recording a human decision is out of scope.",
                    validation.reasons,
                )

    def test_every_fillable_decision_field_blocks_when_not_exact_empty(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: " ",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected an empty unfilled value.",
                    validation.reasons,
                )

    def test_every_required_false_field_blocks_when_truthy(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: True,
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertIn(
                    f"Decision record is marked {field}; this packet cannot approve, "
                    "authorize, activate, execute, or grant live access.",
                    validation.reasons,
                )

    def test_every_required_false_field_blocks_when_not_boolean_false(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: "false",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected boolean false.",
                    validation.reasons,
                )

    def test_false_field_non_boolean_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": "matrix-secret-false-field-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes candidate_approved; expected boolean false.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-false-field-value", serialized_report)

    def test_required_false_field_non_boolean_values_do_not_echo_for_every_field(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-false-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        field: unsafe_value,
                    }
                )

                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertFalse(validation["human_decision_recorded"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record changes {field}; expected boolean false.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_known_schema_fields_match_false_default_template(self) -> None:
        record_fields = set(blank_phase14c_candidate_decision_support_record())

        self.assertEqual(record_fields, set(KNOWN_DECISION_RECORD_FIELDS))

    def test_validation_statuses_remain_decision_needed_or_blocked_only(self) -> None:
        records = (
            None,
            blank_phase14c_candidate_decision_support_record(),
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_option": "reject candidate",
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "unknown_future_field": "must-not-pass",
            },
        )

        statuses = {
            validate_phase14c_candidate_decision_record(record).status
            for record in records
        }

        self.assertLessEqual(
            statuses,
            {PilotPrepStatus.DECISION_NEEDED, PilotPrepStatus.BLOCKED},
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
            "Decision record changes candidate; expected the unfilled false-default template value.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record changes current_status; expected the unfilled false-default template value.",
            validation.reasons,
        )

    def test_every_required_text_default_blocks_when_not_exact_literal(self) -> None:
        for field, expected in REQUIRED_TEXT_DEFAULTS.items():
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: f" {expected} ",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected the unfilled false-default "
                    "template value.",
                    validation.reasons,
                )

    def test_required_text_default_drift_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "weekday": "matrix-secret-text-default-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes weekday; expected the unfilled false-default "
            "template value.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-text-default-value", serialized_report)

    def test_required_text_default_drift_values_do_not_echo_for_every_field(self) -> None:
        for field in REQUIRED_TEXT_DEFAULTS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-text-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        field: unsafe_value,
                    }
                )

                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record changes {field}; expected the unfilled false-default "
                    "template value.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_readiness_status_blocks_when_not_exact_literal(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "readiness.status": " not_ready ",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertIn(
            "Decision record changes readiness.status; expected 'not_ready'.",
            validation.reasons,
        )

    def test_readiness_status_drift_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "readiness.status": "matrix-secret-readiness-status-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes readiness.status; expected 'not_ready'.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-readiness-status-value", serialized_report)

    def test_each_required_text_default_missing_fails_closed_as_decision_needed(self) -> None:
        for field, expected in REQUIRED_TEXT_DEFAULTS.items():
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required field is missing: {field}={expected}.",
                    validation.reasons,
                )

    def test_each_required_false_field_missing_fails_closed_as_decision_needed(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required false field is missing: {field}.",
                    validation.reasons,
                )

    def test_each_fillable_decision_field_missing_fails_closed_as_decision_needed(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required unfilled field is missing: {field}.",
                    validation.reasons,
                )

    def test_missing_readiness_status_fails_closed_as_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        del record["readiness.status"]

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertIn(
            "Decision-support record required field is missing: "
            "readiness.status=not_ready.",
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

    def test_blocked_report_does_not_echo_unsafe_input_values(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
                "notes": {
                    "api_key": "secret-value-must-not-leak",
                    "todoist_task_id": "live-id-must-not-leak",
                },
                "unknown_future_field": "unknown-value-must-not-leak",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertIsNone(report["decision_record_validation"]["normalized_record"])
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["candidate_activated"])
        self.assertFalse(report["candidate_run"])
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["credentials_loaded"])
        self.assertNotIn("secret-value-must-not-leak", serialized_report)
        self.assertNotIn("live-id-must-not-leak", serialized_report)
        self.assertNotIn("unknown-value-must-not-leak", serialized_report)

    def test_blocked_report_does_not_echo_unsafe_decision_or_drift_values(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_status": "secret-status-value-must-not-leak",
                "decision_option": "secret-option-value-must-not-leak",
                "candidate": "secret-candidate-value-must-not-leak",
                "weekday": "secret-weekday-value-must-not-leak",
                "area": "secret-area-value-must-not-leak",
                "current_status": "secret-current-status-value-must-not-leak",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertTrue(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record selects decision_status; this packet cannot record a human decision.",
            validation["reasons"],
        )
        self.assertIn(
            "Decision record selects decision_option; this packet cannot select approve, reject, or defer.",
            validation["reasons"],
        )
        for unsafe_value in (
            "secret-status-value-must-not-leak",
            "secret-option-value-must-not-leak",
            "secret-candidate-value-must-not-leak",
            "secret-weekday-value-must-not-leak",
            "secret-area-value-must-not-leak",
            "secret-current-status-value-must-not-leak",
        ):
            with self.subTest(unsafe_value=unsafe_value):
                self.assertNotIn(unsafe_value, serialized_report)

    def test_blocked_report_sanitization_matrix_rejects_caller_controlled_tokens(self) -> None:
        cases = (
            (
                "unknown_schema",
                {
                    "matrix-secret-unknown-key": "matrix-secret-unknown-value",
                },
                ("matrix-secret-unknown-key", "matrix-secret-unknown-value"),
            ),
            (
                "decision_selection",
                {
                    "decision_status": "matrix-secret-status-value",
                    "decision_option": "matrix-secret-option-value",
                    "decision_maker": "matrix-secret-maker-value",
                },
                (
                    "matrix-secret-status-value",
                    "matrix-secret-option-value",
                    "matrix-secret-maker-value",
                ),
            ),
            (
                "candidate_drift",
                {
                    "candidate": "matrix-secret-candidate-value",
                    "weekday": "matrix-secret-weekday-value",
                    "area": "matrix-secret-area-value",
                    "current_status": "matrix-secret-status-drift-value",
                },
                (
                    "matrix-secret-candidate-value",
                    "matrix-secret-weekday-value",
                    "matrix-secret-area-value",
                    "matrix-secret-status-drift-value",
                ),
            ),
            (
                "nested_fillable_payload",
                {
                    "notes": {
                        "session_token": "matrix-secret-nested-token-value",
                    },
                },
                ("matrix-secret-nested-token-value",),
            ),
        )

        for name, changes, unsafe_tokens in cases:
            with self.subTest(name=name):
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        **changes,
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(
                    report["decision_record_validation"]["normalized_record"]
                )
                for unsafe_token in unsafe_tokens:
                    self.assertNotIn(unsafe_token, serialized_report)

    def test_nested_prohibited_field_values_are_blocked_without_echo(self) -> None:
        cases = (
            (
                "nested_live_api_fields",
                {
                    "matrix-secret-live-container": {
                        "todoist_task_id": "matrix-secret-live-id-value",
                        "live_object_id": "matrix-secret-live-object-value",
                    },
                },
                (
                    "matrix-secret-live-container",
                    "matrix-secret-live-id-value",
                    "matrix-secret-live-object-value",
                ),
                (
                    "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
                    "Decision record contains prohibited live/API field: todoist_task_id.",
                    "Decision record contains prohibited live/API field: live_object_id.",
                ),
            ),
            (
                "nested_credential_secret_fields",
                {
                    "matrix-secret-credential-container": {
                        "api_key": "matrix-secret-api-key-value",
                        "oauth_token": "matrix-secret-oauth-token-value",
                        "client_secret": "matrix-secret-client-secret-value",
                    },
                },
                (
                    "matrix-secret-credential-container",
                    "matrix-secret-api-key-value",
                    "matrix-secret-oauth-token-value",
                    "matrix-secret-client-secret-value",
                ),
                (
                    "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
                    "Decision record contains prohibited credential/secret field: api_key.",
                    "Decision record contains prohibited credential/secret field: oauth_token.",
                    "Decision record contains prohibited credential/secret field: client_secret.",
                ),
            ),
        )

        for name, changes, unsafe_tokens, expected_reasons in cases:
            with self.subTest(name=name):
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        **changes,
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertFalse(report["human_decision_recorded"])
                self.assertFalse(validation["human_decision_recorded"])
                self.assertIsNone(validation["normalized_record"])
                for reason in expected_reasons:
                    self.assertIn(reason, validation["reasons"])
                for unsafe_token in unsafe_tokens:
                    self.assertNotIn(unsafe_token, serialized_report)

    def test_default_report_timestamp_is_deterministic(self) -> None:
        first_report = build_phase14c_candidate_decision_support_report()
        second_report = build_phase14c_candidate_decision_support_report()
        custom_report = build_phase14c_candidate_decision_support_report(
            generated_at_utc="2026-06-25T05:00:00+00:00"
        )

        self.assertEqual(first_report["generated_at_utc"], "2026-06-25T00:00:00+00:00")
        self.assertEqual(first_report["generated_at_utc"], second_report["generated_at_utc"])
        self.assertEqual(custom_report["generated_at_utc"], "2026-06-25T05:00:00+00:00")

    def test_checklist_preserves_non_authorization_boundary(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        checklist = "\n".join(report["preflight_checklist"])

        self.assertIn("Decision record is unfilled by default.", checklist)
        self.assertIn("Decision option remains unselected.", checklist)
        self.assertIn("No approve, reject, or defer decision is recorded.", checklist)
        self.assertIn("Phase 14-C remains blocked.", checklist)
        self.assertIn("Candidate is not approved, authorized, activated, or run.", checklist)
        self.assertIn("Todoist, Gmail, Calendar, OpenClaw", checklist)

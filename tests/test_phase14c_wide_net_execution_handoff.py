import json
import os
import unittest
from unittest import mock

from personalos.phase14c_wide_net_execution_handoff import (
    PHASE14C_WIDE_NET_EVIDENCE_BLOCKED,
    PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
    PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_STATUS,
    PHASE14C_WIDE_NET_EVIDENCE_VALID,
    PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS,
    build_phase14c_wide_net_evidence_input_size_report,
    build_phase14c_wide_net_evidence_template_report,
    build_phase14c_wide_net_execution_handoff_report,
    validate_phase14c_wide_net_evidence_report,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
)


class Phase14CWideNetExecutionHandoffTest(unittest.TestCase):
    def test_handoff_report_is_inert_and_includes_calendar_contract(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            report = build_phase14c_wide_net_execution_handoff_report()
        serialized = json.dumps(report, sort_keys=True)
        handoff = report["calendar_connector_handoff"]

        self.assertEqual(report["status"], PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertFalse(report["ready_for_live_execution"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["calendar_app_connector_called"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertIn(
            "wide-net-rehearsal --execute-live",
            report["execution_command_template"],
        )
        self.assertIn(
            "wide-net-evidence-validate",
            report["post_run_evidence_validator"]["command"],
        )
        self.assertTrue(
            any(
                "wide-net-calendar-transcript-template --json" in command
                for command in report["preflight_commands"]
            )
        )
        self.assertTrue(
            any(
                "wide-net-calendar-transcript-validate --input-file" in command
                for command in report["preflight_commands"]
            )
        )
        self.assertTrue(
            any(
                "wide-net-evidence-template --json" in command
                for command in report["preflight_commands"]
            )
        )
        self.assertIn(
            "wide-net-calendar-transcript-validate",
            handoff["sanitized_transcript_validator_command"],
        )
        self.assertFalse(report["post_run_evidence_validator"]["raw_evidence_echoed"])
        self.assertEqual(
            report["post_run_evidence_validator"]["max_input_file_size_bytes"],
            PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
        )
        self.assertEqual(
            report["post_run_evidence_validator"]["redaction_scan_max_depth"],
            32,
        )
        self.assertEqual(
            report["post_run_evidence_validator"]["redaction_scan_max_nodes"],
            5000,
        )
        self.assertEqual(
            handoff["duplicate_precheck_args"]["query"],
            PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        )
        self.assertEqual(
            handoff["calendar_create_args"]["title"],
            PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        )
        self.assertTrue(handoff["create_allowed_only_after_matching_event_count_zero"])
        self.assertEqual(report["call_budgets"]["openrouter_primary_calls"], 1)
        self.assertEqual(report["call_budgets"]["calendar_event_create_calls"], 1)
        self.assertEqual(
            report["call_budgets"]["protected_openclaw_runtime_invocation_calls"],
            0,
        )
        self.assertIn(WIDE_NET_PASSED, report["expected_complete_statuses"])
        self.assertIn(
            WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
            report["expected_complete_statuses"],
        )
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, serialized)

    def test_evidence_template_is_inert_and_not_accepted_as_evidence(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            template = build_phase14c_wide_net_evidence_template_report()
        serialized = json.dumps(template, sort_keys=True)
        fillable = template["fillable_evidence_shape"]

        self.assertEqual(template["status"], PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_STATUS)
        self.assertEqual(template["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertFalse(template["ready_for_live_execution"])
        self.assertTrue(template["template_only_not_authorization"])
        self.assertTrue(template["human_live_approval_still_required"])
        self.assertFalse(template["calendar_app_connector_called"])
        self.assertFalse(template["credential_values_read"])
        self.assertFalse(template["external_mutation"])
        self.assertTrue(template["template_payload_is_not_evidence"])
        self.assertTrue(
            template["template_payload_expected_to_fail_validator_until_filled"]
        )
        self.assertIn(
            "wide-net-evidence-validate",
            template["post_run_evidence_validator_command"],
        )
        self.assertIn(
            "wide-net-calendar-transcript-validate",
            template["calendar_transcript_validator_command"],
        )
        self.assertEqual(template["call_budgets"]["calendar_event_create_calls"], 1)
        self.assertEqual(
            template["call_budgets"]["protected_openclaw_runtime_invocation_calls"],
            0,
        )
        blocked = validate_phase14c_wide_net_evidence_report(fillable)
        self.assertEqual(blocked["status"], PHASE14C_WIDE_NET_EVIDENCE_BLOCKED)
        self.assertFalse(blocked["accepted"])
        self.assertIn(
            "wide_net_status_is_not_complete_pass",
            blocked["failure_reasons"],
        )
        self.assertIn(
            "openrouter_primary_calls_missing_or_not_int",
            blocked["failure_reasons"],
        )
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, serialized)

    def test_evidence_validator_accepts_sanitized_complete_evidence(self) -> None:
        validation = validate_phase14c_wide_net_evidence_report(
            {"wide_net_rehearsal": _valid_evidence()}
        )

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_EVIDENCE_VALID)
        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["failure_reasons"], [])
        self.assertEqual(validation["evidence_status"], WIDE_NET_PASSED)
        self.assertTrue(validation["marker_matched"])
        self.assertFalse(validation["raw_evidence_returned"])
        self.assertFalse(validation["input_values_echoed"])
        self.assertFalse(validation["credential_values_reported"])
        self.assertFalse(validation["unmasked_emails_reported"])
        self.assertEqual(
            validation["max_input_file_size_bytes"],
            PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
        )
        self.assertEqual(validation["call_counts"]["openrouter_primary_calls"], 1)
        self.assertEqual(validation["call_counts"]["gmail_email_send_calls"], 1)
        self.assertEqual(
            validation["calendar_precheck_summary"]["matching_event_count"],
            0,
        )
        self.assertFalse(
            validation["calendar_precheck_summary"]["attendee_addresses_logged"]
        )

    def test_evidence_validator_blocks_over_budget_and_redacts_raw_input(self) -> None:
        unsafe = {
            **_valid_evidence(),
            "call_limits": {
                **_valid_evidence()["call_limits"],
                "gmail_email_send_calls": 2,
            },
            "api_key": "secret-openrouter-key",
            "gmail_result": {"recipient": "chris@example.com"},
        }

        validation = validate_phase14c_wide_net_evidence_report(unsafe)
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_EVIDENCE_BLOCKED)
        self.assertFalse(validation["accepted"])
        self.assertIn(
            "gmail_email_send_calls_over_budget",
            validation["failure_reasons"],
        )
        self.assertIn("forbidden_raw_field_present", validation["failure_reasons"])
        self.assertIn("unmasked_email_value_present", validation["failure_reasons"])
        self.assertIn("secret_like_value_present", validation["failure_reasons"])
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_evidence_validator_blocks_scan_limit_failures(self) -> None:
        evidence: dict[str, object] = _valid_evidence()
        nested: object = "safe"
        for _ in range(40):
            nested = {"child": nested}
        evidence["nested_evidence"] = nested

        validation = validate_phase14c_wide_net_evidence_report(evidence)

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_EVIDENCE_BLOCKED)
        self.assertFalse(validation["accepted"])
        self.assertIn(
            "redaction_scan_depth_limit_exceeded",
            validation["failure_reasons"],
        )
        self.assertFalse(validation["raw_evidence_returned"])
        self.assertFalse(validation["input_values_echoed"])

    def test_evidence_input_size_report_blocks_without_input_values(self) -> None:
        validation = build_phase14c_wide_net_evidence_input_size_report(
            PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES + 1
        )
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_EVIDENCE_BLOCKED)
        self.assertFalse(validation["accepted"])
        self.assertEqual(validation["failure_reasons"], ["input_file_too_large"])
        self.assertEqual(
            validation["input_file_size_bytes"],
            PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES + 1,
        )
        self.assertFalse(validation["raw_evidence_returned"])
        self.assertFalse(validation["input_values_echoed"])
        self.assertNotIn(PHASE14C_WIDE_NET_REHEARSAL_MARKER, serialized)


def _valid_evidence() -> dict[str, object]:
    return {
        "status": WIDE_NET_PASSED,
        "rail": "wide_net_rehearsal",
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "call_limits": {
            "openrouter_primary_calls": 1,
            "openrouter_fallback_calls": 0,
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 1,
            "calendar_duplicate_precheck_calls": 1,
            "calendar_event_create_calls": 1,
            "protected_openclaw_runtime_invocation_calls": 0,
        },
        "calendar_duplicate_precheck": {
            "performed": True,
            "matching_event_count": 0,
            "duplicate_marker_found": False,
            "event_details_logged": False,
            "attendee_addresses_logged": False,
        },
        "model_diagnostic": {
            "diagnostic_only": True,
            "model_output_drives_external_writes": False,
            "prompt_logged": False,
            "raw_provider_response_logged": False,
            "generated_model_text_logged": False,
            "configured_model_ids_logged": False,
            "credential_values_logged": False,
        },
        "todoist_task_created": True,
        "gmail_email_sent": True,
        "calendar_event_created": True,
        "mutation_state": "confirmed_task_email_and_calendar_event_created",
        "safety_assertions": {
            "credential_values_read": True,
            "credential_values_logged": False,
            "credential_values_committed": False,
            "environment_dumped": False,
            "live_clients_initialized": True,
            "model_provider_called": True,
            "external_mutation": True,
            "todoist_task_created": True,
            "gmail_email_sent": True,
            "calendar_event_created": True,
            "protected_openclaw_runtime_called": False,
            "scheduler_or_background_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "dynamic_cleaning_triggered": False,
            "broad_live_activation": False,
        },
    }


if __name__ == "__main__":
    unittest.main()

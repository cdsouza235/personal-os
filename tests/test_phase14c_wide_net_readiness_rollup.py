import inspect
import json
import os
import unittest
from pathlib import Path
from unittest import mock

import personalos.phase14c_wide_net_readiness_rollup as rollup_module
from personalos.phase14c_wide_net_readiness_rollup import (
    PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS,
    PHASE14C_WIDE_NET_READINESS_ROLLUP_TOP_LEVEL_FIELDS,
    build_phase14c_wide_net_readiness_rollup_report,
    validate_phase14c_wide_net_readiness_rollup_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "STATUS.md"
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"


class Phase14CWideNetReadinessRollupTest(unittest.TestCase):
    def test_rollup_is_inert_summary_only_and_non_authorizing(self) -> None:
        secret_environment = {
            "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD": "secret-gmail-password",
            "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL": "secret-calendar-label",
        }
        with mock.patch.dict(os.environ, secret_environment, clear=True):
            report = build_phase14c_wide_net_readiness_rollup_report()

        serialized = json.dumps(report, sort_keys=True)
        safety = report["safety_assertions"]
        non_authorization = report["non_authorization"]

        self.assertEqual(report["status"], PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertEqual(
            report["ssl_cert_file_required"],
            PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        )
        self.assertTrue(report["repo_local_rollup_complete"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertFalse(report["config_values_reported"])
        self.assertFalse(report["present_config_names_reported"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertTrue(report["readiness"]["inert_report_only"])
        self.assertFalse(report["readiness"]["live_rails_activated"])
        self.assertTrue(non_authorization["repo_merge_is_not_live_authorization"])
        self.assertTrue(non_authorization["rollup_is_not_live_authorization"])
        self.assertFalse(non_authorization["phase14c_authorized"])
        self.assertFalse(non_authorization["live_service_access_authorized"])
        self.assertFalse(non_authorization["credential_handling_authorized"])
        self.assertFalse(non_authorization["dynamic_cleaning_authorized"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["calendar_app_connector_called"])
        self.assertFalse(safety["calendar_client_injected_into_runner"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["todoist_task_created"])
        self.assertFalse(safety["gmail_email_sent"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertFalse(safety["protected_openclaw_runtime_called"])
        self.assertFalse(safety["raw_fixture_payloads_returned"])
        self.assertFalse(safety["raw_evidence_echoed"])
        self.assertFalse(safety["raw_calendar_details_echoed"])
        self.assertFalse(safety["attendee_addresses_echoed"])
        self.assertFalse(safety["raw_provider_response_logged"])
        self.assertFalse(safety["full_prompt_logged"])
        self.assertFalse(safety["configured_model_ids_logged"])
        self.assertIn(
            "PERSONALOS_OPENCLAW_MODEL_API_KEY",
            report["required_config_entry_names"],
        )
        for secret_value in secret_environment.values():
            self.assertNotIn(secret_value, serialized)

    def test_rollup_summarizes_existing_components_without_raw_payloads(self) -> None:
        report = build_phase14c_wide_net_readiness_rollup_report()
        serialized = json.dumps(report, sort_keys=True)
        statuses = report["component_statuses"]
        readiness = report["component_readiness"]
        rehearsal = report["evidence_rehearsal_summary"]

        self.assertEqual(
            statuses["wide_net_rehearsal_plan"],
            "phase14c_wide_net_rehearsal_plan_ready",
        )
        self.assertEqual(
            statuses["calendar_bridge_payloads"],
            "phase14c_wide_net_calendar_app_bridge_payloads_ready",
        )
        self.assertEqual(
            statuses["calendar_transcript_template"],
            "phase14c_wide_net_calendar_transcript_template_ready",
        )
        self.assertEqual(
            statuses["calendar_operator_packet"],
            "phase14c_wide_net_calendar_operator_packet_ready",
        )
        self.assertEqual(
            statuses["execution_handoff"],
            "phase14c_wide_net_execution_handoff_ready",
        )
        self.assertEqual(
            statuses["evidence_template"],
            "phase14c_wide_net_evidence_template_ready",
        )
        self.assertEqual(
            statuses["evidence_rehearsal"],
            "phase14c_wide_net_evidence_rehearsal_passed",
        )
        self.assertEqual(
            statuses["local_preflight"],
            "phase14c_wide_net_local_preflight_reported",
        )
        self.assertTrue(readiness["local_preflight_report_available"])
        self.assertTrue(readiness["calendar_operator_packet_available"])
        self.assertTrue(readiness["calendar_operator_packet_contract_valid"])
        self.assertTrue(readiness["synthetic_evidence_rehearsal_passed"])
        self.assertTrue(readiness["wide_net_runner_available_but_fail_closed"])
        self.assertFalse(readiness["calendar_cli_connector_wiring_present"])
        self.assertTrue(rehearsal["accepted"])
        self.assertTrue(rehearsal["synthetic_fixture_only"])
        self.assertTrue(rehearsal["not_live_evidence"])
        self.assertFalse(rehearsal["synthetic_fixture_payloads_returned"])
        self.assertTrue(rehearsal["calendar_transcript_accepted"])
        self.assertTrue(rehearsal["wide_net_evidence_accepted"])
        self.assertTrue(rehearsal["crosscheck_accepted"])
        self.assertEqual(rehearsal["calendar_event_create_calls"], 1)
        self.assertEqual(rehearsal["precheck_matching_event_count"], 0)
        self.assertNotIn('"connector_args":', serialized)
        self.assertNotIn("sanitized_result", serialized)
        self.assertNotIn("normalized_response", serialized)
        self.assertNotIn("evt_", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_rollup_contract_validator_accepts_default_report(self) -> None:
        report = build_phase14c_wide_net_readiness_rollup_report()
        validation = validate_phase14c_wide_net_readiness_rollup_report_contract(
            report
        )

        self.assertEqual(
            tuple(report),
            PHASE14C_WIDE_NET_READINESS_ROLLUP_TOP_LEVEL_FIELDS,
        )
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": [
                    "wide_net_readiness_rollup_remains_inert_and_non_authorizing"
                ],
            },
        )

    def test_rollup_contract_validator_blocks_missing_report(self) -> None:
        validation = validate_phase14c_wide_net_readiness_rollup_report_contract(
            None
        )

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": False,
                "reasons": ["wide_net_readiness_rollup_report_missing"],
            },
        )

    def test_rollup_contract_validator_blocks_drift_without_echo(self) -> None:
        cases = (
            (
                "status",
                lambda report, token: report.update({"status": token}),
                "wide_net_readiness_rollup_status_drifted",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "wide_net_readiness_rollup_readiness_drifted",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {"phase14c_authorized": token}
                ),
                "wide_net_readiness_rollup_non_authorization_drifted",
            ),
            (
                "safety",
                lambda report, token: report["safety_assertions"].update(
                    {"calendar_event_created": token}
                ),
                "wide_net_readiness_rollup_safety_assertions_drifted",
            ),
            (
                "component",
                lambda report, token: report["component_statuses"].update(
                    {"evidence_rehearsal": token}
                ),
                "wide_net_readiness_rollup_component_statuses_drifted",
            ),
            (
                "gate",
                lambda report, token: report["remaining_gates_before_live"][0].update(
                    {"gate": token}
                ),
                "wide_net_readiness_rollup_remaining_gates_drifted",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"secret-rollup-{label}"
                report = build_phase14c_wide_net_readiness_rollup_report()
                mutate(report, unsafe_value)

                validation = validate_phase14c_wide_net_readiness_rollup_report_contract(
                    report
                )
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_rollup_contract_validator_blocks_raw_fields_without_echo(self) -> None:
        report = build_phase14c_wide_net_readiness_rollup_report()
        report["api_key"] = "sk-secret-rollup-key"
        report["evidence_rehearsal_summary"]["operator_email"] = (
            "chris.private@example.com"
        )

        validation = validate_phase14c_wide_net_readiness_rollup_report_contract(
            report
        )
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_readiness_rollup_top_level_fields_drifted",
            validation.reasons,
        )
        self.assertIn("forbidden_raw_field_present", validation.reasons)
        self.assertIn("secret_like_value_present", validation.reasons)
        self.assertIn("unmasked_email_value_present", validation.reasons)
        self.assertNotIn("sk-secret-rollup-key", serialized_validation)
        self.assertNotIn("chris.private@example.com", serialized_validation)

    def test_rollup_records_remaining_live_gates_and_commands(self) -> None:
        report = build_phase14c_wide_net_readiness_rollup_report()
        gates = {gate["gate"]: gate for gate in report["remaining_gates_before_live"]}
        command_names = {command["name"] for command in report["commands"]}

        for gate in (
            "fresh_explicit_human_live_approval",
            "claude_code_read_only_audit_before_live_run",
            "audited_calendar_connector_wiring",
            "ssl_cert_file_available_for_live_attempt",
            "openrouter_balance_or_provider_budget_checked",
            "sanitized_calendar_transcript_recorded_after_connector_use",
            "sanitized_wide_net_evidence_recorded_after_live_run",
            "calendar_transcript_and_wide_net_evidence_crosschecked",
        ):
            with self.subTest(gate=gate):
                self.assertTrue(gates[gate]["required"])
                self.assertFalse(gates[gate]["satisfied_by_this_report"])

        self.assertEqual(
            command_names,
            {
                "plan",
                "calendar_bridge_payloads",
                "calendar_transcript_template",
                "calendar_operator_packet",
                "calendar_operator_packet_contract",
                "execution_handoff",
                "evidence_template",
                "evidence_rehearsal",
                "local_preflight",
                "wide_net_gate_default",
            },
        )
        self.assertTrue(
            all(command["live_action"] is False for command in report["commands"])
        )
        self.assertTrue(
            any(
                "wide-net-readiness-rollup" not in command["command"]
                for command in report["commands"]
            )
        )
        self.assertTrue(
            any(
                "wide-net-rehearsal --json" in command["command"]
                for command in report["commands"]
            )
        )

    def test_rollup_module_does_not_use_io_or_live_clients(self) -> None:
        source = inspect.getsource(rollup_module)

        forbidden_snippets = (
            "os.environ",
            "open(",
            "urllib",
            "smtplib",
            "sqlite3",
            "subprocess",
            "requests",
            "httpx",
        )
        for snippet in forbidden_snippets:
            with self.subTest(snippet=snippet):
                self.assertNotIn(snippet, source)

    def test_docs_record_rollup_command_and_non_authorization(self) -> None:
        combined_text = " ".join(
            (
                _normalized_doc_text(README),
                _normalized_doc_text(WIDE_NET_DOC),
                _normalized_doc_text(STATUS),
            )
        )

        required_phrases = (
            "phase14c wide-net-readiness-rollup --json",
            "phase14c wide-net-readiness-rollup-contract",
            "phase14c wide-net-local-preflight --json",
            "wide-net readiness rollup",
            "wide-net local preflight",
            "does not read credentials",
            "does not call connectors",
            "does not authorize a live run",
            "remaining human and connector gates",
            "synthetic evidence rehearsal",
            "not live evidence",
            "contract",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined_text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())

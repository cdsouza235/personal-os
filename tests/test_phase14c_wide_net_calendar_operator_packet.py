import inspect
import json
import unittest
from pathlib import Path

import personalos.phase14c_wide_net_calendar_operator_packet as packet_module
from personalos.phase14c_wide_net_calendar_operator_packet import (
    PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS,
    PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TOP_LEVEL_FIELDS,
    build_phase14c_wide_net_calendar_operator_packet_report,
    validate_phase14c_wide_net_calendar_operator_packet_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "STATUS.md"
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"


class Phase14CWideNetCalendarOperatorPacketTest(unittest.TestCase):
    def test_packet_composes_calendar_handoff_without_authorizing_live_use(self) -> None:
        report = build_phase14c_wide_net_calendar_operator_packet_report()
        validation = validate_phase14c_wide_net_calendar_operator_packet_report_contract(
            report
        )
        connector_readiness = report["calendar_connector_readiness_summary"]
        bridge = report["calendar_bridge_summary"]
        precheck = report["calendar_duplicate_precheck"]
        create = report["calendar_create"]
        transcript = report["calendar_transcript_summary"]
        human_gate = report["human_gate_summary"]

        self.assertEqual(tuple(report), PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TOP_LEVEL_FIELDS)
        self.assertEqual(report["status"], PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertTrue(report["operator_packet_complete"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["calendar_connector_use_authorized"])
        self.assertFalse(report["calendar_app_connector_called"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertTrue(
            connector_readiness["calendar_connector_readiness_available"]
        )
        self.assertTrue(
            connector_readiness["calendar_connector_readiness_contract_valid"]
        )
        self.assertTrue(
            connector_readiness["requires_injected_search_events_callable"]
        )
        self.assertTrue(
            connector_readiness["requires_injected_create_event_callable"]
        )
        self.assertFalse(connector_readiness["calendar_cli_connector_wiring_present"])
        self.assertFalse(connector_readiness["calendar_connector_use_authorized"])
        self.assertFalse(connector_readiness["calendar_app_connector_called"])
        self.assertFalse(connector_readiness["calendar_client_injected_into_runner"])
        self.assertFalse(connector_readiness["ready_for_live_execution"])
        self.assertFalse(
            connector_readiness["wide_net_live_run_authorized_by_this_report"]
        )
        self.assertTrue(bridge["calendar_bridge_payloads_available"])
        self.assertFalse(bridge["repo_cli_constructs_connector"])
        self.assertFalse(bridge["repo_cli_calls_connector"])
        self.assertEqual(precheck["connector_action"], "search_events")
        self.assertEqual(precheck["matching_event_count_must_equal"], 0)
        self.assertFalse(precheck["event_details_logged"])
        self.assertFalse(precheck["attendee_addresses_logged"])
        self.assertEqual(create["connector_action"], "create_event")
        self.assertEqual(create["attendee_count"], 0)
        self.assertFalse(create["conference_link"])
        self.assertIsNone(create["recurrence"])
        self.assertTrue(transcript["calendar_transcript_template_available"])
        self.assertFalse(transcript["raw_event_details_allowed"])
        self.assertFalse(transcript["attendee_addresses_allowed"])
        self.assertTrue(human_gate["human_gate_packet_command_available"])
        self.assertTrue(human_gate["human_gate_packet_contract_command_available"])
        self.assertTrue(
            human_gate[
                "repo_local_preconditions_not_asserted_by_calendar_operator_packet"
            ]
        )
        self.assertTrue(human_gate["fresh_human_message_required"])
        self.assertTrue(human_gate["approval_request_template_is_not_approval"])
        self.assertTrue(human_gate["calendar_connector_wiring_still_required"])
        self.assertFalse(human_gate["ready_for_live_execution"])
        self.assertFalse(human_gate["wide_net_live_run_authorized_by_this_report"])
        self.assertFalse(report["non_authorization"]["calendar_connector_use_authorized"])
        self.assertFalse(report["safety_assertions"]["calendar_app_connector_called"])
        self.assertFalse(report["safety_assertions"]["calendar_event_created"])
        self.assertTrue(validation.report_matches_inert_contract)

    def test_packet_includes_bounded_connector_args(self) -> None:
        report = build_phase14c_wide_net_calendar_operator_packet_report()
        precheck_args = report["calendar_duplicate_precheck"]["connector_args"]
        create_args = report["calendar_create"]["connector_args"]

        self.assertEqual(precheck_args["calendar_id"], "primary")
        self.assertEqual(precheck_args["max_results"], 10)
        self.assertEqual(
            precheck_args["query"],
            "[Phase 14-C Wide Test] Evening Reset Coordination",
        )
        self.assertEqual(create_args["calendar_id"], "primary")
        self.assertEqual(create_args["title"], precheck_args["query"])
        self.assertEqual(create_args["attendees"], [])
        self.assertFalse(create_args["add_google_meet"])
        self.assertIsNone(create_args["recurrence"])

    def test_validator_blocks_live_authorization_drift_without_echo(self) -> None:
        report = build_phase14c_wide_net_calendar_operator_packet_report()
        unsafe_value = "sk-calendar-operator-secret"
        report["ready_for_live_execution"] = True
        report["calendar_bridge_summary"]["connector_type"] = unsafe_value

        validation = validate_phase14c_wide_net_calendar_operator_packet_report_contract(
            report
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_calendar_operator_packet_ready_for_live_execution_must_remain_false",
            validation.reasons,
        )
        self.assertIn(
            "wide_net_calendar_operator_packet_calendar_bridge_summary_drifted",
            validation.reasons,
        )
        self.assertIn("secret_like_value_present", validation.reasons)
        self.assertNotIn(unsafe_value, serialized)

    def test_validator_blocks_calendar_create_shape_drift(self) -> None:
        report = build_phase14c_wide_net_calendar_operator_packet_report()
        report["calendar_create"]["connector_args"]["attendees"] = [
            "leak@example.com"
        ]

        validation = validate_phase14c_wide_net_calendar_operator_packet_report_contract(
            report
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_calendar_operator_packet_calendar_create_drifted",
            validation.reasons,
        )
        self.assertIn("unmasked_email_value_present", validation.reasons)
        self.assertNotIn("leak@example.com", serialized)

    def test_module_does_not_use_io_env_or_live_clients(self) -> None:
        source = inspect.getsource(packet_module)

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



def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

import inspect
import json
import unittest
from pathlib import Path

import personalos.phase14c_wide_net_calendar_connector_readiness as readiness_module
from personalos.phase14c_wide_net_calendar_connector_readiness import (
    PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS,
    PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TOP_LEVEL_FIELDS,
    build_phase14c_wide_net_calendar_connector_readiness_report,
    validate_phase14c_wide_net_calendar_connector_readiness_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "STATUS.md"
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"


class Phase14CWideNetCalendarConnectorReadinessTest(unittest.TestCase):
    def test_report_describes_wiring_boundary_without_authorizing_live_use(
        self,
    ) -> None:
        report = build_phase14c_wide_net_calendar_connector_readiness_report()
        validation = (
            validate_phase14c_wide_net_calendar_connector_readiness_report_contract(
                report
            )
        )
        payload_summary = report["bridge_payload_summary"]
        injection = report["bridge_injection_contract"]
        precheck = report["precheck_wiring_contract"]
        create = report["create_wiring_contract"]

        self.assertEqual(
            tuple(report),
            PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TOP_LEVEL_FIELDS,
        )
        self.assertEqual(
            report["status"],
            PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS,
        )
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertTrue(report["connector_readiness_report_complete"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["calendar_connector_use_authorized"])
        self.assertFalse(report["calendar_app_connector_called"])
        self.assertFalse(report["calendar_client_constructed"])
        self.assertFalse(report["calendar_client_injected_into_runner"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertTrue(payload_summary["app_bridge_payloads_available"])
        self.assertEqual(payload_summary["precheck_calendar_id"], "primary")
        self.assertEqual(payload_summary["precheck_max_results"], 10)
        self.assertEqual(payload_summary["create_calendar_id"], "primary")
        self.assertEqual(payload_summary["create_attendee_count"], 0)
        self.assertFalse(payload_summary["create_adds_google_meet"])
        self.assertIsNone(payload_summary["create_recurrence"])
        self.assertEqual(injection["bridge_class"], "WideNetGoogleCalendarConnectorBridge")
        self.assertTrue(injection["requires_injected_search_events_callable"])
        self.assertTrue(injection["requires_injected_create_event_callable"])
        self.assertFalse(injection["connector_imported_or_constructed_by_this_report"])
        self.assertFalse(injection["connector_callables_bound_by_this_report"])
        self.assertFalse(injection["wide_net_runner_calendar_client_available"])
        self.assertFalse(injection["calendar_client_injected_into_runner_by_this_report"])
        self.assertEqual(precheck["connector_action"], "search_events")
        self.assertEqual(precheck["matching_event_count_must_equal"], 0)
        self.assertFalse(precheck["event_details_logged"])
        self.assertFalse(precheck["attendee_addresses_logged"])
        self.assertEqual(create["connector_action"], "create_event")
        self.assertEqual(create["calendar_id"], "primary")
        self.assertEqual(create["attendee_count"], 0)
        self.assertFalse(create["conference_link"])
        self.assertIsNone(create["recurrence"])
        self.assertFalse(report["non_authorization"]["calendar_connector_use_authorized"])
        self.assertFalse(report["non_authorization"]["calendar_write_authorized"])
        self.assertFalse(report["safety_assertions"]["calendar_app_connector_called"])
        self.assertFalse(report["safety_assertions"]["calendar_client_constructed"])
        self.assertFalse(
            report["safety_assertions"]["calendar_client_injected_into_runner"]
        )
        self.assertTrue(validation.report_matches_inert_contract)

    def test_validator_blocks_live_authorization_drift_without_echo(self) -> None:
        report = build_phase14c_wide_net_calendar_connector_readiness_report()
        unsafe_value = "sk-calendar-connector-secret"
        report["ready_for_live_execution"] = True
        report["bridge_payload_summary"]["connector_type"] = unsafe_value

        validation = (
            validate_phase14c_wide_net_calendar_connector_readiness_report_contract(
                report
            )
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_calendar_connector_readiness_ready_for_live_execution_must_remain_false",
            validation.reasons,
        )
        self.assertIn(
            "wide_net_calendar_connector_readiness_bridge_payload_summary_drifted",
            validation.reasons,
        )
        self.assertIn("secret_like_value_present", validation.reasons)
        self.assertNotIn(unsafe_value, serialized)

    def test_validator_blocks_unmasked_email_without_echo(self) -> None:
        report = build_phase14c_wide_net_calendar_connector_readiness_report()
        report["create_wiring_contract"]["calendar_id"] = "leak@example.com"

        validation = (
            validate_phase14c_wide_net_calendar_connector_readiness_report_contract(
                report
            )
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_calendar_connector_readiness_create_wiring_contract_drifted",
            validation.reasons,
        )
        self.assertIn("unmasked_email_value_present", validation.reasons)
        self.assertNotIn("leak@example.com", serialized)

    def test_module_does_not_use_io_env_or_live_clients(self) -> None:
        source = inspect.getsource(readiness_module)

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

    def test_docs_record_calendar_connector_readiness(self) -> None:
        combined_text = " ".join(
            (
                _normalized_doc_text(README),
                _normalized_doc_text(WIDE_NET_DOC),
                _normalized_doc_text(STATUS),
            )
        )

        required_phrases = (
            "phase14c wide-net-calendar-connector-readiness --json",
            "phase14c wide-net-calendar-connector-readiness-contract --json",
            "wide-net calendar connector readiness",
            "calendar_cli_connector_wiring_present=false",
            "calendar_connector_use_authorized=false",
            "calendar_app_connector_called=false",
            "calendar_client_injected_into_runner=false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined_text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

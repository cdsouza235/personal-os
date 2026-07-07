import inspect
import json
import unittest
from pathlib import Path

import personalos.phase14c_wide_net_human_gate_packet as packet_module
from personalos.phase14c_wide_net_human_gate_packet import (
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED,
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED,
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TOP_LEVEL_FIELDS,
    build_phase14c_wide_net_human_gate_packet_report,
    validate_phase14c_wide_net_human_gate_packet_report_contract,
)
from personalos.phase14c_wide_net_local_preflight import (
    build_phase14c_wide_net_local_preflight_report,
)
from personalos.phase14c_wide_net_pre_run_checklist import (
    build_phase14c_wide_net_pre_run_checklist_report,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "STATUS.md"
FINAL_HANDOFF_DOC = REPO_ROOT / "docs" / "FINAL_NONHUMAN_HANDOFF.md"
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"


class Phase14CWideNetHumanGatePacketTest(unittest.TestCase):
    def test_default_packet_is_blocked_and_non_authorizing(self) -> None:
        report = build_phase14c_wide_net_human_gate_packet_report()
        validation = validate_phase14c_wide_net_human_gate_packet_report_contract(
            report
        )
        checklist = report["pre_run_checklist_summary"]
        handoff = report["execution_handoff_summary"]
        approval_template = report["human_approval_request_template"]

        self.assertEqual(tuple(report), PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TOP_LEVEL_FIELDS)
        self.assertEqual(report["status"], PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertTrue(report["packet_complete"])
        self.assertFalse(report["repo_local_preconditions_met"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertTrue(checklist["pre_run_checklist_contract_valid"])
        self.assertFalse(checklist["repo_local_preconditions_met"])
        self.assertFalse(checklist["present_config_names_reported"])
        self.assertFalse(checklist["available_config_entry_names_reported"])
        self.assertFalse(checklist["credential_values_read"])
        self.assertFalse(checklist["config_values_reported"])
        self.assertTrue(handoff["execution_handoff_available"])
        self.assertFalse(handoff["ready_for_live_execution"])
        self.assertEqual(handoff["call_budgets"]["openrouter_primary_calls"], 1)
        self.assertEqual(handoff["call_budgets"]["openrouter_fallback_calls"], 1)
        self.assertEqual(
            handoff["call_budgets"]["protected_openclaw_runtime_invocation_calls"],
            0,
        )
        self.assertTrue(approval_template["template_is_not_approval"])
        self.assertTrue(approval_template["fresh_human_message_required"])
        self.assertIn(
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            approval_template["suggested_human_approval_text"],
        )
        self.assertFalse(report["non_authorization"]["phase14c_authorized"])
        self.assertFalse(report["safety_assertions"]["calendar_app_connector_called"])
        self.assertFalse(report["safety_assertions"]["external_mutation"])
        self.assertTrue(validation.report_matches_inert_contract)

    def test_local_checks_passed_still_requires_human_approval(self) -> None:
        local_preflight = build_phase14c_wide_net_local_preflight_report(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            ssl_cert_file_is_file=True,
        )
        checklist = build_phase14c_wide_net_pre_run_checklist_report(
            local_preflight_report=local_preflight
        )
        report = build_phase14c_wide_net_human_gate_packet_report(
            pre_run_checklist_report=checklist
        )
        validation = validate_phase14c_wide_net_human_gate_packet_report_contract(
            report
        )

        self.assertEqual(
            report["status"],
            PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED,
        )
        self.assertTrue(report["repo_local_preconditions_met"])
        self.assertTrue(report["pre_run_checklist_summary"]["local_preflight_passed"])
        self.assertTrue(report["pre_run_checklist_summary"]["config_names_present"])
        self.assertTrue(report["pre_run_checklist_summary"]["ssl_cert_file_available"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(
            report["human_approval_request_template"]["template_is_not_approval"]
        )
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertTrue(validation.report_matches_inert_contract)

    def test_secret_values_are_not_echoed_from_checklist_input(self) -> None:
        secret_config = {
            name: f"secret-value-for-{name}" for name in WIDE_NET_REQUIRED_CONFIG_NAMES
        }
        secret_config["UNRELATED_SECRET_TOKEN"] = "sk-secret-human-gate"
        local_preflight = build_phase14c_wide_net_local_preflight_report(
            available_config_names=secret_config,
            ssl_cert_file_is_file=True,
        )
        checklist = build_phase14c_wide_net_pre_run_checklist_report(
            local_preflight_report=local_preflight
        )
        report = build_phase14c_wide_net_human_gate_packet_report(
            pre_run_checklist_report=checklist
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertTrue(report["pre_run_checklist_summary"]["local_preflight_passed"])
        self.assertFalse(
            report["pre_run_checklist_summary"]["present_config_names_reported"]
        )
        self.assertFalse(
            report["pre_run_checklist_summary"][
                "available_config_entry_names_reported"
            ]
        )
        self.assertNotIn("UNRELATED_SECRET_TOKEN", serialized)
        self.assertNotIn("sk-secret-human-gate", serialized)
        for value in secret_config.values():
            self.assertNotIn(value, serialized)

    def test_validator_blocks_live_authorization_drift_without_echo(self) -> None:
        report = build_phase14c_wide_net_human_gate_packet_report()
        unsafe_value = "secret-human-gate-drift"
        report["ready_for_live_execution"] = True
        report["human_approval_request_template"][
            "suggested_human_approval_text"
        ] = unsafe_value

        validation = validate_phase14c_wide_net_human_gate_packet_report_contract(
            report
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_human_gate_packet_ready_for_live_execution_must_remain_false",
            validation.reasons,
        )
        self.assertIn(
            "wide_net_human_gate_packet_approval_template_drifted",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized)

    def test_validator_blocks_budget_drift(self) -> None:
        report = build_phase14c_wide_net_human_gate_packet_report()
        report["execution_handoff_summary"]["call_budgets"][
            "calendar_event_create_calls"
        ] = 2

        validation = validate_phase14c_wide_net_human_gate_packet_report_contract(
            report
        )

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_human_gate_packet_execution_handoff_drifted",
            validation.reasons,
        )

    def test_module_does_not_use_io_or_live_clients(self) -> None:
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

import inspect
import json
import unittest
from pathlib import Path

import personalos.phase14c_wide_net_pre_run_checklist as checklist_module
from personalos.phase14c_wide_net_local_preflight import (
    build_phase14c_wide_net_local_preflight_report,
)
from personalos.phase14c_wide_net_pre_run_checklist import (
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED,
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED,
    build_phase14c_wide_net_pre_run_checklist_report,
    validate_phase14c_wide_net_pre_run_checklist_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "STATUS.md"
WIDE_NET_DOC = REPO_ROOT / "docs" / "PHASE_14C_WIDE_NET_REHEARSAL.md"


class Phase14CWideNetPreRunChecklistTest(unittest.TestCase):
    def test_default_checklist_is_blocked_and_non_authorizing(self) -> None:
        report = build_phase14c_wide_net_pre_run_checklist_report()
        validation = validate_phase14c_wide_net_pre_run_checklist_report_contract(
            report
        )
        local = report["local_preflight_summary"]
        decision = report["pre_run_decision"]
        safety = report["safety_assertions"]

        self.assertEqual(report["status"], PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertTrue(report["repo_local_checklist_complete"])
        self.assertFalse(report["repo_local_preconditions_met"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertTrue(report["rollup_contract"]["report_matches_inert_contract"])
        self.assertFalse(local["config_names_present"])
        self.assertFalse(local["ssl_cert_file_available"])
        self.assertFalse(local["local_preflight_passed"])
        self.assertEqual(
            local["missing_config_entry_names"],
            WIDE_NET_REQUIRED_CONFIG_NAMES,
        )
        self.assertFalse(local["present_config_names_reported"])
        self.assertFalse(local["available_config_entry_names_reported"])
        self.assertFalse(local["credential_values_read"])
        self.assertFalse(local["credential_values_logged"])
        self.assertFalse(local["config_values_reported"])
        self.assertFalse(local["ssl_cert_file_content_read"])
        self.assertEqual(decision["decision"], "blocked_by_human_or_external_gates")
        self.assertFalse(decision["live_execution_authorized"])
        self.assertTrue(decision["fresh_human_approval_required"])
        self.assertTrue(decision["claude_code_audit_required"])
        self.assertTrue(decision["calendar_connector_wiring_required"])
        self.assertTrue(decision["openrouter_budget_confirmation_required"])
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["calendar_app_connector_called"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertTrue(validation.report_matches_inert_contract)

    def test_local_checks_passed_still_keeps_human_gates(self) -> None:
        local_preflight = build_phase14c_wide_net_local_preflight_report(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            ssl_cert_file_is_file=True,
        )
        report = build_phase14c_wide_net_pre_run_checklist_report(
            local_preflight_report=local_preflight
        )
        validation = validate_phase14c_wide_net_pre_run_checklist_report_contract(
            report
        )
        gates = {gate["gate"]: gate for gate in report["remaining_human_or_external_gates"]}

        self.assertEqual(
            report["status"],
            PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED,
        )
        self.assertTrue(report["repo_local_preconditions_met"])
        self.assertTrue(report["local_preflight_summary"]["local_preflight_passed"])
        self.assertTrue(report["local_preflight_summary"]["config_names_present"])
        self.assertTrue(report["local_preflight_summary"]["ssl_cert_file_available"])
        self.assertEqual(report["local_preflight_summary"]["missing_config_entry_names"], ())
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertFalse(report["pre_run_decision"]["live_execution_authorized"])
        self.assertTrue(report["pre_run_decision"]["fresh_human_approval_required"])
        self.assertTrue(report["pre_run_decision"]["claude_code_audit_required"])
        self.assertTrue(report["pre_run_decision"]["calendar_connector_wiring_required"])
        self.assertTrue(gates["fresh_explicit_human_live_approval"]["required"])
        self.assertFalse(
            gates["fresh_explicit_human_live_approval"]["satisfied_by_checklist"]
        )
        self.assertTrue(gates["audited_calendar_connector_wiring"]["required"])
        self.assertFalse(
            gates["audited_calendar_connector_wiring"]["satisfied_by_checklist"]
        )
        self.assertTrue(validation.report_matches_inert_contract)

    def test_secret_values_are_not_echoed_from_local_preflight_input(self) -> None:
        secret_config = {
            name: f"secret-value-for-{name}" for name in WIDE_NET_REQUIRED_CONFIG_NAMES
        }
        secret_config["UNRELATED_SECRET_TOKEN"] = "sk-secret-pre-run-checklist"
        local_preflight = build_phase14c_wide_net_local_preflight_report(
            available_config_names=secret_config,
            ssl_cert_file_is_file=True,
        )
        report = build_phase14c_wide_net_pre_run_checklist_report(
            local_preflight_report=local_preflight
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertTrue(report["local_preflight_summary"]["local_preflight_passed"])
        self.assertFalse(report["local_preflight_summary"]["present_config_names_reported"])
        self.assertFalse(
            report["local_preflight_summary"]["available_config_entry_names_reported"]
        )
        self.assertNotIn("UNRELATED_SECRET_TOKEN", serialized)
        self.assertNotIn("sk-secret-pre-run-checklist", serialized)
        for value in secret_config.values():
            self.assertNotIn(value, serialized)

    def test_validator_blocks_authorization_drift_without_echo(self) -> None:
        report = build_phase14c_wide_net_pre_run_checklist_report()
        unsafe_value = "secret-pre-run-drift"
        report["ready_for_live_execution"] = True
        report["pre_run_decision"]["decision"] = unsafe_value

        validation = validate_phase14c_wide_net_pre_run_checklist_report_contract(
            report
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_pre_run_checklist_ready_for_live_execution_must_remain_false",
            validation.reasons,
        )
        self.assertIn("wide_net_pre_run_checklist_decision_drifted", validation.reasons)
        self.assertNotIn(unsafe_value, serialized)

    def test_validator_blocks_raw_fields_without_echo(self) -> None:
        report = build_phase14c_wide_net_pre_run_checklist_report()
        report["api_key"] = "sk-secret-pre-run"
        report["local_preflight_summary"]["operator_email"] = "chris@example.com"

        validation = validate_phase14c_wide_net_pre_run_checklist_report_contract(
            report
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_pre_run_checklist_top_level_fields_drifted",
            validation.reasons,
        )
        self.assertIn("forbidden_raw_field_present", validation.reasons)
        self.assertIn("secret_like_value_present", validation.reasons)
        self.assertIn("unmasked_email_value_present", validation.reasons)
        self.assertNotIn("sk-secret-pre-run", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_module_does_not_use_io_or_live_clients(self) -> None:
        source = inspect.getsource(checklist_module)

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

    def test_docs_record_pre_run_checklist_and_non_authorization(self) -> None:
        combined_text = " ".join(
            (
                _normalized_doc_text(README),
                _normalized_doc_text(WIDE_NET_DOC),
                _normalized_doc_text(STATUS),
            )
        )

        required_phrases = (
            "phase14c wide-net-pre-run-checklist --json",
            "phase14c wide-net-pre-run-checklist-contract --json",
            "wide-net pre-run checklist",
            "repo-local checks pass",
            "fresh human approval",
            "claude code audit",
            "calendar connector wiring",
            "openrouter budget confirmation",
            "still cannot authorize a live run",
            "live_execution_authorized=false",
            "wide_net_live_run_authorized_by_this_report=false",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined_text)


def _normalized_doc_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


if __name__ == "__main__":
    unittest.main()

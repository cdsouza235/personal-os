import json
import unittest

from personalos.phase14c_wide_net_local_preflight import (
    PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS,
    build_phase14c_wide_net_local_preflight_report,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_REQUIRED_CONFIG_NAMES,
)


class Phase14CWideNetLocalPreflightTest(unittest.TestCase):
    def test_missing_names_report_is_non_authorizing_and_no_live(self) -> None:
        report = build_phase14c_wide_net_local_preflight_report(
            available_config_names=(),
            ssl_cert_file_is_file=False,
        )
        safety = report["safety_assertions"]

        self.assertEqual(report["status"], PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS)
        self.assertEqual(report["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(
            report["approval_reference_to_request"],
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        )
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["template_only_not_authorization"])
        self.assertTrue(report["human_live_approval_still_required"])
        self.assertTrue(report["claude_code_audit_required_before_live_run"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["credential_values_logged"])
        self.assertFalse(report["config_values_reported"])
        self.assertFalse(report["present_config_names_reported"])
        self.assertEqual(
            report["config_preflight"]["missing_config_entry_names"],
            WIDE_NET_REQUIRED_CONFIG_NAMES,
        )
        self.assertEqual(
            report["config_preflight"]["missing_config_entry_count"],
            len(WIDE_NET_REQUIRED_CONFIG_NAMES),
        )
        self.assertFalse(
            report["config_preflight"]["all_required_config_names_present"]
        )
        self.assertFalse(
            report["config_preflight"]["available_config_entry_names_reported"]
        )
        self.assertEqual(
            report["ssl_cert_file"]["path"],
            PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        )
        self.assertFalse(report["ssl_cert_file"]["is_file"])
        self.assertFalse(report["ssl_cert_file"]["content_read"])
        self.assertFalse(report["local_preflight"]["local_preflight_passed"])
        self.assertTrue(
            report["local_preflight"]["calendar_connector_wiring_still_required"]
        )
        self.assertTrue(
            report["local_preflight"]["openrouter_budget_check_still_required"]
        )
        self.assertTrue(
            report["local_preflight"]["fresh_human_live_approval_still_required"]
        )
        self.assertTrue(
            report["local_preflight"]["claude_code_audit_still_required"]
        )
        self.assertFalse(safety["credential_values_read"])
        self.assertFalse(safety["environment_dumped"])
        self.assertFalse(safety["ssl_cert_file_content_read"])
        self.assertFalse(safety["calendar_app_connector_called"])
        self.assertFalse(safety["external_mutation"])
        self.assertFalse(safety["model_provider_called"])
        self.assertFalse(safety["todoist_task_created"])
        self.assertFalse(safety["gmail_email_sent"])
        self.assertFalse(safety["calendar_event_created"])
        self.assertFalse(safety["protected_openclaw_runtime_called"])
        self.assertFalse(safety["scheduler_or_background_activated"])
        self.assertFalse(safety["production_db_active"])
        self.assertFalse(safety["protected_paths_touched"])
        self.assertFalse(safety["dynamic_cleaning_triggered"])
        self.assertFalse(safety["broad_live_activation"])

    def test_present_names_and_cert_still_do_not_authorize_live_execution(self) -> None:
        report = build_phase14c_wide_net_local_preflight_report(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            ssl_cert_file_is_file=True,
        )

        self.assertTrue(
            report["config_preflight"]["all_required_config_names_present"]
        )
        self.assertEqual(report["config_preflight"]["missing_config_entry_names"], ())
        self.assertTrue(report["ssl_cert_file"]["is_file"])
        self.assertTrue(report["local_preflight"]["local_preflight_passed"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertFalse(report["calendar_cli_connector_wiring_present"])
        self.assertTrue(
            report["local_preflight"]["calendar_connector_wiring_still_required"]
        )
        self.assertTrue(
            report["local_preflight"]["fresh_human_live_approval_still_required"]
        )

    def test_mapping_input_reports_names_only_without_values_or_present_names(
        self,
    ) -> None:
        secret_config = {
            name: f"secret-value-for-{name}" for name in WIDE_NET_REQUIRED_CONFIG_NAMES
        }
        secret_config["UNRELATED_SECRET_TOKEN"] = "sk-secret-local-preflight"

        report = build_phase14c_wide_net_local_preflight_report(
            available_config_names=secret_config,
            ssl_cert_file_is_file=True,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertTrue(report["local_preflight"]["local_preflight_passed"])
        self.assertFalse(report["present_config_names_reported"])
        self.assertFalse(
            report["config_preflight"]["available_config_entry_names_reported"]
        )
        self.assertNotIn("sk-secret-local-preflight", serialized)
        self.assertNotIn("UNRELATED_SECRET_TOKEN", serialized)
        for value in secret_config.values():
            self.assertNotIn(value, serialized)


if __name__ == "__main__":
    unittest.main()

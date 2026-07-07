import inspect
import json
import unittest

import personalos.phase14c_wide_net_dry_run as dry_run_module
from personalos.phase14c_wide_net_dry_run import (
    PHASE14C_WIDE_NET_DRY_RUN_PASSED,
    build_phase14c_wide_net_dry_run_report,
    validate_phase14c_wide_net_dry_run_report_contract,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
)


class Phase14CWideNetDryRunTest(unittest.TestCase):
    def test_dry_run_exercises_pass_model_failure_and_duplicate_stop_paths(self) -> None:
        report = build_phase14c_wide_net_dry_run_report()
        validation = validate_phase14c_wide_net_dry_run_report_contract(report)
        scenarios = {item["scenario"]: item for item in report["scenario_results"]}

        self.assertEqual(report["status"], PHASE14C_WIDE_NET_DRY_RUN_PASSED)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["wide_net_live_run_authorized_by_this_report"])
        self.assertTrue(report["fake_clients_used"])
        self.assertTrue(report["placeholder_values_used"])
        self.assertFalse(report["real_credential_values_read"])
        self.assertFalse(report["external_mutation"])
        self.assertEqual(set(scenarios), {"all_pass", "model_diagnostic_failure", "duplicate_calendar_marker"})

        all_pass = scenarios["all_pass"]
        self.assertEqual(all_pass["runner_status"], WIDE_NET_PASSED)
        self.assertEqual(all_pass["call_counts"]["openrouter_primary_calls"], 1)
        self.assertEqual(all_pass["call_counts"]["openrouter_fallback_calls"], 0)
        self.assertEqual(all_pass["call_counts"]["todoist_task_create_calls"], 1)
        self.assertEqual(all_pass["call_counts"]["gmail_email_send_calls"], 1)
        self.assertEqual(all_pass["call_counts"]["calendar_event_create_calls"], 1)

        model_failure = scenarios["model_diagnostic_failure"]
        self.assertEqual(
            model_failure["runner_status"],
            WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
        )
        self.assertEqual(model_failure["call_counts"]["openrouter_primary_calls"], 1)
        self.assertEqual(model_failure["call_counts"]["openrouter_fallback_calls"], 1)
        self.assertEqual(model_failure["call_counts"]["todoist_task_create_calls"], 1)
        self.assertEqual(model_failure["call_counts"]["gmail_email_send_calls"], 1)
        self.assertEqual(model_failure["call_counts"]["calendar_event_create_calls"], 1)
        self.assertFalse(
            model_failure["model_diagnostic"]["model_output_drives_external_writes"]
        )

        duplicate = scenarios["duplicate_calendar_marker"]
        self.assertEqual(duplicate["runner_status"], WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER)
        self.assertEqual(duplicate["call_counts"]["calendar_duplicate_precheck_calls"], 1)
        self.assertEqual(duplicate["call_counts"]["openrouter_primary_calls"], 0)
        self.assertEqual(duplicate["call_counts"]["todoist_task_create_calls"], 0)
        self.assertEqual(duplicate["call_counts"]["gmail_email_send_calls"], 0)
        self.assertEqual(duplicate["call_counts"]["calendar_event_create_calls"], 0)
        self.assertFalse(duplicate["simulated_runner_external_mutation"])

    def test_dry_run_report_does_not_expose_fake_values_or_payloads(self) -> None:
        report = build_phase14c_wide_net_dry_run_report()
        serialized = json.dumps(report, sort_keys=True)

        for forbidden in (
            "placeholder-openrouter-key",
            "placeholder-todoist-token",
            "placeholder-gmail-password",
            "placeholder-nemotron-model",
            "placeholder-glm-model",
            "phase14c@example.invalid",
            "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
            "dry-run-id-not-live",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(report["safety_assertions"]["raw_fake_payloads_returned"])
        self.assertFalse(report["safety_assertions"]["unmasked_emails_reported"])

    def test_contract_blocks_live_auth_drift_and_redaction_without_echo(self) -> None:
        report = build_phase14c_wide_net_dry_run_report()
        report["ready_for_live_execution"] = True
        report["marker"] = "sk-calendar-dry-run-secret"

        validation = validate_phase14c_wide_net_dry_run_report_contract(report)
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "wide_net_dry_run_ready_for_live_execution_must_remain_false",
            validation.reasons,
        )
        self.assertIn("secret_like_value_present", validation.reasons)
        self.assertNotIn("sk-calendar-dry-run-secret", serialized)

    def test_module_source_is_repo_local_no_live_surface(self) -> None:
        source = inspect.getsource(dry_run_module)

        for forbidden in (
            "os.environ",
            "import urllib",
            "import smtplib",
            "import sqlite3",
            "import subprocess",
            "import requests",
            "import httpx",
            "import socket",
            ".connect(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from personalos.demo.no_send_e2e import ARTIFACT_NAMES, run_no_send_e2e_demo
from personalos.dry_run_evidence import (
    BLOCKED_LIVE_RAILS,
    COMPLETION_REPORT_CONTRACT_FIELDS,
    DRY_RUN_EVIDENCE_DEFAULT_GENERATED_AT_UTC,
    DRY_RUN_EVIDENCE_SCHEMA_VERSION,
    DRY_RUN_EVIDENCE_STATUS,
    DRY_RUN_EVIDENCE_TOP_LEVEL_FIELDS,
    FAKE_LOCAL_FIXTURE_SURFACES,
    FAKE_LOCAL_FIXTURE_SURFACE_FIELDS,
    HUMAN_REQUIRED_GATES,
    NO_SEND_COMPLETION_REPORT_FIELDS,
    NO_SEND_DEMO_CONTRACT_FIELDS,
    NO_SEND_SAFETY_ASSERTION_FIELDS,
    NON_AUTHORIZATION_FALSE_FIELDS,
    NON_AUTHORIZATION_FIELDS,
    NON_AUTHORIZATION_TRUE_FIELDS,
    READINESS_PAYLOAD_FIELDS,
    SMOKE_COMMAND_TEMPLATES,
    SMOKE_COMMAND_TEMPLATE_FIELDS,
    WEEKEND_TEST_READINESS_PAYLOAD_FIELDS,
    build_dry_run_evidence_bundle_report,
    validate_dry_run_evidence_bundle_report_contract,
    validate_no_send_completion_report_contract,
)


class DryRunEvidenceBundleReportTest(unittest.TestCase):
    def test_report_builder_accepts_no_caller_input(self) -> None:
        signature = inspect.signature(build_dry_run_evidence_bundle_report)

        self.assertEqual(signature.parameters, {})

    def test_default_report_is_inert_not_live_and_contract_valid(self) -> None:
        report = build_dry_run_evidence_bundle_report()
        validation = validate_dry_run_evidence_bundle_report_contract(report)

        self.assertEqual(tuple(report), DRY_RUN_EVIDENCE_TOP_LEVEL_FIELDS)
        self.assertEqual(report["schema_version"], DRY_RUN_EVIDENCE_SCHEMA_VERSION)
        self.assertEqual(
            report["generated_at_utc"], DRY_RUN_EVIDENCE_DEFAULT_GENERATED_AT_UTC
        )
        self.assertEqual(report["status"], DRY_RUN_EVIDENCE_STATUS)
        self.assertFalse(report["dry_run_execution_started"])
        self.assertFalse(report["repo_evidence_bundle_written"])
        self.assertTrue(report["temp_only_smoke_supported"])
        self.assertFalse(report["live_mvp_ready"])
        self.assertTrue(report["human_gates_remaining"])
        self.assertEqual(tuple(report["readiness"]), READINESS_PAYLOAD_FIELDS)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": [
                    "Dry-run evidence bundle report remains inert and not live testing."
                ],
            },
        )

    def test_report_composes_weekend_readiness_without_starting_testing(self) -> None:
        weekend = build_dry_run_evidence_bundle_report()["weekend_test_readiness"]

        self.assertEqual(tuple(weekend), WEEKEND_TEST_READINESS_PAYLOAD_FIELDS)
        self.assertEqual(weekend["status"], "test_plan_recorded_not_live")
        self.assertTrue(weekend["contract_valid"])
        self.assertFalse(weekend["weekend_testing_started"])
        self.assertFalse(weekend["live_testing_authorized"])
        self.assertTrue(weekend["human_gates_remaining"])

    def test_no_send_demo_contract_matches_existing_artifact_contract(self) -> None:
        contract = build_dry_run_evidence_bundle_report()["no_send_demo_contract"]

        self.assertEqual(tuple(contract), NO_SEND_DEMO_CONTRACT_FIELDS)
        self.assertEqual(contract["artifact_names"], list(ARTIFACT_NAMES))
        self.assertEqual(contract["demo_sqlite_name"], "demo.sqlite3")
        self.assertTrue(contract["requires_explicit_safe_output_dir"])
        self.assertTrue(contract["output_dir_must_be_temp"])
        self.assertFalse(contract["repo_local_var_allowed"])
        self.assertFalse(contract["repo_local_db_allowed"])
        self.assertFalse(contract["writes_repo_files"])
        self.assertFalse(contract["external_writes_allowed"])

    def test_smoke_commands_are_non_live_and_credential_free(self) -> None:
        report = build_dry_run_evidence_bundle_report()

        self.assertEqual(report["smoke_command_templates"], list(SMOKE_COMMAND_TEMPLATES))
        command_ids = {
            command["command_id"] for command in report["smoke_command_templates"]
        }
        self.assertIn("phase13e_d_no_send_e2e", command_ids)
        self.assertIn("readiness_status_json", command_ids)
        for command in report["smoke_command_templates"]:
            with self.subTest(command=command["command_id"]):
                self.assertEqual(tuple(command), SMOKE_COMMAND_TEMPLATE_FIELDS)
                self.assertFalse(command["requires_credentials"])
                self.assertFalse(command["uses_production_db"])
                self.assertFalse(command["activates_scheduler"])
                self.assertFalse(command["calls_openclaw"])
                self.assertFalse(command["external_write"])

    def test_fake_local_fixture_surfaces_are_preview_only(self) -> None:
        report = build_dry_run_evidence_bundle_report()

        self.assertEqual(
            report["fake_local_fixture_surfaces"],
            list(FAKE_LOCAL_FIXTURE_SURFACES),
        )
        surface_ids = {
            surface["surface_id"] for surface in report["fake_local_fixture_surfaces"]
        }
        self.assertIn("todoist_fake_client", surface_ids)
        self.assertIn("calendar_fake_client", surface_ids)
        self.assertIn("fake_composer_adapter", surface_ids)
        self.assertIn("side_effect_dry_run_ledger", surface_ids)
        for surface in report["fake_local_fixture_surfaces"]:
            with self.subTest(surface=surface["surface_id"]):
                self.assertEqual(tuple(surface), FAKE_LOCAL_FIXTURE_SURFACE_FIELDS)
                self.assertTrue(surface["fake_or_preview_only"])
                self.assertFalse(surface["live_client_allowed"])
                self.assertFalse(surface["credential_required"])
                self.assertFalse(surface["external_write"])

    def test_completion_report_contract_is_non_authorizing(self) -> None:
        contract = build_dry_run_evidence_bundle_report()["completion_report_contract"]

        self.assertEqual(tuple(contract), COMPLETION_REPORT_CONTRACT_FIELDS)
        self.assertEqual(
            contract["required_top_level_fields"],
            list(NO_SEND_COMPLETION_REPORT_FIELDS),
        )
        self.assertEqual(
            contract["required_safety_assertions"],
            list(NO_SEND_SAFETY_ASSERTION_FIELDS),
        )
        self.assertEqual(contract["required_artifacts"], list(ARTIFACT_NAMES))
        self.assertTrue(contract["requires_phase14_blocked"])
        self.assertTrue(contract["requires_no_deviations"])
        self.assertFalse(contract["allows_secret_values"])
        self.assertFalse(contract["allows_live_object_ids"])
        self.assertFalse(contract["authorizes_live_access"])

    def test_human_gates_blocked_rails_and_non_authorization_are_explicit(self) -> None:
        report = build_dry_run_evidence_bundle_report()

        self.assertEqual(report["human_required_gates"], list(HUMAN_REQUIRED_GATES))
        self.assertEqual(report["blocked_live_rails"], list(BLOCKED_LIVE_RAILS))
        self.assertIn(
            "actual live-service testing remains a separate human-gated activity",
            report["human_required_gates"],
        )
        self.assertIn("credentials", report["blocked_live_rails"])
        self.assertIn("openclaw", report["blocked_live_rails"])
        self.assertEqual(tuple(report["non_authorization"]), NON_AUTHORIZATION_FIELDS)
        for field in NON_AUTHORIZATION_TRUE_FIELDS:
            with self.subTest(field=field):
                self.assertTrue(report["non_authorization"][field])
        for field in NON_AUTHORIZATION_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report["non_authorization"][field])

    def test_validator_blocks_static_report_drift_without_echo(self) -> None:
        cases = (
            (
                "status",
                lambda report, token: report.update({"status": token}),
                "Dry-run evidence report status must remain dry_run_contract_recorded_not_live.",
            ),
            (
                "generated_at_utc",
                lambda report, token: report.update({"generated_at_utc": token}),
                "Dry-run evidence report generated_at_utc does not match the contract.",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "Dry-run evidence report readiness.status must remain not_ready.",
            ),
            (
                "weekend",
                lambda report, token: report["weekend_test_readiness"].update(
                    {"status": token}
                ),
                "Dry-run evidence report weekend readiness field status drifted.",
            ),
            (
                "demo_contract",
                lambda report, token: report["no_send_demo_contract"].update(
                    {"demo_name": token}
                ),
                "Dry-run evidence report no-send demo field demo_name drifted.",
            ),
            (
                "command",
                lambda report, token: report["smoke_command_templates"][0].update(
                    {"command_template": token}
                ),
                "Dry-run evidence report smoke command template list drifted.",
            ),
            (
                "fixture",
                lambda report, token: report["fake_local_fixture_surfaces"][0].update(
                    {"label": token}
                ),
                "Dry-run evidence report fake/local fixture surface list drifted.",
            ),
            (
                "contract",
                lambda report, token: report["completion_report_contract"].update(
                    {"required_artifacts": [token]}
                ),
                "Dry-run evidence report completion contract field required_artifacts drifted.",
            ),
            (
                "human_gates",
                lambda report, token: report["human_required_gates"].append(token),
                "Dry-run evidence report human gate list drifted.",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {"candidate_approved": token}
                ),
                "Dry-run evidence report non_authorization field candidate_approved must remain false.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-dry-run-{label}"
                report = build_dry_run_evidence_bundle_report()
                mutate(report, unsafe_value)

                validation = validate_dry_run_evidence_bundle_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_boolean_lookalike_values(self) -> None:
        cases = (
            (
                "top_level_false",
                lambda report: report.update({"dry_run_execution_started": 0}),
                "Dry-run evidence report field dry_run_execution_started drifted.",
            ),
            (
                "command_false",
                lambda report: report["smoke_command_templates"][0].update(
                    {"requires_credentials": 0}
                ),
                "Dry-run evidence report smoke command field requires_credentials must remain false.",
            ),
            (
                "fixture_true",
                lambda report: report["fake_local_fixture_surfaces"][0].update(
                    {"fake_or_preview_only": 1}
                ),
                "Dry-run evidence report fake/local fixture marker must remain true.",
            ),
            (
                "non_authorization_true",
                lambda report: report["non_authorization"].update(
                    {"repo_merge_is_not_live_authorization": 1}
                ),
                "Dry-run evidence report non_authorization field repo_merge_is_not_live_authorization must remain true.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                report = build_dry_run_evidence_bundle_report()
                mutate(report)

                validation = validate_dry_run_evidence_bundle_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)

    def test_no_send_completion_validator_accepts_temp_demo_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evidence"
            completion_report = run_no_send_e2e_demo(output_dir)

            validation = validate_no_send_completion_report_contract(
                completion_report
            )

            self.assertTrue(validation.report_matches_dry_run_contract)
            self.assertEqual(
                validation.to_dict(),
                {
                    "report_matches_dry_run_contract": True,
                    "reasons": [
                        "No-send completion report matches the dry-run evidence contract."
                    ],
                },
            )

    def test_no_send_completion_validator_blocks_unsafe_drift_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completion_report = run_no_send_e2e_demo(Path(temp_dir) / "evidence")

        cases = (
            (
                "demo_name",
                lambda report, token: report.update({"demo_name": token}),
                "No-send completion report field demo_name drifted.",
            ),
            (
                "artifact_name",
                lambda report, token: report["artifact_list"][0].update(
                    {"name": token}
                ),
                "No-send completion report artifact names drifted.",
            ),
            (
                "safety",
                lambda report, token: report["safety_assertions"].update(
                    {"credentials_loaded": token}
                ),
                "No-send completion report safety assertion credentials_loaded must remain false.",
            ),
            (
                "no_send_summary",
                lambda report, token: report["no_send_export_summary"].update(
                    {"delivery_mode": token}
                ),
                "No-send completion report delivery_mode must remain no_send.",
            ),
            (
                "blocked_summary",
                lambda report, token: report["blocked_live_action_summary"].update(
                    {"gmail_sent_or_drafted": token}
                ),
                "No-send completion report blocked-live field gmail_sent_or_drafted must remain false.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-completion-{label}"
                report = json.loads(json.dumps(completion_report))
                mutate(report, unsafe_value)

                validation = validate_no_send_completion_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_dry_run_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_no_send_completion_validator_rejects_missing_report(self) -> None:
        validation = validate_no_send_completion_report_contract(None)

        self.assertFalse(validation.report_matches_dry_run_contract)
        self.assertEqual(
            validation.reasons,
            ("No no-send completion report was supplied.",),
        )

    def test_static_validator_rejects_missing_report(self) -> None:
        validation = validate_dry_run_evidence_bundle_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("No dry-run evidence bundle report was supplied.",),
        )


if __name__ == "__main__":
    unittest.main()

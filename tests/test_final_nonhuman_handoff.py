import inspect
import json
import unittest

from personalos.final_nonhuman_handoff import (
    BLOCKED_LIVE_RAILS,
    CLOSURE_PACKET_STATUS_FIELDS,
    DRY_RUN_EVIDENCE_PAYLOAD_FIELDS,
    FINAL_NONHUMAN_CLOSURE_PACKET_STATUSES,
    FINAL_NONHUMAN_HANDOFF_DEFAULT_GENERATED_AT_UTC,
    FINAL_NONHUMAN_HANDOFF_SCHEMA_VERSION,
    FINAL_NONHUMAN_HANDOFF_STATUS,
    FINAL_NONHUMAN_HANDOFF_TOP_LEVEL_FIELDS,
    HUMAN_GATE_CHECKLIST,
    HUMAN_GATE_CHECKLIST_FIELDS,
    NEXT_HUMAN_WORK_FIELDS,
    NEXT_HUMAN_WORK_PLAN,
    NON_AUTHORIZATION_FALSE_FIELDS,
    NON_AUTHORIZATION_FIELDS,
    NON_AUTHORIZATION_TRUE_FIELDS,
    READINESS_PAYLOAD_FIELDS,
    build_final_nonhuman_handoff_report,
    validate_final_nonhuman_handoff_report_contract,
)


class FinalNonhumanHandoffReportTest(unittest.TestCase):
    def test_report_builder_accepts_no_caller_input(self) -> None:
        signature = inspect.signature(build_final_nonhuman_handoff_report)

        self.assertEqual(signature.parameters, {})

    def test_default_report_is_inert_human_gated_and_contract_valid(self) -> None:
        report = build_final_nonhuman_handoff_report()
        validation = validate_final_nonhuman_handoff_report_contract(report)

        self.assertEqual(tuple(report), FINAL_NONHUMAN_HANDOFF_TOP_LEVEL_FIELDS)
        self.assertEqual(
            report["schema_version"], FINAL_NONHUMAN_HANDOFF_SCHEMA_VERSION
        )
        self.assertEqual(
            report["generated_at_utc"],
            FINAL_NONHUMAN_HANDOFF_DEFAULT_GENERATED_AT_UTC,
        )
        self.assertEqual(report["status"], FINAL_NONHUMAN_HANDOFF_STATUS)
        self.assertTrue(report["safe_nonhuman_packet_artifacts_complete"])
        self.assertTrue(report["final_packet_claude_code_audit_passed"])
        self.assertFalse(report["live_mvp_ready"])
        self.assertTrue(report["human_gates_remaining"])
        self.assertEqual(tuple(report["readiness"]), READINESS_PAYLOAD_FIELDS)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": [
                    "Final non-human handoff remains inert and blocked by human gates."
                ],
            },
        )

    def test_report_composes_dry_run_evidence_without_starting_dry_run(self) -> None:
        dry_run = build_final_nonhuman_handoff_report()["dry_run_evidence"]

        self.assertEqual(tuple(dry_run), DRY_RUN_EVIDENCE_PAYLOAD_FIELDS)
        self.assertEqual(dry_run["status"], "dry_run_contract_recorded_not_live")
        self.assertTrue(dry_run["contract_valid"])
        self.assertFalse(dry_run["dry_run_execution_started"])
        self.assertFalse(dry_run["repo_evidence_bundle_written"])
        self.assertTrue(dry_run["temp_only_smoke_supported"])
        self.assertFalse(dry_run["live_mvp_ready"])
        self.assertTrue(dry_run["human_gates_remaining"])

    def test_packet_statuses_record_five_merged_packets(self) -> None:
        report = build_final_nonhuman_handoff_report()

        self.assertEqual(
            report["closure_packet_statuses"],
            [dict(packet) for packet in FINAL_NONHUMAN_CLOSURE_PACKET_STATUSES],
        )
        self.assertEqual(len(report["closure_packet_statuses"]), 5)
        for packet in report["closure_packet_statuses"]:
            with self.subTest(packet=packet["packet_id"]):
                self.assertEqual(tuple(packet), CLOSURE_PACKET_STATUS_FIELDS)
                self.assertEqual(packet["repo_local_status"], "merged_on_main")
                self.assertTrue(packet["claude_code_audit_required"])
                self.assertIn(
                    packet["claude_code_audit_status"],
                    {"pass", "pass_with_notes_no_required_fixes"},
                )
                self.assertEqual(packet["merge_status"], "merged_on_main")
                self.assertFalse(packet["contains_human_decision"])
                self.assertFalse(packet["contains_live_access"])

    def test_human_gate_checklist_is_exact_and_pending(self) -> None:
        report = build_final_nonhuman_handoff_report()

        self.assertEqual(
            report["human_gate_checklist"],
            [dict(gate) for gate in HUMAN_GATE_CHECKLIST],
        )
        self.assertEqual(len(report["human_gate_checklist"]), 9)
        expected_gate_ids = {
            "candidate_approval",
            "phase14c_authorization",
            "live_service_access",
            "credential_auth_handling",
            "production_db_activation",
            "scheduler_background_activation",
            "openclaw_handoff_or_invocation",
            "actual_live_service_testing",
            "go_no_go_launch_approval",
        }
        self.assertEqual(
            {gate["gate_id"] for gate in report["human_gate_checklist"]},
            expected_gate_ids,
        )
        for gate in report["human_gate_checklist"]:
            with self.subTest(gate=gate["gate_id"]):
                self.assertEqual(tuple(gate), HUMAN_GATE_CHECKLIST_FIELDS)
                self.assertEqual(gate["status"], "pending_human_decision")

    def test_blocked_rails_and_next_human_work_remain_non_live(self) -> None:
        report = build_final_nonhuman_handoff_report()

        self.assertEqual(report["blocked_live_rails"], list(BLOCKED_LIVE_RAILS))
        self.assertIn("credentials", report["blocked_live_rails"])
        self.assertIn("openclaw", report["blocked_live_rails"])
        self.assertIn("protected_paths", report["blocked_live_rails"])
        self.assertEqual(
            report["next_human_work_plan"],
            [dict(step) for step in NEXT_HUMAN_WORK_PLAN],
        )
        for step in report["next_human_work_plan"]:
            with self.subTest(step=step["step_id"]):
                self.assertEqual(tuple(step), NEXT_HUMAN_WORK_FIELDS)
                self.assertTrue(step["blocked_until_human_decision"])
                self.assertFalse(step["live_action_allowed_by_this_report"])
                self.assertFalse(step["credential_access_allowed_by_this_report"])

    def test_non_authorization_flags_remain_false(self) -> None:
        non_authorization = build_final_nonhuman_handoff_report()[
            "non_authorization"
        ]

        self.assertEqual(tuple(non_authorization), NON_AUTHORIZATION_FIELDS)
        for field in NON_AUTHORIZATION_TRUE_FIELDS:
            with self.subTest(field=field):
                self.assertTrue(non_authorization[field])
        for field in NON_AUTHORIZATION_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(non_authorization[field])

    def test_validator_blocks_top_level_and_readiness_drift_without_echo(self) -> None:
        cases = (
            (
                "status",
                lambda report, token: report.update({"status": token}),
                "Final non-human handoff report status must remain human-gated.",
            ),
            (
                "generated_at_utc",
                lambda report, token: report.update({"generated_at_utc": token}),
                "Final non-human handoff report generated_at_utc does not match the contract.",
            ),
            (
                "live_mvp_ready",
                lambda report, token: report.update({"live_mvp_ready": token}),
                "Final non-human handoff report field live_mvp_ready drifted.",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "Final non-human handoff report readiness.status must remain not_ready.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-final-top-{label}"
                report = build_final_nonhuman_handoff_report()
                mutate(report, unsafe_value)

                validation = validate_final_nonhuman_handoff_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_nested_payload_drift_without_echo(self) -> None:
        cases = (
            (
                "dry_run",
                lambda report, token: report["dry_run_evidence"].update(
                    {"status": token}
                ),
                "Final non-human handoff report dry-run field status drifted.",
            ),
            (
                "packet",
                lambda report, token: report["closure_packet_statuses"][0].update(
                    {"packet_id": token}
                ),
                "Final non-human handoff report packet status list drifted.",
            ),
            (
                "human_gate",
                lambda report, token: report["human_gate_checklist"][0].update(
                    {"gate_id": token}
                ),
                "Final non-human handoff report human gate checklist drifted.",
            ),
            (
                "blocked_rails",
                lambda report, token: report["blocked_live_rails"].append(token),
                "Final non-human handoff report blocked live rail list drifted.",
            ),
            (
                "next_human_work",
                lambda report, token: report["next_human_work_plan"][0].update(
                    {"step_id": token}
                ),
                "Final non-human handoff report next human work plan drifted.",
            ),
            (
                "safety_posture",
                lambda report, token: report["safety_posture"].update(
                    {"live_rails_activated": token}
                ),
                "Final non-human handoff report safety_posture does not match the contract.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-final-nested-{label}"
                report = build_final_nonhuman_handoff_report()
                mutate(report, unsafe_value)

                validation = validate_final_nonhuman_handoff_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_non_authorization_drift_without_echo(self) -> None:
        cases = (
            (
                "true_field",
                "repo_merge_is_not_live_authorization",
                1,
                "Final non-human handoff report non_authorization field repo_merge_is_not_live_authorization must remain true.",
            ),
            (
                "false_field",
                "candidate_approved",
                "matrix-secret-final-candidate-approved",
                "Final non-human handoff report non_authorization field candidate_approved must remain false.",
            ),
        )
        for label, field, value, expected_reason in cases:
            with self.subTest(label=label):
                report = build_final_nonhuman_handoff_report()
                report["non_authorization"][field] = value

                validation = validate_final_nonhuman_handoff_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(str(value), serialized_validation)

    def test_validator_blocks_boolean_lookalike_values(self) -> None:
        cases = (
            (
                "top_level_true",
                lambda report: report.update(
                    {"safe_nonhuman_packet_artifacts_complete": 1}
                ),
                "Final non-human handoff report field safe_nonhuman_packet_artifacts_complete drifted.",
            ),
            (
                "dry_run_false",
                lambda report: report["dry_run_evidence"].update(
                    {"dry_run_execution_started": 0}
                ),
                "Final non-human handoff report dry-run field dry_run_execution_started drifted.",
            ),
            (
                "packet_false",
                lambda report: report["closure_packet_statuses"][0].update(
                    {"contains_live_access": 0}
                ),
                "Final non-human handoff report packet live-access flag must remain false.",
            ),
            (
                "human_work_true",
                lambda report: report["next_human_work_plan"][0].update(
                    {"blocked_until_human_decision": 1}
                ),
                "Final non-human handoff report human-work block flag must remain true.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                report = build_final_nonhuman_handoff_report()
                mutate(report)

                validation = validate_final_nonhuman_handoff_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)

    def test_static_validator_rejects_missing_report(self) -> None:
        validation = validate_final_nonhuman_handoff_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("No final non-human handoff report was supplied.",),
        )


if __name__ == "__main__":
    unittest.main()

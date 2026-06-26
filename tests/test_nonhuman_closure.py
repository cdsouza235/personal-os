import inspect
import json
import unittest

from personalos.nonhuman_closure import (
    BLOCKED_LIVE_RAILS,
    HUMAN_REQUIRED_GATES,
    NONHUMAN_CLOSURE_DEFAULT_GENERATED_AT_UTC,
    NONHUMAN_CLOSURE_PACKET_PLAN,
    NONHUMAN_CLOSURE_SCHEMA_VERSION,
    NONHUMAN_CLOSURE_STATUS,
    NONHUMAN_CLOSURE_TOP_LEVEL_FIELDS,
    NON_AUTHORIZATION_FALSE_FIELDS,
    NON_AUTHORIZATION_FIELDS,
    PACKET_PLAN_FIELDS,
    build_nonhuman_closure_plan_report,
    validate_nonhuman_closure_plan_report_contract,
)


class NonhumanClosurePlanReportTest(unittest.TestCase):
    def test_report_builder_accepts_no_caller_input(self) -> None:
        signature = inspect.signature(build_nonhuman_closure_plan_report)

        self.assertEqual(signature.parameters, {})

    def test_default_report_is_inert_and_blocked_by_human_gates(self) -> None:
        report = build_nonhuman_closure_plan_report()
        validation = validate_nonhuman_closure_plan_report_contract(report)

        self.assertEqual(tuple(report), NONHUMAN_CLOSURE_TOP_LEVEL_FIELDS)
        self.assertEqual(report["schema_version"], NONHUMAN_CLOSURE_SCHEMA_VERSION)
        self.assertEqual(
            report["generated_at_utc"], NONHUMAN_CLOSURE_DEFAULT_GENERATED_AT_UTC
        )
        self.assertEqual(report["status"], NONHUMAN_CLOSURE_STATUS)
        self.assertFalse(report["nonhuman_closure_complete"])
        self.assertFalse(report["live_mvp_ready"])
        self.assertTrue(report["human_gates_remaining"])
        self.assertTrue(report["accelerated_packet_model_recorded"])
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": [
                    "Non-human closure plan remains inert and blocked by human gates."
                ],
            },
        )

    def test_report_composes_mvp_readiness_without_authorizing_live_work(self) -> None:
        mvp_readiness = build_nonhuman_closure_plan_report()["mvp_readiness"]

        self.assertEqual(mvp_readiness["status"], "not_ready")
        self.assertTrue(mvp_readiness["contract_valid"])
        self.assertFalse(mvp_readiness["live_mvp_ready"])
        self.assertTrue(mvp_readiness["candidate_review_tracking_only"])
        self.assertTrue(mvp_readiness["phase14_c_blocked"])

    def test_packet_plan_records_five_safe_merged_audited_packets(self) -> None:
        report = build_nonhuman_closure_plan_report()

        self.assertEqual(report["packet_plan"], [dict(packet) for packet in NONHUMAN_CLOSURE_PACKET_PLAN])
        self.assertEqual(len(report["packet_plan"]), 5)
        for packet in report["packet_plan"]:
            with self.subTest(packet=packet["packet_id"]):
                self.assertEqual(tuple(packet), PACKET_PLAN_FIELDS)
                self.assertEqual(packet["status"], "merged_on_main")
                self.assertIn("repo-local", packet["allowed_surface"])
                self.assertTrue(packet["claude_code_audit_required"])
                self.assertFalse(packet["contains_human_decision"])
                self.assertFalse(packet["contains_live_access"])

    def test_report_keeps_human_gates_and_blocked_live_rails_explicit(self) -> None:
        report = build_nonhuman_closure_plan_report()

        self.assertEqual(report["human_required_gates"], list(HUMAN_REQUIRED_GATES))
        self.assertEqual(report["blocked_live_rails"], list(BLOCKED_LIVE_RAILS))
        self.assertIn(
            "actual live-service testing remains a separate human-gated activity",
            report["human_required_gates"],
        )
        self.assertIn(
            "go/no-go launch approval remains a separate human decision",
            report["human_required_gates"],
        )
        self.assertIn("credentials", report["blocked_live_rails"])
        self.assertIn("openclaw", report["blocked_live_rails"])
        self.assertIn("protected_paths", report["blocked_live_rails"])

    def test_non_authorization_flags_remain_false(self) -> None:
        non_authorization = build_nonhuman_closure_plan_report()["non_authorization"]

        self.assertEqual(tuple(non_authorization), NON_AUTHORIZATION_FIELDS)
        self.assertTrue(non_authorization["repo_merge_is_not_live_authorization"])
        self.assertTrue(non_authorization["nonhuman_closure_is_not_product_approval"])
        for field in NON_AUTHORIZATION_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(non_authorization[field])

    def test_validator_blocks_top_level_and_readiness_drift_without_echo(self) -> None:
        cases = (
            (
                "status",
                lambda report, token: report.update({"status": token}),
                "Non-human closure report status must remain blocked_by_human_gates.",
            ),
            (
                "generated_at_utc",
                lambda report, token: report.update({"generated_at_utc": token}),
                "Non-human closure report generated_at_utc does not match the contract.",
            ),
            (
                "live_mvp_ready",
                lambda report, token: report.update({"live_mvp_ready": token}),
                "Non-human closure report field live_mvp_ready drifted.",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "Non-human closure report readiness.status must remain not_ready.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-nonhuman-top-{label}"
                report = build_nonhuman_closure_plan_report()
                mutate(report, unsafe_value)

                validation = validate_nonhuman_closure_plan_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_nested_payload_drift_without_echo(self) -> None:
        cases = (
            (
                "mvp_readiness",
                lambda report, token: report["mvp_readiness"].update({"status": token}),
                "Non-human closure report MVP readiness field status drifted.",
            ),
            (
                "packet_plan",
                lambda report, token: report["packet_plan"][0].update({"packet_id": token}),
                "Non-human closure report packet plan drifted.",
            ),
            (
                "human_required_gates",
                lambda report, token: report["human_required_gates"].append(token),
                "Non-human closure report human gate list drifted.",
            ),
            (
                "blocked_live_rails",
                lambda report, token: report["blocked_live_rails"].append(token),
                "Non-human closure report blocked live rail list drifted.",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {"candidate_approved": token}
                ),
                "Non-human closure report non_authorization field candidate_approved must remain false.",
            ),
            (
                "safety_posture",
                lambda report, token: report["safety_posture"].update(
                    {"live_rails_activated": token}
                ),
                "Non-human closure report safety_posture does not match the contract.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-nonhuman-nested-{label}"
                report = build_nonhuman_closure_plan_report()
                mutate(report, unsafe_value)

                validation = validate_nonhuman_closure_plan_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_mvp_boolean_lookalike_values(self) -> None:
        report = build_nonhuman_closure_plan_report()
        report["mvp_readiness"]["contract_valid"] = 1

        validation = validate_nonhuman_closure_plan_report_contract(report)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Non-human closure report MVP readiness field contract_valid drifted.",
            validation.reasons,
        )

    def test_validator_blocks_packet_flags_that_cross_boundaries(self) -> None:
        cases = (
            (
                "audit",
                "claude_code_audit_required",
                False,
                "Non-human closure report packet audit flag must remain true.",
            ),
            (
                "human_decision",
                "contains_human_decision",
                True,
                "Non-human closure report packet human-decision flag must remain false.",
            ),
            (
                "live_access",
                "contains_live_access",
                True,
                "Non-human closure report packet live-access flag must remain false.",
            ),
        )
        for label, field, value, expected_reason in cases:
            with self.subTest(label=label):
                report = build_nonhuman_closure_plan_report()
                report["packet_plan"][1][field] = value

                validation = validate_nonhuman_closure_plan_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)

    def test_validator_rejects_missing_report(self) -> None:
        validation = validate_nonhuman_closure_plan_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("No non-human closure plan report was supplied.",),
        )


if __name__ == "__main__":
    unittest.main()

import inspect
import json
import unittest

from personalos.mvp_readiness import (
    BLOCKED_LIVE_RAILS,
    COMPLETED_INERT_CAPABILITIES,
    MVP_READINESS_DEFAULT_GENERATED_AT_UTC,
    MVP_READINESS_SCHEMA_VERSION,
    MVP_READINESS_STATUS,
    MVP_READINESS_TOP_LEVEL_FIELDS,
    NON_AUTHORIZATION_FIELDS,
    NON_AUTHORIZATION_FALSE_FIELDS,
    PENDING_HUMAN_DECISIONS,
    PHASE14C_DECISION_SUPPORT_PAYLOAD_FIELDS,
    READINESS_PAYLOAD_FIELDS,
    build_mvp_readiness_gap_report,
    validate_mvp_readiness_gap_report_contract,
)


class MvpReadinessGapReportTest(unittest.TestCase):
    def test_report_builder_accepts_no_caller_input(self) -> None:
        signature = inspect.signature(build_mvp_readiness_gap_report)

        self.assertEqual(signature.parameters, {})

    def test_default_report_is_inert_not_ready_and_contract_valid(self) -> None:
        report = build_mvp_readiness_gap_report()
        validation = validate_mvp_readiness_gap_report_contract(report)

        self.assertEqual(tuple(report), MVP_READINESS_TOP_LEVEL_FIELDS)
        self.assertEqual(report["schema_version"], MVP_READINESS_SCHEMA_VERSION)
        self.assertEqual(
            report["generated_at_utc"], MVP_READINESS_DEFAULT_GENERATED_AT_UTC
        )
        self.assertEqual(report["status"], MVP_READINESS_STATUS)
        self.assertFalse(report["live_mvp_ready"])
        self.assertTrue(report["inert_report_only"])
        self.assertTrue(report["candidate_review_tracking_only"])
        self.assertTrue(report["phase14_c_blocked"])
        self.assertEqual(tuple(report["readiness"]), READINESS_PAYLOAD_FIELDS)
        self.assertEqual(
            tuple(report["phase14c_decision_support"]),
            PHASE14C_DECISION_SUPPORT_PAYLOAD_FIELDS,
        )
        self.assertEqual(tuple(report["non_authorization"]), NON_AUTHORIZATION_FIELDS)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": ["MVP readiness gap report remains inert and not_ready."],
            },
        )

    def test_report_preserves_phase14c_non_authorization_boundary(self) -> None:
        phase14c = build_mvp_readiness_gap_report()["phase14c_decision_support"]

        self.assertEqual(phase14c["report_status"], "decision_needed")
        self.assertTrue(phase14c["report_contract_valid"])
        self.assertTrue(phase14c["decision_record_validated_as_unfilled"])
        self.assertTrue(phase14c["candidate_review_tracking_only"])
        self.assertTrue(phase14c["phase14_c_blocked"])
        for field in (
            "human_decision_recorded",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated",
            "candidate_run",
        ):
            with self.subTest(field=field):
                self.assertFalse(phase14c[field])

    def test_report_lists_completed_inert_work_and_pending_human_gates(self) -> None:
        report = build_mvp_readiness_gap_report()

        self.assertEqual(
            report["completed_inert_capabilities"],
            list(COMPLETED_INERT_CAPABILITIES),
        )
        self.assertEqual(
            report["pending_human_decisions"],
            list(PENDING_HUMAN_DECISIONS),
        )
        self.assertEqual(report["blocked_live_rails"], list(BLOCKED_LIVE_RAILS))
        self.assertIn(
            "Phase 14-C decision gate and decision-support report contract",
            report["completed_inert_capabilities"],
        )
        self.assertIn(
            "candidate approval remains a separate human decision",
            report["pending_human_decisions"],
        )
        self.assertIn("todoist", report["blocked_live_rails"])
        self.assertIn("openclaw", report["blocked_live_rails"])

    def test_non_authorization_flags_remain_false(self) -> None:
        report = build_mvp_readiness_gap_report()
        non_authorization = report["non_authorization"]

        self.assertTrue(
            non_authorization["approval_to_merge_docs_is_not_live_authorization"]
        )
        for field in NON_AUTHORIZATION_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(non_authorization[field])

    def test_validator_blocks_top_level_and_readiness_drift_without_echo(self) -> None:
        cases = (
            (
                "status",
                lambda report, token: report.update({"status": token}),
                "MVP readiness report status must remain not_ready.",
            ),
            (
                "live_mvp_ready",
                lambda report, token: report.update({"live_mvp_ready": token}),
                "MVP readiness report field live_mvp_ready drifted.",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "MVP readiness report readiness.status must remain not_ready.",
            ),
            (
                "generated_at_utc",
                lambda report, token: report.update({"generated_at_utc": token}),
                "MVP readiness report generated_at_utc does not match the contract.",
            ),
            (
                "safety_posture",
                lambda report, token: report["safety_posture"].update(
                    {"readiness.status": token}
                ),
                "MVP readiness report safety_posture does not match the contract.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-mvp-readiness-{label}"
                report = build_mvp_readiness_gap_report()
                mutate(report, unsafe_value)

                validation = validate_mvp_readiness_gap_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_nested_payload_shape_drift_without_echo(self) -> None:
        cases = (
            (
                "readiness",
                lambda report, token: report["readiness"].update({token: token}),
                "MVP readiness report readiness fields do not match the contract.",
            ),
            (
                "phase14c",
                lambda report, token: report["phase14c_decision_support"].update(
                    {token: token}
                ),
                "MVP readiness report Phase 14-C fields do not match the contract.",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {token: token}
                ),
                "MVP readiness report non_authorization fields do not match the contract.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-mvp-nested-{label}"
                report = build_mvp_readiness_gap_report()
                mutate(report, unsafe_value)

                validation = validate_mvp_readiness_gap_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_phase14c_drift_without_echo(self) -> None:
        cases = (
            (
                "report_status",
                "MVP readiness report Phase 14-C status must remain decision_needed.",
            ),
            (
                "candidate_approved",
                "MVP readiness report Phase 14-C field candidate_approved drifted.",
            ),
            (
                "candidate_run",
                "MVP readiness report Phase 14-C field candidate_run drifted.",
            ),
        )
        for field, expected_reason in cases:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-phase14c-{field}"
                report = build_mvp_readiness_gap_report()
                report["phase14c_decision_support"][field] = unsafe_value

                validation = validate_mvp_readiness_gap_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_list_and_non_authorization_drift_without_echo(self) -> None:
        cases = (
            (
                "completed_inert_capabilities",
                lambda report, token: report["completed_inert_capabilities"].append(token),
                "MVP readiness report completed capability list drifted.",
            ),
            (
                "pending_human_decisions",
                lambda report, token: report["pending_human_decisions"].append(token),
                "MVP readiness report pending human decision list drifted.",
            ),
            (
                "blocked_live_rails",
                lambda report, token: report["blocked_live_rails"].append(token),
                "MVP readiness report blocked live rail list drifted.",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {"candidate_approved": token}
                ),
                "MVP readiness report non_authorization field candidate_approved must remain false.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-mvp-list-{label}"
                report = build_mvp_readiness_gap_report()
                mutate(report, unsafe_value)

                validation = validate_mvp_readiness_gap_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_rejects_missing_report(self) -> None:
        validation = validate_mvp_readiness_gap_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("No MVP readiness gap report was supplied.",),
        )


if __name__ == "__main__":
    unittest.main()

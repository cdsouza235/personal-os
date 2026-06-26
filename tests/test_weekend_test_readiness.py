import inspect
import json
import unittest

from personalos.weekend_test_readiness import (
    BLOCKED_LIVE_RAILS,
    EVIDENCE_TEMPLATE_FIELDS,
    EVIDENCE_TEMPLATES,
    HUMAN_REQUIRED_GATES,
    MANUAL_TEST_CATEGORIES,
    MANUAL_TEST_CATEGORY_FIELDS,
    NO_GO_CRITERIA,
    NONHUMAN_CLOSURE_PAYLOAD_FIELDS,
    NON_AUTHORIZATION_FALSE_FIELDS,
    NON_AUTHORIZATION_FIELDS,
    NON_AUTHORIZATION_TRUE_FIELDS,
    READINESS_PAYLOAD_FIELDS,
    ROLLBACK_REHEARSAL_TEMPLATE_FIELDS,
    ROLLBACK_REHEARSAL_TEMPLATES,
    SOURCE_DOCUMENTS,
    WEEKEND_TEST_READINESS_DEFAULT_GENERATED_AT_UTC,
    WEEKEND_TEST_READINESS_SCHEMA_VERSION,
    WEEKEND_TEST_READINESS_STATUS,
    WEEKEND_TEST_READINESS_TOP_LEVEL_FIELDS,
    build_weekend_test_readiness_report,
    validate_weekend_test_readiness_report_contract,
)


class WeekendTestReadinessReportTest(unittest.TestCase):
    def test_report_builder_accepts_no_caller_input(self) -> None:
        signature = inspect.signature(build_weekend_test_readiness_report)

        self.assertEqual(signature.parameters, {})

    def test_default_report_is_inert_not_live_and_contract_valid(self) -> None:
        report = build_weekend_test_readiness_report()
        validation = validate_weekend_test_readiness_report_contract(report)

        self.assertEqual(tuple(report), WEEKEND_TEST_READINESS_TOP_LEVEL_FIELDS)
        self.assertEqual(
            report["schema_version"], WEEKEND_TEST_READINESS_SCHEMA_VERSION
        )
        self.assertEqual(
            report["generated_at_utc"],
            WEEKEND_TEST_READINESS_DEFAULT_GENERATED_AT_UTC,
        )
        self.assertEqual(report["status"], WEEKEND_TEST_READINESS_STATUS)
        self.assertFalse(report["weekend_testing_started"])
        self.assertFalse(report["live_testing_authorized"])
        self.assertFalse(report["live_mvp_ready"])
        self.assertTrue(report["human_gates_remaining"])
        self.assertTrue(report["inert_report_only"])
        self.assertEqual(tuple(report["readiness"]), READINESS_PAYLOAD_FIELDS)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": [
                    "Weekend test readiness report remains inert and not live testing."
                ],
            },
        )

    def test_report_composes_nonhuman_closure_current_packet(self) -> None:
        closure = build_weekend_test_readiness_report()["nonhuman_closure"]

        self.assertEqual(tuple(closure), NONHUMAN_CLOSURE_PAYLOAD_FIELDS)
        self.assertEqual(closure["status"], "blocked_by_human_gates")
        self.assertTrue(closure["contract_valid"])
        self.assertFalse(closure["nonhuman_closure_complete"])
        self.assertTrue(closure["human_gates_remaining"])
        self.assertFalse(closure["live_mvp_ready"])
        self.assertTrue(closure["accelerated_packet_model_recorded"])
        self.assertEqual(
            closure["current_packet_id"], "packet_3_weekend_test_readiness_runbook"
        )

    def test_manual_test_categories_are_safe_and_source_backed(self) -> None:
        report = build_weekend_test_readiness_report()

        self.assertEqual(report["source_documents"], list(SOURCE_DOCUMENTS))
        self.assertEqual(
            report["manual_test_categories"],
            [_materialize(record) for record in MANUAL_TEST_CATEGORIES],
        )
        category_ids = {
            category["category_id"] for category in report["manual_test_categories"]
        }
        self.assertIn("repo_validation_capture", category_ids)
        self.assertIn("activation_checklist_review", category_ids)
        self.assertIn("rollback_tabletop_review", category_ids)
        for category in report["manual_test_categories"]:
            with self.subTest(category=category["category_id"]):
                self.assertEqual(tuple(category), MANUAL_TEST_CATEGORY_FIELDS)
                self.assertIn(category["source_document"], SOURCE_DOCUMENTS)
                self.assertTrue(category["evidence_required"])
                self.assertFalse(category["contains_human_decision"])
                self.assertFalse(category["contains_live_access"])
                self.assertFalse(category["credentials_required"])
                self.assertFalse(category["production_db_required"])
                self.assertFalse(category["scheduler_required"])
                self.assertFalse(category["openclaw_required"])

    def test_evidence_templates_do_not_capture_secrets_or_authorize_live_access(self) -> None:
        report = build_weekend_test_readiness_report()

        self.assertEqual(
            report["evidence_templates"],
            [_materialize(record) for record in EVIDENCE_TEMPLATES],
        )
        for template in report["evidence_templates"]:
            with self.subTest(template=template["template_id"]):
                self.assertEqual(tuple(template), EVIDENCE_TEMPLATE_FIELDS)
                self.assertTrue(template["required_fields"])
                self.assertFalse(template["captures_secret_values"])
                self.assertFalse(template["records_live_object_ids"])
                self.assertFalse(template["authorizes_live_access"])

    def test_no_go_and_rollback_templates_are_rehearsal_only(self) -> None:
        report = build_weekend_test_readiness_report()

        self.assertEqual(report["no_go_criteria"], list(NO_GO_CRITERIA))
        self.assertIn(
            "go/no-go launch approval is missing",
            report["no_go_criteria"],
        )
        self.assertEqual(
            report["rollback_rehearsal_templates"],
            [_materialize(record) for record in ROLLBACK_REHEARSAL_TEMPLATES],
        )
        for template in report["rollback_rehearsal_templates"]:
            with self.subTest(template=template["template_id"]):
                self.assertEqual(tuple(template), ROLLBACK_REHEARSAL_TEMPLATE_FIELDS)
                self.assertTrue(template["rehearsal_only"])
                self.assertFalse(template["live_action_authorized"])
                self.assertTrue(template["required_fields"])

    def test_report_keeps_human_gates_and_blocked_live_rails_explicit(self) -> None:
        report = build_weekend_test_readiness_report()

        self.assertEqual(report["human_required_gates"], list(HUMAN_REQUIRED_GATES))
        self.assertEqual(report["blocked_live_rails"], list(BLOCKED_LIVE_RAILS))
        self.assertIn(
            "actual live-service testing remains a separate human-gated activity",
            report["human_required_gates"],
        )
        self.assertIn("todoist", report["blocked_live_rails"])
        self.assertIn("credentials", report["blocked_live_rails"])
        self.assertIn("openclaw", report["blocked_live_rails"])

    def test_non_authorization_flags_remain_false(self) -> None:
        non_authorization = build_weekend_test_readiness_report()["non_authorization"]

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
                "Weekend test readiness report status must remain test_plan_recorded_not_live.",
            ),
            (
                "generated_at_utc",
                lambda report, token: report.update({"generated_at_utc": token}),
                "Weekend test readiness report generated_at_utc does not match the contract.",
            ),
            (
                "live_testing_authorized",
                lambda report, token: report.update({"live_testing_authorized": token}),
                "Weekend test readiness report field live_testing_authorized drifted.",
            ),
            (
                "readiness",
                lambda report, token: report["readiness"].update({"status": token}),
                "Weekend test readiness report readiness.status must remain not_ready.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-weekend-top-{label}"
                report = build_weekend_test_readiness_report()
                mutate(report, unsafe_value)

                validation = validate_weekend_test_readiness_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_nested_payload_drift_without_echo(self) -> None:
        cases = (
            (
                "source_documents",
                lambda report, token: report["source_documents"].append(token),
                "Weekend test readiness report source document list drifted.",
            ),
            (
                "nonhuman_closure",
                lambda report, token: report["nonhuman_closure"].update(
                    {"status": token}
                ),
                "Weekend test readiness report non-human closure field status drifted.",
            ),
            (
                "manual_test_categories",
                lambda report, token: report["manual_test_categories"][0].update(
                    {"label": token}
                ),
                "Weekend test readiness report manual test category list drifted.",
            ),
            (
                "evidence_templates",
                lambda report, token: report["evidence_templates"][0].update(
                    {"label": token}
                ),
                "Weekend test readiness report evidence template list drifted.",
            ),
            (
                "no_go_criteria",
                lambda report, token: report["no_go_criteria"].append(token),
                "Weekend test readiness report no-go criteria drifted.",
            ),
            (
                "rollback_rehearsal_templates",
                lambda report, token: report["rollback_rehearsal_templates"][0].update(
                    {"rail": token}
                ),
                "Weekend test readiness report rollback template list drifted.",
            ),
            (
                "human_required_gates",
                lambda report, token: report["human_required_gates"].append(token),
                "Weekend test readiness report human gate list drifted.",
            ),
            (
                "blocked_live_rails",
                lambda report, token: report["blocked_live_rails"].append(token),
                "Weekend test readiness report blocked live rail list drifted.",
            ),
            (
                "non_authorization",
                lambda report, token: report["non_authorization"].update(
                    {"candidate_approved": token}
                ),
                "Weekend test readiness report non_authorization field candidate_approved must remain false.",
            ),
            (
                "safety_posture",
                lambda report, token: report["safety_posture"].update(
                    {"live_rails_activated": token}
                ),
                "Weekend test readiness report safety_posture does not match the contract.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-weekend-nested-{label}"
                report = build_weekend_test_readiness_report()
                mutate(report, unsafe_value)

                validation = validate_weekend_test_readiness_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_validator_blocks_boolean_lookalike_values(self) -> None:
        cases = (
            (
                "manual_live_access",
                lambda report: report["manual_test_categories"][0].update(
                    {"contains_live_access": 0}
                ),
                "Weekend test readiness report manual test field contains_live_access must remain false.",
            ),
            (
                "evidence_authorizes_live_access",
                lambda report: report["evidence_templates"][0].update(
                    {"authorizes_live_access": 0}
                ),
                "Weekend test readiness report evidence template field authorizes_live_access must remain false.",
            ),
            (
                "rollback_rehearsal_only",
                lambda report: report["rollback_rehearsal_templates"][0].update(
                    {"rehearsal_only": 1}
                ),
                "Weekend test readiness report rollback rehearsal flag must remain true.",
            ),
            (
                "non_authorization_true_field",
                lambda report: report["non_authorization"].update(
                    {"repo_merge_is_not_live_authorization": 1}
                ),
                "Weekend test readiness report non_authorization field repo_merge_is_not_live_authorization must remain true.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                report = build_weekend_test_readiness_report()
                mutate(report)

                validation = validate_weekend_test_readiness_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)

    def test_validator_rejects_missing_report(self) -> None:
        validation = validate_weekend_test_readiness_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("No weekend test readiness report was supplied.",),
        )


def _materialize(record: dict[str, object]) -> dict[str, object]:
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in record.items()
    }


if __name__ == "__main__":
    unittest.main()

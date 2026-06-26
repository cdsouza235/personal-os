import json
import unittest

from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus
from personalos.phase14c_candidate_decision_support import (
    ALLOWED_VALIDATION_STATUS_VALUES,
    FILLABLE_DECISION_FIELDS,
    KNOWN_DECISION_RECORD_FIELDS,
    PHASE14C_DECISION_SUPPORT_CONTRACT_SCHEMA_VERSION,
    PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
    PROHIBITED_LIVE_FIELDS,
    PROHIBITED_SECRET_FIELDS,
    REPORT_INERT_FALSE_FIELDS,
    REPORT_INERT_TRUE_FIELD_PATHS,
    REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT,
    REPORT_TOP_LEVEL_FIELDS,
    REQUIRED_FALSE_FIELDS,
    REQUIRED_TEXT_DEFAULTS,
    VALIDATION_PAYLOAD_FIELDS,
    blank_phase14c_candidate_decision_support_record,
    build_phase14c_candidate_decision_support_contract_manifest,
    build_phase14c_candidate_decision_support_report,
    validate_phase14c_candidate_decision_record,
    validate_phase14c_candidate_decision_support_report_contract,
)


class Phase14CCandidateDecisionSupportRecordTest(unittest.TestCase):
    def test_blank_template_is_unfilled_and_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        validation = validate_phase14c_candidate_decision_record(record)
        report = build_phase14c_candidate_decision_support_report(record)

        self.assertEqual(record["schema_version"], PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION)
        self.assertEqual(record["readiness.status"], "not_ready")
        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertTrue(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertTrue(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertFalse(report["decision_option_selected"])
        self.assertEqual(report["decision_option"], "unselected")

    def test_default_report_uses_unfilled_false_default_record(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertTrue(report["decision_record_validated_as_unfilled"])
        self.assertTrue(validation["record_accepted_as_unfilled_template"])
        self.assertEqual(report["decision_record_template"]["decision_status"], "unfilled")
        self.assertEqual(report["decision_record_template"]["decision_option"], "unselected")
        self.assertFalse(report["decision_record_template"]["candidate_approved"])

    def test_report_top_level_shape_remains_explicit_and_inert(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        self.assertEqual(tuple(report), REPORT_TOP_LEVEL_FIELDS)
        for field in REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT:
            with self.subTest(field=field):
                self.assertNotIn(field, report)

    def test_contract_manifest_is_inert_and_non_authorizing(self) -> None:
        manifest = build_phase14c_candidate_decision_support_contract_manifest()
        serialized_manifest = json.dumps(manifest, sort_keys=True)

        self.assertEqual(
            manifest["schema_version"],
            PHASE14C_DECISION_SUPPORT_CONTRACT_SCHEMA_VERSION,
        )
        self.assertEqual(
            manifest["decision_support_schema_version"],
            PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            manifest["allowed_validation_statuses"],
            list(ALLOWED_VALIDATION_STATUS_VALUES),
        )
        non_authorization = manifest["non_authorization_contract"]
        self.assertTrue(non_authorization["candidate_review_tracking_only"])
        self.assertTrue(non_authorization["phase14_c_blocked"])
        self.assertTrue(non_authorization["inert_report_only"])
        self.assertEqual(non_authorization["readiness.status"], "not_ready")
        for field in (
            "live_rails_activated",
            "human_decision_recorded",
            "decision_option_selected",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated_or_run",
            "live_service_access_authorized",
            "credentials_auth_handling_authorized",
            "production_db_activation_authorized",
            "scheduler_background_activation_authorized",
            "openclaw_invocation_authorized",
            "protected_path_access_authorized",
            "runtime_operator_scaffolding_authorized",
        ):
            with self.subTest(field=field):
                self.assertFalse(non_authorization[field])

        self.assertNotIn("approve for execution", serialized_manifest.lower())
        self.assertNotIn("ready", manifest["allowed_validation_statuses"])

    def test_contract_manifest_matches_template_schema_groups(self) -> None:
        manifest = build_phase14c_candidate_decision_support_contract_manifest()
        schema = manifest["decision_record_schema"]
        blocked_groups = manifest["blocked_field_groups"]
        record = blank_phase14c_candidate_decision_support_record()

        self.assertEqual(set(schema["known_fields"]), set(record))
        self.assertEqual(schema["required_text_defaults"], REQUIRED_TEXT_DEFAULTS)
        self.assertEqual(schema["required_false_fields"], list(REQUIRED_FALSE_FIELDS))
        self.assertEqual(schema["fillable_decision_fields"], list(FILLABLE_DECISION_FIELDS))
        self.assertEqual(schema["readiness_status_field"], "readiness.status")
        self.assertEqual(schema["readiness_status_required_value"], "not_ready")
        self.assertEqual(
            schema["raw_input_echo_fields_absent"],
            list(REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT),
        )
        self.assertEqual(blocked_groups["required_false_fields"], list(REQUIRED_FALSE_FIELDS))
        self.assertEqual(blocked_groups["fillable_decision_fields"], list(FILLABLE_DECISION_FIELDS))
        self.assertEqual(blocked_groups["prohibited_live_fields"], list(PROHIBITED_LIVE_FIELDS))
        self.assertEqual(
            blocked_groups["prohibited_secret_fields"],
            list(PROHIBITED_SECRET_FIELDS),
        )

    def test_contract_manifest_matches_report_contract(self) -> None:
        manifest = build_phase14c_candidate_decision_support_contract_manifest()
        report_contract = manifest["report_contract"]
        report = build_phase14c_candidate_decision_support_report()

        self.assertEqual(report_contract["top_level_fields"], list(REPORT_TOP_LEVEL_FIELDS))
        self.assertEqual(
            report_contract["validation_payload_fields"],
            list(VALIDATION_PAYLOAD_FIELDS),
        )
        self.assertEqual(tuple(report), REPORT_TOP_LEVEL_FIELDS)
        self.assertEqual(
            report_contract["inert_false_fields"],
            list(REPORT_INERT_FALSE_FIELDS),
        )
        self.assertEqual(
            report_contract["inert_true_field_paths"],
            list(REPORT_INERT_TRUE_FIELD_PATHS),
        )
        for field in report_contract["inert_false_fields"]:
            with self.subTest(field=field):
                self.assertFalse(report[field])
        for path in report_contract["inert_true_field_paths"]:
            with self.subTest(path=path):
                self.assertTrue(_path_value(report, path))
        for field in report_contract["raw_input_echo_fields_absent"]:
            with self.subTest(field=field):
                self.assertNotIn(field, report)

    def test_report_embeds_contract_manifest_as_inert_audit_metadata(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        manifest = build_phase14c_candidate_decision_support_contract_manifest()
        non_authorization = report["contract_manifest"]["non_authorization_contract"]

        self.assertEqual(report["contract_manifest"], manifest)
        self.assertIn("contract_manifest", REPORT_TOP_LEVEL_FIELDS)
        self.assertTrue(non_authorization["candidate_review_tracking_only"])
        self.assertTrue(non_authorization["phase14_c_blocked"])
        self.assertTrue(non_authorization["inert_report_only"])
        self.assertEqual(non_authorization["readiness.status"], "not_ready")
        self.assertFalse(non_authorization["candidate_approved"])
        self.assertFalse(non_authorization["live_service_access_authorized"])
        self.assertFalse(non_authorization["credentials_auth_handling_authorized"])
        self.assertFalse(non_authorization["runtime_operator_scaffolding_authorized"])

    def test_blocked_report_embeds_manifest_without_echoing_unsafe_input(self) -> None:
        unsafe_key = "secret-report-manifest-key-must-not-leak"
        unsafe_values = (
            "secret-report-manifest-decision-value",
            "secret-report-manifest-note-value",
            "secret-report-manifest-key-value",
        )
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_option": unsafe_values[0],
                "notes": {"api_key": unsafe_values[1]},
                unsafe_key: unsafe_values[2],
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertIsNone(validation["normalized_record"])
        self.assertEqual(
            report["contract_manifest"],
            build_phase14c_candidate_decision_support_contract_manifest(),
        )
        self.assertNotIn(unsafe_key, serialized_report)
        for unsafe_value in unsafe_values:
            with self.subTest(unsafe_value=unsafe_value):
                self.assertNotIn(unsafe_value, serialized_report)

    def test_report_contract_validator_accepts_default_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        validation = validate_phase14c_candidate_decision_support_report_contract(report)

        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": True,
                "reasons": ["Decision-support report matches the inert contract."],
            },
        )

    def test_report_contract_validator_accepts_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
            }
        )

        validation = validate_phase14c_candidate_decision_support_report_contract(report)

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertTrue(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.reasons,
            ("Decision-support report matches the inert contract.",),
        )

    def test_report_contract_validator_blocks_tampered_report_contract(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        report["status"] = "ready"
        report["candidate_approved"] = True
        report["contract_manifest"] = {"schema_version": "tampered"}
        report["readiness"] = {
            "status": "ready",
            "inert_report_only": False,
            "live_rails_activated": True,
        }

        validation = validate_phase14c_candidate_decision_support_report_contract(report)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report status is outside allowed decision-support statuses.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report status does not match validation status.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report contract_manifest does not match the static manifest.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report field candidate_approved must remain false.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report readiness.status must remain not_ready.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report readiness.live_rails_activated must remain false.",
            validation.reasons,
        )

    def test_report_contract_validator_does_not_echo_unsafe_report_tokens(self) -> None:
        unsafe_key = "secret-report-contract-key-must-not-leak"
        unsafe_value = "secret-report-contract-value-must-not-leak"
        unsafe_manifest_value = "secret-report-contract-manifest-value-must-not-leak"
        report = {
            **build_phase14c_candidate_decision_support_report(),
            unsafe_key: unsafe_value,
            "contract_manifest": {"unsafe": unsafe_manifest_value},
            "raw_decision_record": {"unsafe": unsafe_value},
        }

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report top-level fields do not match the contract.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report contract_manifest does not match the static manifest.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report contains raw decision-record echo fields.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_key, serialized_validation)
        self.assertNotIn(unsafe_value, serialized_validation)
        self.assertNotIn(unsafe_manifest_value, serialized_validation)

    def test_report_contract_validator_requires_report_payload(self) -> None:
        validation = validate_phase14c_candidate_decision_support_report_contract(None)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertEqual(
            validation.to_dict(),
            {
                "report_matches_inert_contract": False,
                "reasons": [
                    "No decision-support report was supplied; the inert report contract remains required.",
                ],
            },
        )

    def test_report_contract_validator_blocks_each_missing_top_level_field(self) -> None:
        for field in REPORT_TOP_LEVEL_FIELDS:
            with self.subTest(field=field):
                report = build_phase14c_candidate_decision_support_report()
                del report[field]

                validation = validate_phase14c_candidate_decision_support_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    "Decision-support report top-level fields do not match the contract.",
                    validation.reasons,
                )

    def test_report_contract_validator_blocks_extra_top_level_field_without_echo(self) -> None:
        unsafe_key = "secret-report-extra-key-must-not-leak"
        unsafe_value = "secret-report-extra-value-must-not-leak"
        report = {
            **build_phase14c_candidate_decision_support_report(),
            unsafe_key: unsafe_value,
        }

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report top-level fields do not match the contract.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_key, serialized_validation)
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_every_inert_false_field_drift(self) -> None:
        for field in REPORT_INERT_FALSE_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-report-false-drift"
                report = build_phase14c_candidate_decision_support_report()
                report[field] = unsafe_value

                validation = validate_phase14c_candidate_decision_support_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    f"Decision-support report field {field} must remain false.",
                    validation.reasons,
                )
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_every_inert_true_path_drift(self) -> None:
        for path in REPORT_INERT_TRUE_FIELD_PATHS:
            with self.subTest(path=path):
                report = build_phase14c_candidate_decision_support_report()
                _set_path_value(report, path, False)

                validation = validate_phase14c_candidate_decision_support_report_contract(report)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    f"Decision-support report path {path} must remain true.",
                    validation.reasons,
                )

    def test_report_contract_validator_blocks_raw_echo_fields_without_echoing_values(self) -> None:
        for field in REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-raw-echo-value"
                report = build_phase14c_candidate_decision_support_report()
                report[field] = {"unsafe": unsafe_value}

                validation = validate_phase14c_candidate_decision_support_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    "Decision-support report contains raw decision-record echo fields.",
                    validation.reasons,
                )
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_validation_payload_mismatch(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        report["decision_record_validation"] = {
            **report["decision_record_validation"],
            "status": PilotPrepStatus.BLOCKED.value,
            "record_accepted_as_unfilled_template": False,
        }

        validation = validate_phase14c_candidate_decision_support_report_contract(report)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report status does not match validation status.",
            validation.reasons,
        )
        self.assertIn(
            "Decision-support report unfilled-template flag does not match validation payload.",
            validation.reasons,
        )

    def test_report_contract_validator_blocks_metadata_drift_without_echo(self) -> None:
        cases = (
            (
                "schema_version",
                "matrix-secret-report-schema-version",
                "Decision-support report schema_version does not match the contract.",
            ),
            (
                "phase_label",
                "matrix-secret-report-phase-label",
                "Decision-support report phase_label does not match the contract.",
            ),
            (
                "status",
                "matrix-secret-report-status",
                "Decision-support report status is outside allowed decision-support statuses.",
            ),
        )
        for field, unsafe_value, expected_reason in cases:
            with self.subTest(field=field):
                report = build_phase14c_candidate_decision_support_report()
                report[field] = unsafe_value

                validation = validate_phase14c_candidate_decision_support_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_readiness_payload_drift_without_echo(self) -> None:
        cases = (
            (
                "payload",
                None,
                "matrix-secret-readiness-payload",
                "Decision-support report readiness payload is missing.",
            ),
            (
                "status",
                "status",
                "matrix-secret-readiness-status",
                "Decision-support report readiness.status must remain not_ready.",
            ),
            (
                "inert_report_only",
                "inert_report_only",
                "matrix-secret-readiness-inert-report-only",
                "Decision-support report readiness.inert_report_only must remain true.",
            ),
            (
                "live_rails_activated",
                "live_rails_activated",
                "matrix-secret-readiness-live-rails",
                "Decision-support report readiness.live_rails_activated must remain false.",
            ),
        )
        for label, readiness_field, unsafe_value, expected_reason in cases:
            with self.subTest(label=label):
                report = build_phase14c_candidate_decision_support_report()
                if readiness_field is None:
                    report["readiness"] = unsafe_value
                else:
                    report["readiness"][readiness_field] = unsafe_value

                validation = validate_phase14c_candidate_decision_support_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_every_safety_posture_field_drift_without_echo(
        self,
    ) -> None:
        for field in SAFETY_POSTURE:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-safety-posture-drift"
                report = build_phase14c_candidate_decision_support_report()
                report["safety_posture"][field] = unsafe_value

                validation = validate_phase14c_candidate_decision_support_report_contract(report)
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    "Decision-support report safety_posture does not match the inert safety posture.",
                    validation.reasons,
                )
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_extra_safety_posture_key_without_echo(
        self,
    ) -> None:
        unsafe_key = "matrix-secret-safety-posture-key"
        unsafe_value = "matrix-secret-safety-posture-value"
        report = build_phase14c_candidate_decision_support_report()
        report["safety_posture"][unsafe_key] = unsafe_value

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report safety_posture does not match the inert safety posture.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_key, serialized_validation)
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_decision_option_drift_without_echo(
        self,
    ) -> None:
        unsafe_value = "matrix-secret-report-decision-option"
        report = build_phase14c_candidate_decision_support_report()
        report["decision_option"] = unsafe_value

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report decision_option must remain unselected.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_candidate_tracking_payload_drift_without_echo(
        self,
    ) -> None:
        unsafe_value = "matrix-secret-candidate-tracking-value"
        report = build_phase14c_candidate_decision_support_report()
        report["candidate_review_tracking"]["candidate"]["candidate_name"] = unsafe_value
        report["candidate_review_tracking"]["candidate"]["approved"] = True

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report candidate_review_tracking payload does not match the inert tracking contract.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_decision_record_template_drift_without_echo(
        self,
    ) -> None:
        unsafe_value = "matrix-secret-template-value"
        report = build_phase14c_candidate_decision_support_report()
        report["decision_record_template"]["notes"] = unsafe_value

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report decision_record_template does not match the false-default template.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_validation_payload_drift_without_echo(
        self,
    ) -> None:
        cases = (
            (
                "extra-field",
                lambda report, token: report["decision_record_validation"].update(
                    {"matrix-secret-validation-key": token}
                ),
                "Decision-support report decision_record_validation payload fields do not match the contract.",
                ("matrix-secret-validation-key",),
            ),
            (
                "unsafe-reason",
                lambda report, token: report["decision_record_validation"]["reasons"].append(
                    token
                ),
                "Decision-support report decision_record_validation reasons are outside the allowed contract.",
                (),
            ),
            (
                "unfilled-normalized-record",
                lambda report, token: report["decision_record_validation"][
                    "normalized_record"
                ].update({"candidate": token}),
                "Decision-support report unfilled normalized_record does not match the false-default template.",
                (),
            ),
            (
                "non-unfilled-normalized-record",
                lambda report, token: report["decision_record_validation"].update(
                    {"normalized_record": {"unsafe": token}}
                ),
                "Decision-support report non-unfilled normalized_record must remain absent.",
                (),
            ),
        )
        for label, mutate, expected_reason, extra_tokens in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-validation-payload-{label}"
                report = (
                    build_phase14c_candidate_decision_support_report(
                        {
                            **blank_phase14c_candidate_decision_support_record(),
                            "candidate_approved": True,
                        }
                    )
                    if label == "non-unfilled-normalized-record"
                    else build_phase14c_candidate_decision_support_report()
                )
                mutate(report, unsafe_value)

                validation = validate_phase14c_candidate_decision_support_report_contract(
                    report
                )
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)
                for extra_token in extra_tokens:
                    self.assertNotIn(extra_token, serialized_validation)

    def test_report_contract_validator_blocks_preflight_checklist_drift_without_echo(
        self,
    ) -> None:
        unsafe_value = "matrix-secret-preflight-checklist-value"
        report = build_phase14c_candidate_decision_support_report()
        report["preflight_checklist"].append(unsafe_value)

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report preflight_checklist does not match the validation payload.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_each_missing_validation_payload_field(
        self,
    ) -> None:
        for field in VALIDATION_PAYLOAD_FIELDS:
            with self.subTest(field=field):
                report = build_phase14c_candidate_decision_support_report()
                del report["decision_record_validation"][field]

                validation = validate_phase14c_candidate_decision_support_report_contract(
                    report
                )

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(
                    "Decision-support report decision_record_validation payload fields do not match the contract.",
                    validation.reasons,
                )

    def test_report_contract_validator_blocks_validation_payload_type_drift_without_echo(
        self,
    ) -> None:
        cases = (
            (
                "status",
                lambda payload, token: payload.update({"status": token}),
                "Decision-support report decision_record_validation status is outside allowed decision-support statuses.",
            ),
            (
                "record_accepted_as_unfilled_template",
                lambda payload, token: payload.update(
                    {"record_accepted_as_unfilled_template": token}
                ),
                "Decision-support report unfilled-template flag must remain boolean.",
            ),
            (
                "human_decision_recorded",
                lambda payload, token: payload.update({"human_decision_recorded": token}),
                "Decision-support report human_decision_recorded validation flag must remain boolean.",
            ),
            (
                "reasons",
                lambda payload, token: payload.update({"reasons": token}),
                "Decision-support report decision_record_validation reasons payload is missing.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                unsafe_value = f"matrix-secret-validation-type-{label}"
                report = build_phase14c_candidate_decision_support_report()
                mutate(report["decision_record_validation"], unsafe_value)

                validation = validate_phase14c_candidate_decision_support_report_contract(
                    report
                )
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_missing_payload_surfaces_without_echo(
        self,
    ) -> None:
        cases = (
            (
                "candidate_review_tracking",
                "matrix-secret-candidate-tracking-payload",
                "Decision-support report candidate_review_tracking payload does not match the inert tracking contract.",
            ),
            (
                "decision_record_template",
                "matrix-secret-decision-template-payload",
                "Decision-support report decision_record_template does not match the false-default template.",
            ),
            (
                "decision_record_validation",
                "matrix-secret-validation-payload",
                "Decision-support report decision_record_validation payload is missing.",
            ),
            (
                "preflight_checklist",
                "matrix-secret-preflight-payload",
                "Decision-support report preflight_checklist payload is missing.",
            ),
        )
        for field, unsafe_value, expected_reason in cases:
            with self.subTest(field=field):
                report = build_phase14c_candidate_decision_support_report()
                report[field] = unsafe_value

                validation = validate_phase14c_candidate_decision_support_report_contract(
                    report
                )
                serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

                self.assertFalse(validation.report_matches_inert_contract)
                self.assertIn(expected_reason, validation.reasons)
                self.assertNotIn(unsafe_value, serialized_validation)

    def test_report_contract_validator_blocks_preflight_checklist_type_drift_without_echo(
        self,
    ) -> None:
        unsafe_value = "matrix-secret-preflight-list-item"
        report = build_phase14c_candidate_decision_support_report()
        report["preflight_checklist"] = ["still-text", {"unsafe": unsafe_value}]

        validation = validate_phase14c_candidate_decision_support_report_contract(report)
        serialized_validation = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.report_matches_inert_contract)
        self.assertIn(
            "Decision-support report preflight_checklist payload is missing.",
            validation.reasons,
        )
        self.assertNotIn(unsafe_value, serialized_validation)

    def test_contract_manifest_allowed_statuses_cover_validation_outputs(self) -> None:
        manifest = build_phase14c_candidate_decision_support_contract_manifest()
        allowed_statuses = set(manifest["allowed_validation_statuses"])
        records = (
            None,
            blank_phase14c_candidate_decision_support_record(),
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_option": "reject candidate",
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "unknown_future_field": "must-not-pass",
            },
        )

        statuses = {
            validate_phase14c_candidate_decision_record(record).status.value
            for record in records
        }

        self.assertEqual(
            allowed_statuses,
            {PilotPrepStatus.DECISION_NEEDED.value, PilotPrepStatus.BLOCKED.value},
        )
        self.assertLessEqual(statuses, allowed_statuses)

    def test_validation_payload_shape_remains_explicit(self) -> None:
        validation = validate_phase14c_candidate_decision_record(
            blank_phase14c_candidate_decision_support_record()
        ).to_dict()

        self.assertEqual(
            set(validation),
            {
                "status",
                "record_accepted_as_unfilled_template",
                "human_decision_recorded",
                "reasons",
                "normalized_record",
            },
        )
        self.assertEqual(validation["status"], PilotPrepStatus.DECISION_NEEDED.value)
        self.assertEqual(
            set(validation["normalized_record"]),
            set(REQUIRED_TEXT_DEFAULTS)
            | set(REQUIRED_FALSE_FIELDS)
            | set(FILLABLE_DECISION_FIELDS)
            | {
                "phase14_c_blocked",
                "candidate_review_tracking_only",
                "human_decision_recorded",
                "readiness.status",
            },
        )

    def test_missing_record_requires_false_default_template(self) -> None:
        validation = validate_phase14c_candidate_decision_record(None)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "No decision-support record was supplied; the false-default template remains required.",
            validation.reasons,
        )

    def test_selected_decision_option_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "decision_status": "recorded",
            "decision_option": "approve for later bounded repo-local prep packet",
            "decision_date": "2026-06-25",
            "decision_maker": "Chris",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertTrue(validation.human_decision_recorded)
        self.assertIn(
            "Decision record selects decision_status; this packet cannot record a human decision.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record selects decision_option; this packet cannot select approve, reject, or defer.",
            validation.reasons,
        )

    def test_approval_authorization_and_execution_flags_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "phase14_c_approved": True,
            "candidate_approved": True,
            "candidate_authorized": True,
            "candidate_activated": True,
            "candidate_run": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["candidate_activated"])
        self.assertFalse(report["candidate_run"])
        for field in (
            "phase14_c_approved",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated",
            "candidate_run",
        ):
            with self.subTest(field=field):
                self.assertTrue(any(field in reason for reason in reasons))

    def test_live_service_and_runtime_authorization_flags_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "todoist_write_authorized": True,
            "gmail_access_authorized": True,
            "calendar_write_authorized": True,
            "openclaw_authorized": True,
            "scheduler_background_activation_authorized": True,
            "production_db_activation_authorized": True,
            "protected_path_access_authorized": True,
            "live_model_api_calls_authorized": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["gmail_touched"])
        self.assertFalse(report["calendar_touched"])
        self.assertFalse(report["openclaw_called"])
        self.assertFalse(report["scheduler_activated"])
        for field in (
            "todoist_write_authorized",
            "gmail_access_authorized",
            "calendar_write_authorized",
            "openclaw_authorized",
            "scheduler_background_activation_authorized",
            "production_db_activation_authorized",
            "protected_path_access_authorized",
            "live_model_api_calls_authorized",
        ):
            with self.subTest(field=field):
                self.assertTrue(any(field in reason for reason in reasons))

    def test_dynamic_cleaning_watch_tower_agent_and_runtime_scaffolding_are_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "dynamic_cleaning_authorized": True,
            "fifteen_task_import_authorized": True,
            "skip_push_bump_behavior_authorized": True,
            "automatic_rescheduling_authorized": True,
            "watch_tower_adoption_authorized": True,
            "agent_directory_authorized": True,
            "claude_md_authorized": True,
            "runtime_operator_scaffolding_authorized": True,
        }

        report = build_phase14c_candidate_decision_support_report(record)
        reasons = report["decision_record_validation"]["reasons"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["watch_tower_adopted_or_merged"])
        self.assertFalse(report["agent_directory_created"])
        self.assertFalse(report["claude_md_created"])
        self.assertFalse(report["runtime_operator_scaffolding_created"])
        self.assertTrue(any("dynamic_cleaning_authorized" in reason for reason in reasons))
        self.assertTrue(any("watch_tower_adoption_authorized" in reason for reason in reasons))
        self.assertTrue(any("agent_directory_authorized" in reason for reason in reasons))
        self.assertTrue(any("claude_md_authorized" in reason for reason in reasons))

    def test_live_ids_credentials_and_secret_fields_are_blocked_even_when_nested(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "metadata": {
                "todoist_task_id": "1234567890",
                "oauth_token": "must-not-exist",
                "api_key": "must-not-exist",
                "secret": "must-not-exist",
            },
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertIn(
            "Decision record contains prohibited live/API field: todoist_task_id.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: oauth_token.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: api_key.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record contains prohibited credential/secret field: secret.",
            validation.reasons,
        )

    def test_unknown_top_level_schema_field_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "session_token": "novel-field-name-must-not-pass",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
            validation.reasons,
        )

    def test_nested_unknown_container_is_blocked_before_acceptance(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "metadata": {"session_token": "must-not-pass"},
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
            validation.reasons,
        )

    def test_blocked_report_does_not_echo_unknown_schema_key_names(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "secret-unknown-key-must-not-leak": (
                    "secret-unknown-value-must-not-leak"
                ),
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertIn(
            "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
            validation["reasons"],
        )
        self.assertNotIn("secret-unknown-key-must-not-leak", serialized_report)
        self.assertNotIn("secret-unknown-value-must-not-leak", serialized_report)

    def test_nested_payload_under_known_fillable_field_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "notes": {"session_token": "must-not-pass"},
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertTrue(validation.human_decision_recorded)
        self.assertIn(
            "Decision record fills notes; recording a human decision is out of scope.",
            validation.reasons,
        )

    def test_fillable_decision_field_values_do_not_echo_for_every_field(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-fillable-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        field: unsafe_value,
                    }
                )

                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertTrue(validation["human_decision_recorded"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record fills {field}; recording a human decision is out of scope.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_every_fillable_decision_field_blocks_and_marks_human_decision(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: "filled outside this packet",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertTrue(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record fills {field}; recording a human decision is out of scope.",
                    validation.reasons,
                )

    def test_every_fillable_decision_field_blocks_when_not_exact_empty(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: " ",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected an empty unfilled value.",
                    validation.reasons,
                )

    def test_every_required_false_field_blocks_when_truthy(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: True,
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertIn(
                    f"Decision record is marked {field}; this packet cannot approve, "
                    "authorize, activate, execute, or grant live access.",
                    validation.reasons,
                )

    def test_every_required_false_field_blocks_when_not_boolean_false(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: "false",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected boolean false.",
                    validation.reasons,
                )

    def test_false_field_non_boolean_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": "matrix-secret-false-field-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes candidate_approved; expected boolean false.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-false-field-value", serialized_report)

    def test_required_false_field_non_boolean_values_do_not_echo_for_every_field(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-false-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        field: unsafe_value,
                    }
                )

                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertFalse(validation["human_decision_recorded"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record changes {field}; expected boolean false.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_known_schema_fields_match_false_default_template(self) -> None:
        record_fields = set(blank_phase14c_candidate_decision_support_record())

        self.assertEqual(record_fields, set(KNOWN_DECISION_RECORD_FIELDS))

    def test_validation_statuses_remain_decision_needed_or_blocked_only(self) -> None:
        records = (
            None,
            blank_phase14c_candidate_decision_support_record(),
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_option": "reject candidate",
            },
            {
                **blank_phase14c_candidate_decision_support_record(),
                "unknown_future_field": "must-not-pass",
            },
        )

        statuses = {
            validate_phase14c_candidate_decision_record(record).status
            for record in records
        }

        self.assertLessEqual(
            statuses,
            {PilotPrepStatus.DECISION_NEEDED, PilotPrepStatus.BLOCKED},
        )

    def test_candidate_context_drift_is_blocked(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "candidate": "Different Candidate",
            "weekday": "Tuesday",
            "area": "Garage",
            "current_status": "approved",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertIn(
            "Decision record changes candidate; expected the unfilled false-default template value.",
            validation.reasons,
        )
        self.assertIn(
            "Decision record changes current_status; expected the unfilled false-default template value.",
            validation.reasons,
        )

    def test_every_required_text_default_blocks_when_not_exact_literal(self) -> None:
        for field, expected in REQUIRED_TEXT_DEFAULTS.items():
            with self.subTest(field=field):
                record = {
                    **blank_phase14c_candidate_decision_support_record(),
                    field: f" {expected} ",
                }

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision record changes {field}; expected the unfilled false-default "
                    "template value.",
                    validation.reasons,
                )

    def test_required_text_default_drift_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "weekday": "matrix-secret-text-default-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes weekday; expected the unfilled false-default "
            "template value.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-text-default-value", serialized_report)

    def test_required_text_default_drift_values_do_not_echo_for_every_field(self) -> None:
        for field in REQUIRED_TEXT_DEFAULTS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-text-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        field: unsafe_value,
                    }
                )

                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record changes {field}; expected the unfilled false-default "
                    "template value.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_readiness_status_blocks_when_not_exact_literal(self) -> None:
        record = {
            **blank_phase14c_candidate_decision_support_record(),
            "readiness.status": " not_ready ",
        }

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.BLOCKED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertIn(
            "Decision record changes readiness.status; expected 'not_ready'.",
            validation.reasons,
        )

    def test_readiness_status_drift_value_is_not_echoed_in_blocked_report(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "readiness.status": "matrix-secret-readiness-status-value",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record changes readiness.status; expected 'not_ready'.",
            validation["reasons"],
        )
        self.assertNotIn("matrix-secret-readiness-status-value", serialized_report)

    def test_each_required_text_default_missing_fails_closed_as_decision_needed(self) -> None:
        for field, expected in REQUIRED_TEXT_DEFAULTS.items():
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required field is missing: {field}={expected}.",
                    validation.reasons,
                )

    def test_each_required_false_field_missing_fails_closed_as_decision_needed(self) -> None:
        for field in REQUIRED_FALSE_FIELDS:
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required false field is missing: {field}.",
                    validation.reasons,
                )

    def test_each_fillable_decision_field_missing_fails_closed_as_decision_needed(self) -> None:
        for field in FILLABLE_DECISION_FIELDS:
            with self.subTest(field=field):
                record = blank_phase14c_candidate_decision_support_record()
                del record[field]

                validation = validate_phase14c_candidate_decision_record(record)

                self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
                self.assertFalse(validation.record_accepted_as_unfilled_template)
                self.assertFalse(validation.human_decision_recorded)
                self.assertIn(
                    f"Decision-support record required unfilled field is missing: {field}.",
                    validation.reasons,
                )

    def test_missing_readiness_status_fails_closed_as_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        del record["readiness.status"]

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertFalse(validation.human_decision_recorded)
        self.assertIn(
            "Decision-support record required field is missing: "
            "readiness.status=not_ready.",
            validation.reasons,
        )

    def test_missing_required_false_field_fails_closed_as_decision_needed(self) -> None:
        record = blank_phase14c_candidate_decision_support_record()
        del record["candidate_approved"]

        validation = validate_phase14c_candidate_decision_record(record)

        self.assertEqual(validation.status, PilotPrepStatus.DECISION_NEEDED)
        self.assertFalse(validation.record_accepted_as_unfilled_template)
        self.assertIn(
            "Decision-support record required false field is missing: candidate_approved.",
            validation.reasons,
        )

    def test_report_preserves_inert_safety_posture_and_candidate_tracking_only(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        tracking = report["candidate_review_tracking"]

        self.assertTrue(report["candidate_review_tracking_only"])
        self.assertEqual(tracking["candidate"]["candidate_name"], "Clean Kitchen Countertops and Stovetop")
        self.assertEqual(tracking["candidate"]["weekday"], "Monday")
        self.assertEqual(tracking["candidate"]["home_area"], "Kitchen")
        self.assertTrue(tracking["candidate"]["review_tracking_only"])
        self.assertFalse(tracking["candidate"]["selected"])
        self.assertFalse(tracking["candidate"]["approved"])
        self.assertFalse(tracking["candidate"]["authorized"])
        self.assertFalse(tracking["candidate"]["live_pilot_run"])
        self.assertTrue(report["phase14_c_blocked"])
        self.assertEqual(report["readiness"]["status"], "not_ready")
        self.assertTrue(report["readiness"]["inert_report_only"])
        self.assertFalse(report["readiness"]["live_rails_activated"])
        self.assertEqual(report["safety_posture"], SAFETY_POSTURE)

    def test_report_live_external_and_runtime_flags_remain_false(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        self.assertFalse(report["gmail_touched"])
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["calendar_touched"])
        self.assertFalse(report["openclaw_called"])
        self.assertFalse(report["scheduler_activated"])
        self.assertFalse(report["background_loop_activated"])
        self.assertFalse(report["launch_agent_installed"])
        self.assertFalse(report["crontab_modified"])
        self.assertFalse(report["daemon_started"])
        self.assertFalse(report["credentials_loaded"])
        self.assertFalse(report["credentials_read"])
        self.assertFalse(report["production_db_path_active"])
        self.assertFalse(report["personalos_markdown_written"])
        self.assertFalse(report["protected_paths_touched"])
        self.assertFalse(report["live_model_api_called"])
        self.assertFalse(report["external_services_contacted"])
        self.assertFalse(report["external_mutation"])

    def test_report_top_level_inert_false_fields_remain_false(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        for field in REPORT_INERT_FALSE_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(report[field])

    def test_report_inert_true_fields_remain_true(self) -> None:
        report = build_phase14c_candidate_decision_support_report()

        for path in REPORT_INERT_TRUE_FIELD_PATHS:
            with self.subTest(path=path):
                self.assertTrue(_path_value(report, path))

    def test_blocked_report_does_not_echo_unsafe_input_values(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "candidate_approved": True,
                "notes": {
                    "api_key": "secret-value-must-not-leak",
                    "todoist_task_id": "live-id-must-not-leak",
                },
                "unknown_future_field": "unknown-value-must-not-leak",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertIsNone(report["decision_record_validation"]["normalized_record"])
        self.assertFalse(report["candidate_approved"])
        self.assertFalse(report["candidate_authorized"])
        self.assertFalse(report["candidate_activated"])
        self.assertFalse(report["candidate_run"])
        self.assertFalse(report["todoist_touched"])
        self.assertFalse(report["credentials_loaded"])
        self.assertNotIn("secret-value-must-not-leak", serialized_report)
        self.assertNotIn("live-id-must-not-leak", serialized_report)
        self.assertNotIn("unknown-value-must-not-leak", serialized_report)

    def test_blocked_report_does_not_echo_unsafe_decision_or_drift_values(self) -> None:
        report = build_phase14c_candidate_decision_support_report(
            {
                **blank_phase14c_candidate_decision_support_record(),
                "decision_status": "secret-status-value-must-not-leak",
                "decision_option": "secret-option-value-must-not-leak",
                "candidate": "secret-candidate-value-must-not-leak",
                "weekday": "secret-weekday-value-must-not-leak",
                "area": "secret-area-value-must-not-leak",
                "current_status": "secret-current-status-value-must-not-leak",
            }
        )

        serialized_report = json.dumps(report, sort_keys=True)
        validation = report["decision_record_validation"]

        self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
        self.assertFalse(report["decision_record_validated_as_unfilled"])
        self.assertFalse(report["human_decision_recorded"])
        self.assertTrue(validation["human_decision_recorded"])
        self.assertIsNone(validation["normalized_record"])
        self.assertIn(
            "Decision record selects decision_status; this packet cannot record a human decision.",
            validation["reasons"],
        )
        self.assertIn(
            "Decision record selects decision_option; this packet cannot select approve, reject, or defer.",
            validation["reasons"],
        )
        for unsafe_value in (
            "secret-status-value-must-not-leak",
            "secret-option-value-must-not-leak",
            "secret-candidate-value-must-not-leak",
            "secret-weekday-value-must-not-leak",
            "secret-area-value-must-not-leak",
            "secret-current-status-value-must-not-leak",
        ):
            with self.subTest(unsafe_value=unsafe_value):
                self.assertNotIn(unsafe_value, serialized_report)

    def test_blocked_report_sanitization_matrix_rejects_caller_controlled_tokens(self) -> None:
        cases = (
            (
                "unknown_schema",
                {
                    "matrix-secret-unknown-key": "matrix-secret-unknown-value",
                },
                ("matrix-secret-unknown-key", "matrix-secret-unknown-value"),
            ),
            (
                "decision_selection",
                {
                    "decision_status": "matrix-secret-status-value",
                    "decision_option": "matrix-secret-option-value",
                    "decision_maker": "matrix-secret-maker-value",
                },
                (
                    "matrix-secret-status-value",
                    "matrix-secret-option-value",
                    "matrix-secret-maker-value",
                ),
            ),
            (
                "candidate_drift",
                {
                    "candidate": "matrix-secret-candidate-value",
                    "weekday": "matrix-secret-weekday-value",
                    "area": "matrix-secret-area-value",
                    "current_status": "matrix-secret-status-drift-value",
                },
                (
                    "matrix-secret-candidate-value",
                    "matrix-secret-weekday-value",
                    "matrix-secret-area-value",
                    "matrix-secret-status-drift-value",
                ),
            ),
            (
                "nested_fillable_payload",
                {
                    "notes": {
                        "session_token": "matrix-secret-nested-token-value",
                    },
                },
                ("matrix-secret-nested-token-value",),
            ),
        )

        for name, changes, unsafe_tokens in cases:
            with self.subTest(name=name):
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        **changes,
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(
                    report["decision_record_validation"]["normalized_record"]
                )
                for unsafe_token in unsafe_tokens:
                    self.assertNotIn(unsafe_token, serialized_report)

    def test_nested_prohibited_field_values_are_blocked_without_echo(self) -> None:
        cases = (
            (
                "nested_live_api_fields",
                {
                    "matrix-secret-live-container": {
                        "todoist_task_id": "matrix-secret-live-id-value",
                        "live_object_id": "matrix-secret-live-object-value",
                    },
                },
                (
                    "matrix-secret-live-container",
                    "matrix-secret-live-id-value",
                    "matrix-secret-live-object-value",
                ),
                (
                    "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
                    "Decision record contains prohibited live/API field: todoist_task_id.",
                    "Decision record contains prohibited live/API field: live_object_id.",
                ),
            ),
            (
                "nested_credential_secret_fields",
                {
                    "matrix-secret-credential-container": {
                        "api_key": "matrix-secret-api-key-value",
                        "oauth_token": "matrix-secret-oauth-token-value",
                        "client_secret": "matrix-secret-client-secret-value",
                    },
                },
                (
                    "matrix-secret-credential-container",
                    "matrix-secret-api-key-value",
                    "matrix-secret-oauth-token-value",
                    "matrix-secret-client-secret-value",
                ),
                (
                    "Decision record contains unknown schema fields; only the false-default template schema is accepted.",
                    "Decision record contains prohibited credential/secret field: api_key.",
                    "Decision record contains prohibited credential/secret field: oauth_token.",
                    "Decision record contains prohibited credential/secret field: client_secret.",
                ),
            ),
        )

        for name, changes, unsafe_tokens, expected_reasons in cases:
            with self.subTest(name=name):
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        **changes,
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertFalse(report["human_decision_recorded"])
                self.assertFalse(validation["human_decision_recorded"])
                self.assertIsNone(validation["normalized_record"])
                for reason in expected_reasons:
                    self.assertIn(reason, validation["reasons"])
                for unsafe_token in unsafe_tokens:
                    self.assertNotIn(unsafe_token, serialized_report)

    def test_prohibited_live_field_values_do_not_echo_for_every_field(self) -> None:
        for field in PROHIBITED_LIVE_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-live-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        "notes": {field: unsafe_value},
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record contains prohibited live/API field: {field}.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_prohibited_secret_field_values_do_not_echo_for_every_field(self) -> None:
        for field in PROHIBITED_SECRET_FIELDS:
            with self.subTest(field=field):
                unsafe_value = f"matrix-secret-{field}-secret-value"
                report = build_phase14c_candidate_decision_support_report(
                    {
                        **blank_phase14c_candidate_decision_support_record(),
                        "notes": {field: unsafe_value},
                    }
                )
                serialized_report = json.dumps(report, sort_keys=True)
                validation = report["decision_record_validation"]

                self.assertEqual(report["status"], PilotPrepStatus.BLOCKED.value)
                self.assertFalse(report["decision_record_validated_as_unfilled"])
                self.assertIsNone(validation["normalized_record"])
                self.assertIn(
                    f"Decision record contains prohibited credential/secret field: {field}.",
                    validation["reasons"],
                )
                self.assertNotIn(unsafe_value, serialized_report)

    def test_default_report_timestamp_is_deterministic(self) -> None:
        first_report = build_phase14c_candidate_decision_support_report()
        second_report = build_phase14c_candidate_decision_support_report()
        custom_report = build_phase14c_candidate_decision_support_report(
            generated_at_utc="2026-06-25T05:00:00+00:00"
        )

        self.assertEqual(first_report["generated_at_utc"], "2026-06-25T00:00:00+00:00")
        self.assertEqual(first_report["generated_at_utc"], second_report["generated_at_utc"])
        self.assertEqual(custom_report["generated_at_utc"], "2026-06-25T05:00:00+00:00")

    def test_checklist_preserves_non_authorization_boundary(self) -> None:
        report = build_phase14c_candidate_decision_support_report()
        checklist = "\n".join(report["preflight_checklist"])

        self.assertIn("Decision record is unfilled by default.", checklist)
        self.assertIn("Decision option remains unselected.", checklist)
        self.assertIn("No approve, reject, or defer decision is recorded.", checklist)
        self.assertIn("Phase 14-C remains blocked.", checklist)
        self.assertIn("Candidate is not approved, authorized, activated, or run.", checklist)
        self.assertIn("Todoist, Gmail, Calendar, OpenClaw", checklist)


def _path_value(mapping: dict[str, object], dotted_path: str) -> object:
    value: object = mapping
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            raise AssertionError(f"path segment {part!r} is not in a mapping")
        value = value[part]
    return value


def _set_path_value(mapping: dict[str, object], dotted_path: str, new_value: object) -> None:
    value: object = mapping
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        if not isinstance(value, dict):
            raise AssertionError(f"path segment {part!r} is not in a mapping")
        value = value[part]
    if not isinstance(value, dict):
        raise AssertionError(f"path segment {parts[-1]!r} is not in a mapping")
    value[parts[-1]] = new_value

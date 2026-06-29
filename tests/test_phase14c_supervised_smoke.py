import copy
import json
import tempfile
import unittest
from pathlib import Path

from personalos.phase14c_supervised_smoke import (
    BOUNDARY_FIELDS,
    DRY_RUN_COMPLETION_REPORT_FIELDS,
    DRY_RUN_REHEARSAL_ARTIFACT_NAMES,
    DRY_RUN_SAFETY_ASSERTION_FIELDS,
    DRY_RUN_MODE,
    LIVE_RUN_MODE,
    PHASE14C_SUPERVISED_SMOKE_DRY_RUN_STATUS,
    PHASE14C_SUPERVISED_SMOKE_MARKER,
    PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION,
    PHASE14C_SUPERVISED_SMOKE_STATUS,
    PHASE14C_SUPERVISED_SMOKE_TEMPLATE_RECIPIENT,
    PHASE14C_SUPERVISED_SMOKE_TEMPLATE_STATUS,
    PHASE14C_TODOIST_ADJUSTED_DUE_DATE,
    PHASE14C_TODOIST_DEFAULT_PROJECT,
    REQUEST_TEMPLATE_REPORT_FIELDS,
    REQUEST_TEMPLATE_SAFETY_ASSERTION_FIELDS,
    REQUEST_VALIDATION_REPORT_FIELDS,
    REQUEST_VALIDATION_SAFETY_ASSERTION_FIELDS,
    REQUIRED_CONFIG_ENTRY_NAMES,
    RUNBOOK_TOP_LEVEL_FIELDS,
    Phase14CSupervisedSmokeClients,
    build_default_phase14c_supervised_smoke_request,
    build_phase14c_gmail_self_send_readiness_report,
    build_phase14c_gmail_self_send_smoke_request,
    build_phase14c_credential_preflight_report,
    build_phase14c_supervised_live_smoke_status,
    build_phase14c_supervised_smoke_runbook,
    build_phase14c_supervised_smoke_request_template_report,
    build_phase14c_supervised_smoke_request_validation_report,
    execute_phase14c_supervised_smoke_request,
    resolve_phase14c_todoist_due_date,
    run_phase14c_openclaw_local_sandbox_smoke,
    run_phase14c_supervised_smoke_dry_run_rehearsal,
    validate_phase14c_supervised_smoke_request,
)


class Phase14CSupervisedSmokeTest(unittest.TestCase):
    def test_runbook_records_supervised_multi_rail_smoke_boundaries(self) -> None:
        runbook = build_phase14c_supervised_smoke_runbook()

        self.assertEqual(tuple(runbook), RUNBOOK_TOP_LEVEL_FIELDS)
        self.assertEqual(
            runbook["schema_version"], PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION
        )
        self.assertEqual(runbook["status"], PHASE14C_SUPERVISED_SMOKE_STATUS)
        self.assertEqual(runbook["test_marker"], PHASE14C_SUPERVISED_SMOKE_MARKER)
        self.assertEqual(
            {rail["rail"] for rail in runbook["rails"]},
            {"todoist", "google_calendar", "gmail", "openclaw"},
        )
        for rail in runbook["rails"]:
            with self.subTest(rail=rail["rail"]):
                self.assertEqual(rail["max_live_operations"], 1)
                self.assertTrue(rail["requires_marker"])
                self.assertTrue(rail["dry_run_allowed"])
                self.assertTrue(rail["live_run_allowed_after_human_initiation"])

        self.assertTrue(runbook["live_run_boundaries"]["manual_foreground_invocation_only"])
        self.assertTrue(
            runbook["live_run_boundaries"]["requires_current_human_live_test_initiation"]
        )
        for field in BOUNDARY_FIELDS:
            with self.subTest(field=field):
                self.assertFalse(runbook["live_run_boundaries"][field])
        self.assertFalse(runbook["repo_prep_safety"]["todoist_task_created"])
        self.assertFalse(runbook["repo_prep_safety"]["calendar_event_created"])
        self.assertFalse(runbook["repo_prep_safety"]["gmail_email_created_or_sent"])
        self.assertFalse(runbook["repo_prep_safety"]["openclaw_invoked"])
        self.assertFalse(runbook["repo_prep_safety"]["credential_values_read"])
        smoke_status = runbook["supervised_live_smoke_status"]
        self.assertEqual(smoke_status["readiness_status"], "not_ready")
        self.assertFalse(smoke_status["broad_live_activation"])
        self.assertTrue(smoke_status["calendar_external_write_happened"])
        self.assertEqual(smoke_status["supervised_external_write_count"], 1)
        self.assertEqual(smoke_status["rails"]["google_calendar"]["status"], "passed")
        self.assertEqual(smoke_status["rails"]["gmail"]["status"], "not_run")
        self.assertEqual(
            smoke_status["rails"]["todoist"]["target_project"],
            PHASE14C_TODOIST_DEFAULT_PROJECT,
        )
        self.assertEqual(
            smoke_status["rails"]["openclaw"]["harness_function"],
            "run_phase14c_openclaw_local_sandbox_smoke",
        )

    def test_default_dry_run_request_validates_without_credentials(self) -> None:
        request = build_default_phase14c_supervised_smoke_request()
        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertTrue(validation.accepted)
        self.assertEqual(validation.status, "accepted")
        self.assertEqual(
            validation.reasons,
            ("Smoke request satisfies Phase 14-C supervised guardrails.",),
        )
        self.assertEqual(
            validation.missing_config_entry_names, REQUIRED_CONFIG_ENTRY_NAMES
        )
        self.assertEqual(
            validation.normalized_request["rail_operation_counts"],
            {
                "todoist_tasks": 1,
                "calendar_events": 1,
                "gmail_emails": 1,
                "openclaw_invocations": 1,
            },
        )
        task = validation.normalized_request["rails"]["todoist"]["task"]
        self.assertEqual(task["project"], PHASE14C_TODOIST_DEFAULT_PROJECT)
        self.assertEqual(task["due_date"], PHASE14C_TODOIST_ADJUSTED_DUE_DATE)
        self.assertEqual(task["subtasks"], [])
        self.assertEqual(task["labels"], [])
        invocation = validation.normalized_request["rails"]["openclaw"]["invocation"]
        self.assertEqual(invocation["name"], "phase14c_smoke_test")
        self.assertFalse(invocation["external_mutation"])

    def test_supervised_live_smoke_status_records_calendar_pass_without_activation(
        self,
    ) -> None:
        status = build_phase14c_supervised_live_smoke_status()

        self.assertEqual(status["readiness_status"], "not_ready")
        self.assertFalse(status["broad_live_activation"])
        self.assertTrue(status["rails"]["google_calendar"]["external_write_happened"])
        self.assertEqual(
            status["rails"]["google_calendar"]["object_id"],
            "memu6fhql6stl71auv05e1a6d0",
        )
        self.assertFalse(status["rails"]["gmail"]["external_write_happened"])
        self.assertFalse(status["rails"]["todoist"]["external_write_happened"])
        self.assertFalse(status["rails"]["openclaw"]["external_write_happened"])
        self.assertTrue(
            all(
                value is False
                for value in status["safety_assertions"].values()
            )
        )

    def test_request_template_report_builds_dry_run_template_without_authorization(
        self,
    ) -> None:
        report = build_phase14c_supervised_smoke_request_template_report()
        request = report["request"]
        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertEqual(tuple(report), REQUEST_TEMPLATE_REPORT_FIELDS)
        self.assertEqual(report["status"], PHASE14C_SUPERVISED_SMOKE_TEMPLATE_STATUS)
        self.assertEqual(report["mode"], DRY_RUN_MODE)
        self.assertTrue(report["template_only_not_authorization"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertEqual(request["mode"], DRY_RUN_MODE)
        self.assertFalse(request["live_run_requested"])
        self.assertIsNone(request["approval_reference"])
        self.assertEqual(
            request["controlled_test_recipients"],
            [PHASE14C_SUPERVISED_SMOKE_TEMPLATE_RECIPIENT],
        )
        self.assertEqual(
            request["rails"]["gmail"]["emails"][0]["to"],
            [PHASE14C_SUPERVISED_SMOKE_TEMPLATE_RECIPIENT],
        )
        self.assertTrue(validation.accepted)
        self.assertTrue(report["validation_preview"]["accepted"])
        self.assertNotIn("normalized_request", report["validation_preview"])
        self.assertEqual(
            tuple(report["safety_assertions"]),
            REQUEST_TEMPLATE_SAFETY_ASSERTION_FIELDS,
        )
        for field, value in report["safety_assertions"].items():
            with self.subTest(field=field):
                expected = field == "template_only_not_authorization"
                self.assertIs(value, expected)

    def test_live_run_request_template_is_not_ready_or_authorized(self) -> None:
        report = build_phase14c_supervised_smoke_request_template_report(
            mode=LIVE_RUN_MODE
        )
        request = report["request"]

        self.assertEqual(report["mode"], LIVE_RUN_MODE)
        self.assertEqual(request["mode"], LIVE_RUN_MODE)
        self.assertFalse(request["live_run_requested"])
        self.assertIsNone(request["approval_reference"])
        self.assertFalse(report["ready_for_live_execution"])
        self.assertFalse(report["validation_preview"]["accepted"])
        self.assertIsNone(report["validation_preview"]["normalized_request_summary"])
        self.assertIn(
            "Set live_run_requested=true only after explicit current live-test initiation.",
            report["operator_fill_required"],
        )

    def test_credential_preflight_reports_names_only_without_values(self) -> None:
        secret_values = {
            "PERSONALOS_PHASE14C_TODOIST_TOKEN": "todoist-secret-value",
            "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL": "calendar-secret-value",
            "PERSONALOS_PHASE14C_GMAIL_CREDENTIAL": "gmail-secret-value",
        }

        report = build_phase14c_credential_preflight_report(secret_values)
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(
            report["missing_config_entry_names"],
            ["PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE"],
        )
        self.assertTrue(report["reports_missing_names_only"])
        self.assertFalse(report["credential_values_read"])
        self.assertFalse(report["credential_values_logged"])
        self.assertNotIn("todoist-secret-value", serialized)
        self.assertNotIn("calendar-secret-value", serialized)
        self.assertNotIn("gmail-secret-value", serialized)

    def test_request_validation_report_redacts_accepted_request_values(self) -> None:
        private_recipient = "private.phase14c@example.test"
        request = build_default_phase14c_supervised_smoke_request(
            controlled_test_recipient=private_recipient
        )
        report = build_phase14c_supervised_smoke_request_validation_report(
            request,
            available_config_names={
                "PERSONALOS_PHASE14C_TODOIST_TOKEN": "todoist-secret-value",
            },
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(tuple(report), REQUEST_VALIDATION_REPORT_FIELDS)
        self.assertEqual(report["status"], "request_validation_completed")
        self.assertTrue(report["accepted"])
        self.assertEqual(
            tuple(report["safety_assertions"]),
            REQUEST_VALIDATION_SAFETY_ASSERTION_FIELDS,
        )
        for value in report["safety_assertions"].values():
            self.assertIs(value, False)
        self.assertEqual(report["input_request_summary"]["rails"]["gmail"]["to_count"], 1)
        self.assertNotIn("normalized_request", report["validation"])
        self.assertIn("normalized_request_summary", report["validation"])
        self.assertTrue(
            all(
                report["validation"]["normalized_request_summary"][
                    "boundaries_remain_false"
                ].values()
            )
        )
        self.assertNotIn(private_recipient, serialized)
        self.assertNotIn("todoist-secret-value", serialized)

    def test_request_validation_report_blocked_does_not_echo_unsafe_values(self) -> None:
        unsafe = "secret-token-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request()
        request["test_marker"] = unsafe
        request["rails"]["gmail"]["emails"][0]["to"] = [unsafe]

        report = build_phase14c_supervised_smoke_request_validation_report(request)
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], "request_validation_completed")
        self.assertFalse(report["accepted"])
        self.assertFalse(report["validation"]["accepted"])
        self.assertNotIn("normalized_request", report["validation"])
        self.assertIsNone(report["validation"]["normalized_request_summary"])
        self.assertNotIn(unsafe, serialized)

    def test_dry_run_execution_never_calls_clients(self) -> None:
        clients = _fake_clients()
        report = execute_phase14c_supervised_smoke_request(
            build_default_phase14c_supervised_smoke_request(),
            clients=clients,
        )

        self.assertEqual(report["status"], "dry_run_validated")
        self.assertFalse(report["live_run_executed"])
        self.assertFalse(report["external_mutation"])
        self.assertEqual(
            report["rail_operation_counts"],
            {
                "todoist_tasks": 0,
                "calendar_events": 0,
                "gmail_emails": 0,
                "openclaw_invocations": 0,
            },
        )
        self.assertEqual(clients.todoist.calls, [])
        self.assertEqual(clients.google_calendar.calls, [])
        self.assertEqual(clients.gmail.calls, [])
        self.assertEqual(clients.openclaw.calls, [])
        _assert_execution_validation_redacted(report)

    def test_dry_run_rehearsal_writes_redacted_safe_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "phase14c-smoke-rehearsal"

            result = run_phase14c_supervised_smoke_dry_run_rehearsal(output_dir)

            self.assertEqual(result.output_dir, str(output_dir.resolve(strict=False)))
            self.assertEqual(
                tuple(result.artifact_paths),
                DRY_RUN_REHEARSAL_ARTIFACT_NAMES,
            )
            for path in result.artifact_paths.values():
                self.assertTrue(Path(path).is_file(), path)

            report = result.completion_report
            self.assertEqual(tuple(report), DRY_RUN_COMPLETION_REPORT_FIELDS)
            self.assertEqual(report["status"], PHASE14C_SUPERVISED_SMOKE_DRY_RUN_STATUS)
            self.assertEqual(report["mode"], "dry_run")
            self.assertTrue(report["validation"]["accepted"])
            self.assertNotIn("normalized_request", report["validation"])
            self.assertIn(
                "normalized_request_summary",
                report["validation"],
            )
            self.assertTrue(
                all(
                    report["validation"]["normalized_request_summary"][
                        "boundaries_remain_false"
                    ].values()
                )
            )
            self.assertEqual(report["deviations"], [])
            self.assertEqual(report["rail_operation_counts"]["fake_client_calls"], 4)
            self.assertEqual(report["rail_operation_counts"]["real_external_operations"], 0)
            self.assertEqual(report["rail_operation_counts"]["simulated_todoist_tasks"], 1)
            self.assertEqual(
                report["rail_operation_counts"]["simulated_calendar_events"],
                1,
            )
            self.assertEqual(report["rail_operation_counts"]["simulated_gmail_emails"], 1)
            self.assertEqual(
                report["rail_operation_counts"]["simulated_openclaw_invocations"],
                1,
            )
            for rail in ("todoist", "google_calendar", "gmail", "openclaw"):
                with self.subTest(rail=rail):
                    fake_result = report["fake_client_results"][rail]
                    self.assertTrue(fake_result["marked"])
                    self.assertFalse(fake_result["external_mutation"])
                    self.assertFalse(fake_result["network_called"])
                    self.assertFalse(fake_result["credentials_read"])

            safety = report["safety_assertions"]
            self.assertEqual(tuple(safety), DRY_RUN_SAFETY_ASSERTION_FIELDS)
            for field in DRY_RUN_SAFETY_ASSERTION_FIELDS:
                with self.subTest(field=field):
                    expected = field == "writes_only_output_dir"
                    self.assertIs(safety[field], expected)

            request_artifact = _load_json(result.artifact_paths["request.json"])
            self.assertEqual(request_artifact["rails"]["gmail"]["to_count"], 1)
            self.assertNotIn("boundaries", request_artifact)
            self.assertTrue(all(request_artifact["boundaries_remain_false"].values()))
            for path in result.artifact_paths.values():
                with self.subTest(path=path):
                    self.assertNotIn(
                        "self.phase14c.test@example.test",
                        Path(path).read_text(encoding="utf-8"),
                    )

    def test_dry_run_rehearsal_blocks_unsafe_or_reused_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "phase14c-smoke-rehearsal"
            run_phase14c_supervised_smoke_dry_run_rehearsal(output_dir)

            with self.assertRaisesRegex(ValueError, "choose a fresh safe directory"):
                run_phase14c_supervised_smoke_dry_run_rehearsal(output_dir)

            with self.assertRaisesRegex(ValueError, "must not be inside the repository"):
                run_phase14c_supervised_smoke_dry_run_rehearsal(
                    Path(__file__).resolve().parents[1] / "phase14c-output"
                )

    def test_blocked_dry_run_rehearsal_artifacts_do_not_echo_unsafe_values(self) -> None:
        unsafe = "secret-token-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request()
        request["test_marker"] = unsafe
        request["rails"]["todoist"]["tasks"][0]["title"] = unsafe
        request["rails"]["gmail"]["emails"][0]["subject"] = unsafe
        request["rails"]["gmail"]["emails"][0]["to"] = [unsafe]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "phase14c-blocked-rehearsal"

            result = run_phase14c_supervised_smoke_dry_run_rehearsal(
                output_dir,
                request=request,
            )

            self.assertEqual(result.completion_report["status"], "blocked")
            self.assertFalse(result.completion_report["validation"]["accepted"])
            self.assertEqual(result.completion_report["fake_client_results"], {})
            for path in result.artifact_paths.values():
                with self.subTest(path=path):
                    self.assertNotIn(unsafe, Path(path).read_text(encoding="utf-8"))

    def test_live_run_requires_request_approval_and_config_names(self) -> None:
        request = build_default_phase14c_supervised_smoke_request(mode=LIVE_RUN_MODE)
        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertFalse(validation.accepted)
        self.assertIn("Live run requires live_run_requested=true.", validation.reasons)
        self.assertIn(
            "Live run requires a current approval_reference.", validation.reasons
        )
        self.assertIn(
            "Live run requires all config entry names to be present.",
            validation.reasons,
        )

    def test_gmail_self_send_readiness_uses_injected_identity_and_masks_values(
        self,
    ) -> None:
        client = _GmailIdentityClient("private.phase14c@example.test")

        report = build_phase14c_gmail_self_send_readiness_report(
            gmail_identity_client=client
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], "ready_for_self_send")
        self.assertEqual(
            report["controlled_recipient_source"],
            "authenticated_sender_identity",
        )
        self.assertEqual(report["masked_recipient"], "p***@example.test")
        self.assertFalse(report["raw_recipient_reported"])
        self.assertNotIn("private.phase14c@example.test", serialized)
        self.assertFalse(report["send_boundaries"]["cc_allowed"])
        self.assertFalse(report["send_boundaries"]["bulk_send_allowed"])

    def test_gmail_self_send_request_defaults_to_sender_as_controlled_recipient(
        self,
    ) -> None:
        request = build_phase14c_gmail_self_send_smoke_request(
            gmail_identity_client=_GmailIdentityClient("private.phase14c@example.test")
        )
        email = request["rails"]["gmail"]["emails"][0]

        self.assertEqual(request["controlled_test_recipients"], [email["to"][0]])
        self.assertEqual(email["to"], ["private.phase14c@example.test"])
        self.assertTrue(email["send"])
        self.assertFalse(email["create_draft"])
        self.assertTrue(validate_phase14c_supervised_smoke_request(request).accepted)

    def test_gmail_self_send_blocks_when_sender_and_configured_recipient_missing(
        self,
    ) -> None:
        report = build_phase14c_gmail_self_send_readiness_report()

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["reason"], "gmail_not_run_missing_sender_or_controlled_recipient"
        )
        with self.assertRaisesRegex(
            ValueError, "gmail_not_run_missing_sender_or_controlled_recipient"
        ):
            build_phase14c_gmail_self_send_smoke_request()

    def test_todoist_due_date_uses_next_monday_when_original_is_past(self) -> None:
        self.assertEqual(
            resolve_phase14c_todoist_due_date(
                original_due_date="2026-06-29",
                current_date="2026-06-30",
            ),
            "2026-07-06",
        )
        self.assertEqual(
            resolve_phase14c_todoist_due_date(
                original_due_date="2026-07-06",
                current_date="2026-06-30",
            ),
            "2026-07-06",
        )

    def test_openclaw_repo_local_harness_runs_without_runtime_or_external_mutation(
        self,
    ) -> None:
        result = run_phase14c_openclaw_local_sandbox_smoke()

        self.assertEqual(result["status"], "local_test_sandbox_smoke_completed")
        self.assertEqual(result["invocation_name"], "phase14c_smoke_test")
        self.assertEqual(result["mode"], "local_test_sandbox")
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["openclaw_runtime_called"])
        self.assertFalse(result["protected_paths_touched"])
        self.assertFalse(result["scheduler_activated"])
        self.assertFalse(result["production_db_active"])
        self.assertFalse(result["broad_runtime_handoff"])

    def test_live_run_requires_executor_approval_flag(self) -> None:
        request = build_default_phase14c_supervised_smoke_request(
            mode=LIVE_RUN_MODE,
            live_run_requested=True,
            approval_reference="Chris approved Phase 14-C supervised smoke test",
        )
        report = execute_phase14c_supervised_smoke_request(
            request,
            clients=_fake_clients(),
            available_config_names=REQUIRED_CONFIG_ENTRY_NAMES,
            live_run_approved=False,
        )

        self.assertEqual(report["status"], "blocked")
        self.assertIn(
            "Live smoke execution requires live_run_approved=true.",
            report["reasons"],
        )
        self.assertFalse(report["live_run_executed"])
        _assert_execution_validation_redacted(report)

    def test_live_run_requires_all_injected_clients_before_any_call(self) -> None:
        request = build_default_phase14c_supervised_smoke_request(
            mode=LIVE_RUN_MODE,
            live_run_requested=True,
            approval_reference="Chris approved Phase 14-C supervised smoke test",
        )
        todoist = _RecordingTodoistClient()
        report = execute_phase14c_supervised_smoke_request(
            request,
            clients=Phase14CSupervisedSmokeClients(todoist=todoist),
            available_config_names=REQUIRED_CONFIG_ENTRY_NAMES,
            live_run_approved=True,
        )

        self.assertEqual(report["status"], "blocked")
        self.assertIn("Missing injected client for google_calendar.", report["reasons"])
        self.assertIn("Missing injected client for gmail.", report["reasons"])
        self.assertIn("Missing injected client for openclaw.", report["reasons"])
        self.assertEqual(todoist.calls, [])
        _assert_execution_validation_redacted(report)

    def test_live_run_invokes_each_injected_client_once(self) -> None:
        request = build_default_phase14c_supervised_smoke_request(
            mode=LIVE_RUN_MODE,
            live_run_requested=True,
            approval_reference="Chris approved Phase 14-C supervised smoke test",
        )
        clients = _fake_clients()
        report = execute_phase14c_supervised_smoke_request(
            request,
            clients=clients,
            available_config_names=REQUIRED_CONFIG_ENTRY_NAMES,
            live_run_approved=True,
        )

        self.assertEqual(report["status"], "live_run_completed")
        self.assertTrue(report["live_run_executed"])
        self.assertEqual(len(clients.todoist.calls), 1)
        self.assertEqual(len(clients.google_calendar.calls), 1)
        self.assertEqual(len(clients.gmail.calls), 1)
        self.assertEqual(len(clients.openclaw.calls), 1)
        self.assertIn(PHASE14C_SUPERVISED_SMOKE_MARKER, clients.todoist.calls[0]["title"])
        self.assertIn(
            PHASE14C_SUPERVISED_SMOKE_MARKER,
            clients.google_calendar.calls[0]["summary"],
        )
        self.assertIn(PHASE14C_SUPERVISED_SMOKE_MARKER, clients.gmail.calls[0]["subject"])
        self.assertIn(
            PHASE14C_SUPERVISED_SMOKE_MARKER,
            clients.openclaw.calls[0]["label"],
        )
        _assert_execution_validation_redacted(report)

    def test_executor_blocked_guardrail_report_does_not_echo_unsafe_values(self) -> None:
        unsafe = "secret-token-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request()
        request["test_marker"] = unsafe
        request["rails"]["gmail"]["emails"][0]["to"] = [unsafe]

        report = execute_phase14c_supervised_smoke_request(request)
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["validation"]["accepted"])
        self.assertNotIn("normalized_request", report["validation"])
        self.assertIsNone(report["validation"]["normalized_request_summary"])
        self.assertNotIn(unsafe, serialized)

    def test_rejects_more_than_one_object_per_rail(self) -> None:
        cases = (
            (
                "todoist",
                lambda request: request["rails"]["todoist"]["tasks"].append(
                    dict(request["rails"]["todoist"]["tasks"][0])
                ),
                "Todoist task count must be at most one.",
            ),
            (
                "calendar",
                lambda request: request["rails"]["google_calendar"]["events"].append(
                    dict(request["rails"]["google_calendar"]["events"][0])
                ),
                "Calendar event count must be at most one.",
            ),
            (
                "gmail",
                lambda request: request["rails"]["gmail"]["emails"].append(
                    dict(request["rails"]["gmail"]["emails"][0])
                ),
                "Gmail email count must be at most one.",
            ),
            (
                "openclaw",
                lambda request: request["rails"]["openclaw"]["invocations"].append(
                    dict(request["rails"]["openclaw"]["invocations"][0])
                ),
                "OpenClaw invocation count must be at most one.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                request = build_default_phase14c_supervised_smoke_request()
                mutate(request)

                validation = validate_phase14c_supervised_smoke_request(request)

                self.assertFalse(validation.accepted)
                self.assertIn(expected_reason, validation.reasons)

    def test_rejects_missing_marker_on_every_rail(self) -> None:
        cases = (
            (
                "todoist",
                lambda request: request["rails"]["todoist"]["tasks"][0].update(
                    {"title": "Clean Kitchen Countertops and Stovetop"}
                ),
                "Todoist task title must include the required test marker.",
            ),
            (
                "calendar",
                lambda request: request["rails"]["google_calendar"]["events"][0].update(
                    {"summary": "Clean Kitchen Countertops and Stovetop"}
                ),
                "Calendar event summary must include the required test marker.",
            ),
            (
                "gmail",
                lambda request: request["rails"]["gmail"]["emails"][0].update(
                    {"subject": "Clean Kitchen Countertops and Stovetop"}
                ),
                "Gmail subject must include the required test marker.",
            ),
            (
                "openclaw",
                lambda request: request["rails"]["openclaw"]["invocations"][0].update(
                    {"label": "Clean Kitchen Countertops and Stovetop"}
                ),
                "OpenClaw invocation label must include the required test marker.",
            ),
        )
        for label, mutate, expected_reason in cases:
            with self.subTest(label=label):
                request = build_default_phase14c_supervised_smoke_request()
                mutate(request)

                validation = validate_phase14c_supervised_smoke_request(request)

                self.assertFalse(validation.accepted)
                self.assertIn(expected_reason, validation.reasons)

    def test_rejects_calendar_attendees_except_required_self_and_recurrence(self) -> None:
        request = build_default_phase14c_supervised_smoke_request()
        event = request["rails"]["google_calendar"]["events"][0]
        event["attendees"] = ["external@example.com"]
        event["self_attendee_required_by_api"] = True
        event["recurrence"] = ["RRULE:FREQ=WEEKLY"]

        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertFalse(validation.accepted)
        self.assertIn("Calendar event recurrence is not allowed.", validation.reasons)
        self.assertIn(
            "Calendar attendees must contain only the self test identity.",
            validation.reasons,
        )

        allowed_self = build_default_phase14c_supervised_smoke_request()
        self_identity = allowed_self["self_test_identity"]
        allowed_self["rails"]["google_calendar"]["events"][0].update(
            {
                "attendees": [self_identity],
                "self_attendee_required_by_api": True,
            }
        )
        self.assertTrue(
            validate_phase14c_supervised_smoke_request(allowed_self).accepted
        )

    def test_rejects_gmail_uncontrolled_recipients_attachments_and_thread_reuse(self) -> None:
        request = build_default_phase14c_supervised_smoke_request()
        email = request["rails"]["gmail"]["emails"][0]
        email["to"] = ["uncontrolled@example.com"]
        email["cc"] = ["self.phase14c.test@example.test"]
        email["attachments"] = [{"name": "secret.txt"}]
        email["thread_id"] = "real-thread-id"
        email["reply_to_existing_thread"] = True
        email["forward_existing_thread"] = True

        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertFalse(validation.accepted)
        self.assertIn(
            "Gmail recipients must be controlled test recipients only.",
            validation.reasons,
        )
        self.assertIn("Gmail attachments are not allowed.", validation.reasons)
        self.assertIn("Gmail must not attach to an existing thread.", validation.reasons)
        self.assertIn(
            "Gmail replies to existing threads are not allowed.", validation.reasons
        )
        self.assertIn(
            "Gmail forwarding existing threads is not allowed.", validation.reasons
        )

    def test_rejects_blocked_boundary_fields(self) -> None:
        cases = (
            "scheduler_background_loop",
            "production_db",
            "dynamic_cleaning",
            "bulk_writes",
            "protected_path_access",
            "broad_openclaw_runtime_handoff",
        )
        for field in cases:
            with self.subTest(field=field):
                request = build_default_phase14c_supervised_smoke_request()
                request["boundaries"][field] = True

                validation = validate_phase14c_supervised_smoke_request(request)

                self.assertFalse(validation.accepted)
                self.assertIn(
                    f"Smoke boundary {field} must remain false.",
                    validation.reasons,
                )

    def test_rejects_openclaw_scope_mode_broad_handoff_and_protected_path(self) -> None:
        request = build_default_phase14c_supervised_smoke_request()
        invocation = request["rails"]["openclaw"]["invocations"][0]
        invocation["mode"] = "production"
        invocation["scope"] = "operate_personal_os"
        invocation["name"] = "operate_personal_os"
        invocation["broad_runtime_handoff"] = True
        invocation["production_operation"] = True
        invocation["scheduler_background"] = True
        invocation["external_mutation"] = True
        invocation["allowed_paths"] = ["/Users/coldstake/.openclaw/runtime"]

        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertFalse(validation.accepted)
        self.assertIn(
            "OpenClaw invocation name must be phase14c_smoke_test.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw invocation must use local/test/sandbox mode.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw scope must stay to one supervised smoke invocation.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw broad runtime handoff is not allowed.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw production operation is not allowed.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw scheduler/background behavior is not allowed.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw external mutation is not allowed.",
            validation.reasons,
        )
        self.assertIn(
            "OpenClaw invocation must not include protected paths.",
            validation.reasons,
        )

    def test_rejects_todoist_subtasks_labels_comments_and_automatic_mutation(
        self,
    ) -> None:
        request = build_default_phase14c_supervised_smoke_request()
        task = request["rails"]["todoist"]["tasks"][0]
        task["subtasks"] = [{"title": "Subtask"}]
        task["labels"] = ["phase14c"]
        task["comments"] = [{"body": "comment"}]
        task["automatic_edits"] = True
        task["automatic_deletion"] = True
        task["skip_push_bump"] = True
        task["automatic_rescheduling"] = True

        validation = validate_phase14c_supervised_smoke_request(request)

        self.assertFalse(validation.accepted)
        self.assertIn("Todoist subtasks are not allowed.", validation.reasons)
        self.assertIn("Todoist labels are not allowed.", validation.reasons)
        self.assertIn("Todoist comments are not allowed.", validation.reasons)
        self.assertIn(
            "Todoist automatic_edits must remain false.", validation.reasons
        )
        self.assertIn(
            "Todoist automatic_deletion must remain false.", validation.reasons
        )
        self.assertIn("Todoist skip_push_bump must remain false.", validation.reasons)
        self.assertIn(
            "Todoist automatic_rescheduling must remain false.", validation.reasons
        )

    def test_blocked_validation_does_not_echo_unsafe_values(self) -> None:
        unsafe = "secret-token-value-that-must-not-echo"
        request = build_default_phase14c_supervised_smoke_request()
        request["test_marker"] = unsafe
        request["rails"]["gmail"]["emails"][0]["to"] = [unsafe]
        validation = validate_phase14c_supervised_smoke_request(
            request,
            available_config_names={
                "PERSONALOS_PHASE14C_TODOIST_TOKEN": unsafe,
            },
        )
        serialized = json.dumps(validation.to_dict(), sort_keys=True)

        self.assertFalse(validation.accepted)
        self.assertNotIn(unsafe, serialized)
        self.assertIsNone(validation.normalized_request)


class _RecordingTodoistClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_task(self, task):
        self.calls.append(copy.deepcopy(dict(task)))
        return {"status": "created", "external_task_id": "todoist-test-id"}


class _RecordingCalendarClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_event(self, event):
        self.calls.append(copy.deepcopy(dict(event)))
        return {"status": "created", "external_event_id": "calendar-test-id"}


class _RecordingGmailClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_or_send_email(self, email):
        self.calls.append(copy.deepcopy(dict(email)))
        return {"status": "draft_created", "external_message_id": "gmail-test-id"}


class _RecordingOpenClawClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def invoke_smoke(self, invocation):
        self.calls.append(copy.deepcopy(dict(invocation)))
        return {"status": "completed", "invocation_id": "openclaw-test-id"}


class _GmailIdentityClient:
    def __init__(self, email: str) -> None:
        self.email = email

    def get_authenticated_sender(self):
        return {"email": self.email}


def _fake_clients() -> Phase14CSupervisedSmokeClients:
    return Phase14CSupervisedSmokeClients(
        todoist=_RecordingTodoistClient(),
        google_calendar=_RecordingCalendarClient(),
        gmail=_RecordingGmailClient(),
        openclaw=_RecordingOpenClawClient(),
    )


def _assert_execution_validation_redacted(report: dict[str, object]) -> None:
    serialized = json.dumps(report, sort_keys=True)
    validation = report["validation"]
    assert isinstance(validation, dict)
    normalized_summary = validation.get("normalized_request_summary")
    assert isinstance(normalized_summary, dict)

    if "normalized_request" in validation:
        raise AssertionError("execution report must not include raw normalized_request")
    if "self.phase14c.test@example.test" in serialized:
        raise AssertionError("execution report must not include raw test recipient")
    if "rails" not in normalized_summary:
        raise AssertionError("execution report should retain redacted rail summaries")
    if not all(normalized_summary["boundaries_remain_false"].values()):
        raise AssertionError("execution report should prove blocked boundaries stayed false")


def _load_json(path: str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()

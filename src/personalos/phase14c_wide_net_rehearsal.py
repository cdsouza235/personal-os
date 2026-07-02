"""Repo-local wide-net rehearsal plan for Phase 14-C."""

from __future__ import annotations


PHASE14C_WIDE_NET_REHEARSAL_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_rehearsal.v1"
)
PHASE14C_WIDE_NET_REHEARSAL_STATUS = "phase14c_wide_net_rehearsal_plan_ready"
PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE = (
    "phase14c-2026-07-01-wide-net-live-test"
)
PHASE14C_WIDE_NET_REHEARSAL_MARKER = (
    "[Phase 14-C Wide Test] Evening Reset Coordination"
)
PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE = (
    "/opt/homebrew/etc/ca-certificates/cert.pem"
)


def build_phase14c_wide_net_rehearsal_plan() -> dict[str, object]:
    """Build a no-live plan for the next wider Phase 14-C test packet."""

    return {
        "schema_version": PHASE14C_WIDE_NET_REHEARSAL_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_REHEARSAL_STATUS,
        "plan_name": "Phase 14-C wide-net rehearsal",
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "executable_gate_available": True,
        "calendar_bridge_scaffold_available": True,
        "calendar_app_bridge_payload_command_available": True,
        "calendar_client_bridge_available": False,
        "calendar_duplicate_precheck_enforced_by_runner": True,
        "calendar_precheck_unrecognized_response_fails_closed": True,
        "foundation": _confirmed_foundation(),
        "objective": _objective(),
        "proposed_live_sequence": _proposed_live_sequence(),
        "live_call_budgets": _live_call_budgets(),
        "rails_excluded": _rails_excluded(),
        "preconditions": _preconditions(),
        "reporting_policy": _reporting_policy(),
        "stop_conditions": _stop_conditions(),
        "suggested_approval_text": _suggested_approval_text(),
        "safety_assertions": _safety_assertions(),
    }


def _confirmed_foundation() -> dict[str, object]:
    return {
        "gmail": {
            "status": "confirmed",
            "evidence": "gmail_self_send_smoke_passed",
            "bounded_live_writes": 1,
            "masked_sender_recipient_only": True,
        },
        "todoist": {
            "status": "confirmed",
            "evidence": "todoist_inbox_default_task_smoke_passed",
            "bounded_live_writes": 1,
            "manual_first_attempt_outcome": "not_found",
            "ca_bundle_retry_used": True,
        },
        "openrouter": {
            "status": "confirmed_with_budget_caveat",
            "evidence": "openclaw_model_smoke_passed",
            "latest_connected_rehearsal_status": (
                "phase14c_connected_rehearsal_model_validation_failed"
            ),
            "diagnostic_only_for_wide_net": True,
        },
        "calendar": {
            "status": "confirmed_existing_smoke_only",
            "existing_bounded_event_count": 1,
            "duplicate_existing_calendar_smoke_authorized": False,
            "wide_net_duplicate_precheck_enforced_by_runner": True,
            "wide_net_calendar_bridge_scaffold_available": True,
            "wide_net_calendar_app_bridge_payloads_available": True,
            "unrecognized_precheck_response_fails_closed": True,
        },
        "openclaw_runtime": {
            "status": "repo_local_harness_passed_protected_runtime_not_invoked",
            "protected_runtime_invocation_authorized": False,
        },
    }


def _objective() -> dict[str, object]:
    return {
        "kind": "wider_bounded_multi_rail_rehearsal_plan",
        "summary": (
            "Exercise the confirmed low-blast-radius live rails as separate bounded "
            "writes under one marker, while keeping the model probe diagnostic-only "
            "so a provider validation failure does not block Todoist, Gmail, or "
            "Calendar learning."
        ),
        "why_this_is_larger_than_connected_rehearsal": (
            "The next packet widens from model-to-task-to-email to four supervised "
            "rails: OpenRouter diagnostics, Todoist, Gmail, and one self-only "
            "Calendar event."
        ),
        "model_output_drives_external_writes": False,
        "not_dynamic_cleaning": True,
        "not_broad_live_activation": True,
    }


def _proposed_live_sequence() -> list[dict[str, object]]:
    return [
        {
            "step": 1,
            "rail": "google_calendar",
            "operation": "read_duplicate_marker_precheck_before_external_mutation",
            "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "calendar_scope": "primary_or_authenticated_self_calendar_only",
            "external_mutation": False,
            "duplicate_marker_precheck_required": True,
            "requires_bridge_normalized_matching_event_count": True,
            "stop_before_model_todoist_gmail_or_calendar_create_on_match": True,
            "unrecognized_precheck_response_fails_closed": True,
            "event_details_logged": False,
            "attendee_addresses_logged": False,
        },
        {
            "step": 2,
            "rail": "openrouter",
            "operation": "run_one_diagnostic_model_probe",
            "primary_model_alias": "nemotron_super",
            "fallback_model_alias": "glm_5_2",
            "fallback_allowed_only_if_primary_fails_validation": True,
            "diagnostic_only": True,
            "external_write_dependency": False,
            "prompt_policy": {
                "fixed_non_secret_prompt": True,
                "protected_paths_in_prompt": False,
                "credential_values_in_prompt": False,
                "full_prompt_logged": False,
            },
            "output_policy": {
                "raw_provider_response_logged": False,
                "generated_text_used_for_task_or_email": False,
                "safe_metadata_only": True,
            },
        },
        {
            "step": 3,
            "rail": "todoist",
            "operation": "create_one_inbox_default_marker_task",
            "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "due_date_policy": "next_upcoming_monday_at_runtime",
            "project": "Inbox/default",
            "recurrence": None,
            "subtasks": 0,
            "labels": [],
            "comments": 0,
            "automatic_edits_deletes_or_reschedule": False,
        },
        {
            "step": 4,
            "rail": "gmail",
            "operation": "send_one_controlled_self_email_with_marker",
            "subject": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "recipient_scope": "configured_controlled_recipient_or_self_only",
            "cc": 0,
            "bcc": 0,
            "attachments": 0,
            "reply_or_forward": False,
        },
        {
            "step": 5,
            "rail": "google_calendar",
            "operation": "create_one_self_only_marker_event_after_duplicate_precheck",
            "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "duration_minutes": 15,
            "calendar_scope": "primary_or_authenticated_self_calendar_only",
            "attendees": 0,
            "recurrence": None,
            "conference_link": False,
            "attachments": 0,
            "duplicate_marker_precheck_required": True,
        },
    ]


def _live_call_budgets() -> dict[str, object]:
    return {
        "openrouter_primary_calls": 1,
        "openrouter_fallback_calls_max": 1,
        "openrouter_fallback_condition": "primary_validation_failed",
        "todoist_task_creates": 1,
        "gmail_emails_sent": 1,
        "calendar_event_creates": 1,
        "calendar_duplicate_precheck_reads": "minimum_needed_before_create",
        "protected_openclaw_runtime_invocations": 0,
        "openclaw_local_harness_invocations": 0,
        "production_db_writes": 0,
        "scheduler_or_background_jobs": 0,
    }


def _rails_excluded() -> dict[str, object]:
    return {
        "protected_openclaw_runtime": {
            "excluded": True,
            "reason": "OpenClaw runtime handoff remains a separate protected gate.",
        },
        "production_db": {
            "excluded": True,
            "reason": "Wide-net rehearsal is not production activation.",
        },
        "scheduler_background": {
            "excluded": True,
            "reason": "Foreground supervised run only.",
        },
        "dynamic_cleaning": {
            "excluded": True,
            "reason": "The marker is test-only and does not trigger cleaning behavior.",
        },
    }


def _preconditions() -> dict[str, object]:
    return {
        "requires_new_explicit_live_approval": True,
        "requires_claude_code_audit_before_live_run": True,
        "requires_ssl_cert_file": True,
        "ssl_cert_file": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "requires_google_calendar_connector_duplicate_precheck": True,
        "requires_bridge_normalized_precheck_response_contract": True,
        "calendar_bridge_scaffold_available": True,
        "calendar_app_bridge_payload_command_available": True,
        "calendar_cli_bridge_available": False,
        "requires_configured_rails": [
            "PERSONALOS_OPENCLAW_MODEL_API_KEY",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN",
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT",
            "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL",
        ],
        "config_values_reported": False,
        "present_config_names_reported": False,
        "no_env_read_by_this_plan": True,
        "no_calendar_connector_call_by_this_plan": True,
    }


def _reporting_policy() -> dict[str, object]:
    return {
        "allowed_live_report_fields": [
            "status",
            "approval_reference_present",
            "call_counts",
            "todoist_task_created_boolean",
            "gmail_email_sent_boolean",
            "calendar_event_created_boolean",
            "calendar_event_id_if_connector_returns_safe_id",
            "model_metadata_safe_fields",
            "masked_sender",
            "masked_recipient",
        ],
        "forbidden_live_report_fields": [
            "credential_values",
            "api_keys",
            "app_passwords",
            "raw_provider_response",
            "full_prompt",
            "generated_model_text",
            "configured_model_ids",
            "unmasked_email_addresses",
            "calendar_attendee_addresses",
            "environment_dump",
        ],
    }


def _stop_conditions() -> list[str]:
    return [
        "Any rail would perform more than its stated call/write budget.",
        "Todoist task already exists with the wide-net marker.",
        "Calendar event already exists with the wide-net marker.",
        "Gmail recipient is not the configured controlled recipient or self.",
        "Calendar would include attendees, recurrence, conference link, or attachments.",
        "OpenRouter prompt would include secrets, protected paths, or personal data.",
        "OpenRouter would need more than the one primary and one fallback diagnostic call.",
        "OpenRouter would enter a spend/config retry loop.",
        "Protected OpenClaw runtime invocation appears.",
        "Scheduler/background, production DB, dynamic cleaning, or protected paths appear.",
        "Credential values would be printed, logged, copied, committed, or summarized.",
    ]


def _suggested_approval_text() -> str:
    return (
        "Approved: run exactly one Phase 14-C wide-net live test using approval "
        f"reference {PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE} with "
        f"SSL_CERT_FILE={PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE}. Allowed "
        "live actions: one OpenRouter diagnostic model call with one fallback "
        "only if primary validation fails, one Todoist Inbox/default task, one "
        "Gmail controlled self-send, and one self-only Google Calendar event "
        f"using marker {PHASE14C_WIDE_NET_REHEARSAL_MARKER}. Do not run "
        "protected OpenClaw runtime, scheduler/background, production DB, "
        "protected paths, dynamic cleaning, or broad runtime handoff."
    )


def _safety_assertions() -> dict[str, bool]:
    return {
        "live_run_executed": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "environment_dumped": False,
        "live_clients_initialized": False,
        "calendar_connector_called": False,
        "external_mutation": False,
        "model_provider_called": False,
        "todoist_task_created": False,
        "gmail_sent_or_drafted": False,
        "calendar_event_created": False,
        "protected_openclaw_runtime_called": False,
        "scheduler_or_background_activated": False,
        "production_db_active": False,
        "protected_paths_touched": False,
        "dynamic_cleaning_triggered": False,
        "broad_live_activation": False,
    }

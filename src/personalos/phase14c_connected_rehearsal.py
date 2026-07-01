"""Repo-local connected rehearsal plan for Phase 14-C."""

from __future__ import annotations


PHASE14C_CONNECTED_REHEARSAL_SCHEMA_VERSION = (
    "personal_os_phase14c_connected_rehearsal.v1"
)
PHASE14C_CONNECTED_REHEARSAL_STATUS = "phase14c_connected_rehearsal_plan_ready"
PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE = (
    "phase14c-2026-07-01-connected-rehearsal"
)
PHASE14C_CONNECTED_REHEARSAL_MARKER = (
    "[Phase 14-C Connected Test] Kitchen Reset Briefing"
)
PHASE14C_CONNECTED_REHEARSAL_DUE_DATE = "2026-07-06"
PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE = (
    "/opt/homebrew/etc/ca-certificates/cert.pem"
)


def build_phase14c_connected_rehearsal_plan() -> dict[str, object]:
    """Build a no-live plan for the next larger connected Phase 14-C test."""

    return {
        "schema_version": PHASE14C_CONNECTED_REHEARSAL_SCHEMA_VERSION,
        "status": PHASE14C_CONNECTED_REHEARSAL_STATUS,
        "plan_name": "Phase 14-C connected rehearsal",
        "marker": PHASE14C_CONNECTED_REHEARSAL_MARKER,
        "approval_reference_to_request": (
            PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE
        ),
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
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
            "status": "confirmed",
            "evidence": "openclaw_model_smoke_passed",
            "primary_model_alias": "nemotron_super",
            "fallback_calls_on_confirmed_retry": 0,
            "ca_bundle_retry_used": True,
        },
        "calendar": {
            "status": "confirmed_existing_smoke_only",
            "duplicate_creation_authorized": False,
        },
        "openclaw_runtime": {
            "status": "not_invoked",
            "protected_runtime_invocation_authorized": False,
        },
    }


def _objective() -> dict[str, object]:
    return {
        "kind": "connected_model_to_task_to_email_rehearsal",
        "summary": (
            "Use a bounded OpenRouter model response to produce a short test "
            "brief, then create one Todoist Inbox/default task and send one "
            "controlled Gmail self-email containing the same marked brief."
        ),
        "why_this_is_larger_than_connectivity": (
            "The rails are connected through one supervised workflow artifact "
            "instead of isolated hello-world checks."
        ),
        "not_dynamic_cleaning": True,
        "not_broad_live_activation": True,
    }


def _proposed_live_sequence() -> list[dict[str, object]]:
    return [
        {
            "step": 1,
            "rail": "openrouter",
            "operation": "generate_one_short_non_secret_test_brief",
            "primary_model_alias": "nemotron_super",
            "fallback_model_alias": "glm_5_2",
            "fallback_allowed_only_if_primary_fails_validation": True,
            "prompt_policy": {
                "fixed_non_secret_prompt": True,
                "protected_paths_in_prompt": False,
                "credential_values_in_prompt": False,
                "full_prompt_logged": False,
            },
            "output_policy": {
                "max_brief_items": 3,
                "raw_provider_response_logged": False,
                "safe_metadata_only": True,
            },
        },
        {
            "step": 2,
            "rail": "todoist",
            "operation": "create_one_inbox_default_task_from_marked_brief",
            "title": PHASE14C_CONNECTED_REHEARSAL_MARKER,
            "due_date": PHASE14C_CONNECTED_REHEARSAL_DUE_DATE,
            "project": "Inbox/default",
            "recurrence": None,
            "subtasks": 0,
            "labels": [],
            "comments": 0,
            "automatic_edits_deletes_or_reschedule": False,
        },
        {
            "step": 3,
            "rail": "gmail",
            "operation": "send_one_controlled_self_email_from_marked_brief",
            "subject": PHASE14C_CONNECTED_REHEARSAL_MARKER,
            "recipient_scope": "configured_controlled_recipient_or_self_only",
            "cc": 0,
            "bcc": 0,
            "attachments": 0,
            "reply_or_forward": False,
        },
    ]


def _live_call_budgets() -> dict[str, object]:
    return {
        "openrouter_primary_calls": 1,
        "openrouter_fallback_calls_max": 1,
        "openrouter_fallback_condition": "primary_validation_failed",
        "todoist_task_creates": 1,
        "gmail_emails_sent": 1,
        "calendar_event_creates": 0,
        "protected_openclaw_runtime_invocations": 0,
        "production_db_writes": 0,
        "scheduler_or_background_jobs": 0,
    }


def _rails_excluded() -> dict[str, object]:
    return {
        "google_calendar": {
            "excluded": True,
            "reason": "Calendar already has one bounded smoke event; no duplicate event.",
        },
        "protected_openclaw_runtime": {
            "excluded": True,
            "reason": "OpenClaw runtime handoff remains a separate protected gate.",
        },
        "production_db": {
            "excluded": True,
            "reason": "Connected rehearsal is not production activation.",
        },
        "scheduler_background": {
            "excluded": True,
            "reason": "Foreground supervised run only.",
        },
    }


def _preconditions() -> dict[str, object]:
    return {
        "requires_new_explicit_live_approval": True,
        "requires_claude_code_audit_before_live_run": True,
        "requires_ssl_cert_file": True,
        "ssl_cert_file": PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE,
        "requires_configured_rails": [
            "PERSONALOS_OPENCLAW_MODEL_API_KEY",
            "PERSONALOS_PHASE14C_TODOIST_TOKEN",
            "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS",
            "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD",
            "PHASE14C_GMAIL_CONTROLLED_RECIPIENT",
        ],
        "config_values_reported": False,
        "present_config_names_reported": False,
        "no_env_read_by_this_plan": True,
    }


def _reporting_policy() -> dict[str, object]:
    return {
        "allowed_live_report_fields": [
            "status",
            "approval_reference_present",
            "call_counts",
            "todoist_task_created_boolean",
            "gmail_email_sent_boolean",
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
            "configured_model_ids",
            "unmasked_email_addresses",
            "environment_dump",
        ],
    }


def _stop_conditions() -> list[str]:
    return [
        "Any rail would perform more than its stated call/write budget.",
        "Todoist task already exists with the connected rehearsal marker.",
        "Gmail recipient is not the configured controlled recipient or self.",
        "OpenRouter prompt would include secrets, protected paths, or personal data.",
        "Calendar creation appears.",
        "Protected OpenClaw runtime invocation appears.",
        "Scheduler/background, production DB, dynamic cleaning, or protected paths appear.",
        "Credential values would be printed, logged, copied, committed, or summarized.",
    ]


def _suggested_approval_text() -> str:
    return (
        "Approved: run exactly one Phase 14-C connected rehearsal using "
        f"approval reference {PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE} "
        f"with SSL_CERT_FILE={PHASE14C_CONNECTED_REHEARSAL_SSL_CERT_FILE}. "
        "Allowed live actions: one OpenRouter model call with one fallback only if "
        "primary validation fails, one Todoist Inbox/default task, and one Gmail "
        "controlled self-send. Do not run Calendar or protected OpenClaw runtime."
    )


def _safety_assertions() -> dict[str, bool]:
    return {
        "live_run_executed": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "environment_dumped": False,
        "live_clients_initialized": False,
        "external_mutation": False,
        "model_provider_called": False,
        "todoist_task_created": False,
        "gmail_sent_or_drafted": False,
        "calendar_event_created": False,
        "protected_openclaw_runtime_called": False,
        "scheduler_activated": False,
        "production_db_active": False,
        "protected_paths_touched": False,
        "broad_live_activation": False,
    }

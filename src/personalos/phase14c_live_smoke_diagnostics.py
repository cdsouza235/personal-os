"""Repo-local follow-up diagnostics for Phase 14-C live-smoke results."""

from __future__ import annotations

from personalos.openclaw_model_strategy import SAFE_METADATA_FIELDS
from personalos.phase14c_todoist_live_smoke import PHASE14C_TODOIST_TASK_TITLE


PHASE14C_LIVE_SMOKE_DIAGNOSTICS_SCHEMA_VERSION = (
    "personal_os_phase14c_live_smoke_diagnostics.v1"
)
PHASE14C_LIVE_SMOKE_APPROVAL_REFERENCE = (
    "phase14c-2026-06-30-connectivity-live-smoke"
)
PHASE14C_TODOIST_SMOKE_DUE_DATE = "2026-07-06"


def build_phase14c_live_smoke_diagnostics_report() -> dict[str, object]:
    """Build a no-live follow-up report for unresolved Phase 14-C smoke rails."""

    return {
        "schema_version": PHASE14C_LIVE_SMOKE_DIAGNOSTICS_SCHEMA_VERSION,
        "status": "phase14c_live_smoke_diagnostics_ready",
        "approval_reference_label": PHASE14C_LIVE_SMOKE_APPROVAL_REFERENCE,
        "todoist_manual_check": _todoist_manual_check(),
        "openrouter_next_probe_diagnostics": _openrouter_next_probe_diagnostics(),
        "safety_assertions": {
            "credential_values_read": False,
            "credential_values_logged": False,
            "environment_dumped": False,
            "live_clients_initialized": False,
            "external_mutation": False,
            "gmail_sent_or_drafted": False,
            "todoist_task_created": False,
            "calendar_event_created": False,
            "model_provider_called": False,
            "openclaw_runtime_called": False,
            "protected_paths_touched": False,
            "scheduler_activated": False,
            "production_db_active": False,
            "broad_openclaw_runtime_handoff": False,
        },
    }


def _todoist_manual_check() -> dict[str, object]:
    return {
        "status": "todoist_manual_outcome_check_required",
        "rail": "todoist",
        "prior_status": "todoist_inbox_default_task_smoke_failed",
        "prior_mutation_state": "unconfirmed_after_task_create_attempt",
        "target": "inbox_default",
        "title": PHASE14C_TODOIST_TASK_TITLE,
        "due_date": PHASE14C_TODOIST_SMOKE_DUE_DATE,
        "manual_check_required": True,
        "matching_task_id_required_in_chat": False,
        "do_not_rerun_create_without_manual_check": True,
        "manual_check_steps": [
            "Open Todoist Inbox/default.",
            f"Search for the exact title: {PHASE14C_TODOIST_TASK_TITLE}",
            f"Confirm whether the matching task has due date {PHASE14C_TODOIST_SMOKE_DUE_DATE}.",
            "Report only found_matching_task, not_found, or ambiguous_multiple_matches.",
        ],
        "accepted_manual_outcomes": [
            "found_matching_task",
            "not_found",
            "ambiguous_multiple_matches",
        ],
        "next_action_by_outcome": {
            "found_matching_task": "Record Todoist smoke as confirmed without rerunning create.",
            "not_found": (
                "Treat the prior create attempt as not externally visible; any retry "
                "still requires new explicit duplicate-risk approval."
            ),
            "ambiguous_multiple_matches": (
                "Stop and resolve manually before any Todoist retry or broader test."
            ),
        },
    }


def _openrouter_next_probe_diagnostics() -> dict[str, object]:
    safe_fields = list(SAFE_METADATA_FIELDS)
    return {
        "status": "openrouter_next_probe_diagnostics_ready",
        "prior_status": "openclaw_model_smoke_validation_failed",
        "prior_primary_calls": 1,
        "prior_fallback_calls": 1,
        "prior_failure_category": "transport_or_parse_error",
        "next_probe_requires_new_explicit_approval": True,
        "safe_metadata_fields": safe_fields,
        "new_safe_failure_fields": [
            field for field in ("error_kind", "http_status") if field in safe_fields
        ],
        "raw_provider_response_logged": False,
        "full_prompt_logged": False,
        "credential_values_logged": False,
        "configured_model_ids_logged": False,
        "diagnostic_value": (
            "The next approved OpenRouter smoke can distinguish HTTP errors, "
            "transport/TLS/DNS classes, and JSON parse failures without exposing "
            "credentials, prompts, configured model IDs, or raw provider bodies."
        ),
    }

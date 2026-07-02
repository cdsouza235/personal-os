"""Repo-local handoff and evidence checks for the Phase 14-C wide-net run."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from personalos.phase14c_safety_utils import (
    PHASE14C_REDACTION_MAX_DEPTH,
    PHASE14C_REDACTION_MAX_NODES,
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_calendar_app_bridge import (
    build_phase14c_wide_net_calendar_app_bridge_report,
)
from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_CALENDAR_FAILED,
    WIDE_NET_CALENDAR_PRECHECK_FAILED,
    WIDE_NET_GMAIL_FAILED,
    WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
    WIDE_NET_TODOIST_FAILED,
)


PHASE14C_WIDE_NET_EXECUTION_HANDOFF_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_execution_handoff.v1"
)
PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS = (
    "phase14c_wide_net_execution_handoff_ready"
)
PHASE14C_WIDE_NET_EVIDENCE_VALIDATION_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_evidence_validation.v1"
)
PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_evidence_template.v1"
)
PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_STATUS = (
    "phase14c_wide_net_evidence_template_ready"
)
PHASE14C_WIDE_NET_EVIDENCE_VALID = "phase14c_wide_net_evidence_valid"
PHASE14C_WIDE_NET_EVIDENCE_BLOCKED = "phase14c_wide_net_evidence_blocked"
PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES = 262_144

_COMPLETE_PASS_STATUSES = {
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
}
_KNOWN_RUN_STATUSES = {
    *_COMPLETE_PASS_STATUSES,
    WIDE_NET_TODOIST_FAILED,
    WIDE_NET_GMAIL_FAILED,
    WIDE_NET_CALENDAR_FAILED,
    WIDE_NET_CALENDAR_PRECHECK_FAILED,
    WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
}
_MAX_CALL_COUNTS = {
    "openrouter_primary_calls": 1,
    "openrouter_fallback_calls": 1,
    "todoist_task_create_calls": 1,
    "gmail_email_send_calls": 1,
    "calendar_duplicate_precheck_calls": 1,
    "calendar_event_create_calls": 1,
    "protected_openclaw_runtime_invocation_calls": 0,
}
_MODEL_FALSE_FLAGS = (
    "model_output_drives_external_writes",
    "prompt_logged",
    "raw_provider_response_logged",
    "generated_model_text_logged",
    "configured_model_ids_logged",
    "credential_values_logged",
)
_SAFETY_FALSE_FLAGS = (
    "credential_values_logged",
    "credential_values_committed",
    "environment_dumped",
    "protected_openclaw_runtime_called",
    "scheduler_or_background_activated",
    "production_db_active",
    "protected_paths_touched",
    "dynamic_cleaning_triggered",
    "broad_live_activation",
)


def build_phase14c_wide_net_execution_handoff_report() -> dict[str, Any]:
    """Build a no-live handoff report for the future wide-net live gate."""

    bridge = build_phase14c_wide_net_calendar_app_bridge_report()
    return {
        "schema_version": PHASE14C_WIDE_NET_EXECUTION_HANDOFF_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "calendar_app_connector_called": False,
        "credential_values_read": False,
        "external_mutation": False,
        "execution_command_template": (
            "SSL_CERT_FILE="
            f"{PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE} "
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-rehearsal --execute-live --approval-reference "
            f"{PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE} --json"
        ),
        "preflight_commands": (
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-calendar-bridge-payloads --json",
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-calendar-transcript-template --json",
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-calendar-transcript-validate --input-file "
            "<sanitized-calendar-transcript.json> --json",
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-execution-handoff --json",
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-evidence-template --json",
        ),
        "post_run_evidence_validator": {
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-evidence-validate --input-file "
                "<sanitized-wide-net-report.json> --json"
            ),
            "expects_sanitized_report_only": True,
            "raw_evidence_echoed": False,
            "credential_values_allowed": False,
            "unmasked_emails_allowed": False,
            "max_input_file_size_bytes": PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
            "redaction_scan_max_depth": PHASE14C_REDACTION_MAX_DEPTH,
            "redaction_scan_max_nodes": PHASE14C_REDACTION_MAX_NODES,
        },
        "calendar_connector_handoff": {
            "connector_type": "Google Calendar app connector",
            "repo_cli_constructs_connector": False,
            "repo_cli_calls_connector": False,
            "bridge_contract_required": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
            "operator_must_normalize_search_result": True,
            "duplicate_precheck_args": bridge["duplicate_precheck"][
                "google_calendar_search_events_args"
            ],
            "calendar_create_args": bridge["calendar_create"][
                "google_calendar_create_event_args"
            ],
            "create_allowed_only_after_matching_event_count_zero": True,
            "sanitized_transcript_validator_command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-transcript-validate --input-file "
                "<sanitized-calendar-transcript.json> --json"
            ),
        },
        "sequence": (
            "calendar_duplicate_precheck",
            "openrouter_diagnostic",
            "todoist_inbox_default_task",
            "gmail_controlled_self_send",
            "calendar_self_only_event_create",
        ),
        "call_budgets": dict(_MAX_CALL_COUNTS),
        "expected_complete_statuses": tuple(sorted(_COMPLETE_PASS_STATUSES)),
        "failure_statuses_that_require_manual_review": (
            WIDE_NET_TODOIST_FAILED,
            WIDE_NET_GMAIL_FAILED,
            WIDE_NET_CALENDAR_FAILED,
            WIDE_NET_CALENDAR_PRECHECK_FAILED,
            WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
        ),
        "safety_assertions": {
            "credential_values_read": False,
            "credential_values_logged": False,
            "environment_dumped": False,
            "calendar_app_connector_called": False,
            "external_mutation": False,
            "model_provider_called": False,
            "todoist_task_created": False,
            "gmail_email_sent": False,
            "calendar_event_created": False,
            "protected_openclaw_runtime_called": False,
            "scheduler_or_background_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "dynamic_cleaning_triggered": False,
            "broad_live_activation": False,
        },
    }


def build_phase14c_wide_net_evidence_template_report() -> dict[str, Any]:
    """Build a no-live fillable evidence template for the future wide-net run."""

    return {
        "schema_version": PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_EVIDENCE_TEMPLATE_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "calendar_app_connector_called": False,
        "credential_values_read": False,
        "external_mutation": False,
        "template_payload_is_not_evidence": True,
        "template_payload_expected_to_fail_validator_until_filled": True,
        "accepted_complete_statuses": tuple(sorted(_COMPLETE_PASS_STATUSES)),
        "call_budgets": dict(_MAX_CALL_COUNTS),
        "calendar_transcript_validator_command": (
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-calendar-transcript-validate --input-file "
            "<sanitized-calendar-transcript.json> --json"
        ),
        "post_run_evidence_validator_command": (
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-evidence-validate --input-file "
            "<sanitized-wide-net-report.json> --json"
        ),
        "fillable_evidence_shape": _fillable_wide_net_evidence_shape(),
        "required_false_model_flags": _MODEL_FALSE_FLAGS,
        "required_false_safety_flags": _SAFETY_FALSE_FLAGS,
        "input_limits": {
            "max_input_file_size_bytes": PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
            "redaction_scan_max_depth": PHASE14C_REDACTION_MAX_DEPTH,
            "redaction_scan_max_nodes": PHASE14C_REDACTION_MAX_NODES,
        },
        "forbidden_evidence_content": (
            "credential_values",
            "raw_provider_response",
            "full_prompt",
            "generated_model_text",
            "configured_model_ids",
            "raw_calendar_event_details",
            "attendee_addresses",
            "unmasked_emails",
            "event_ids",
            "todoist_ids",
            "gmail_message_ids",
            "protected_paths",
        ),
        "safety_assertions": {
            "calendar_app_connector_called": False,
            "credential_values_read": False,
            "credential_values_logged": False,
            "environment_dumped": False,
            "external_mutation": False,
            "model_provider_called": False,
            "todoist_task_created": False,
            "gmail_email_sent": False,
            "calendar_event_created": False,
            "protected_openclaw_runtime_called": False,
            "scheduler_or_background_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "dynamic_cleaning_triggered": False,
            "broad_live_activation": False,
        },
    }


def build_phase14c_wide_net_evidence_input_size_report(
    input_size_bytes: int,
) -> dict[str, Any]:
    """Build a blocked evidence report without reading an oversized input file."""

    return {
        "schema_version": PHASE14C_WIDE_NET_EVIDENCE_VALIDATION_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_EVIDENCE_BLOCKED,
        "accepted": False,
        "evidence_status": "not_loaded_input_file_too_large",
        "marker_matched": False,
        "failure_reasons": ["input_file_too_large"],
        "raw_evidence_returned": False,
        "input_values_echoed": False,
        "credential_values_reported": False,
        "unmasked_emails_reported": False,
        "input_file_size_bytes": input_size_bytes,
        "max_input_file_size_bytes": PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
        "redaction_scan_max_depth": PHASE14C_REDACTION_MAX_DEPTH,
        "redaction_scan_max_nodes": PHASE14C_REDACTION_MAX_NODES,
        "call_counts": {key: None for key in _MAX_CALL_COUNTS},
        "call_budgets": dict(_MAX_CALL_COUNTS),
        "calendar_precheck_summary": {
            "performed": False,
            "matching_event_count": None,
            "duplicate_marker_found": None,
            "event_details_logged": False,
            "attendee_addresses_logged": False,
        },
        "safety_summary": {
            "credential_values_logged": False,
            "environment_dumped": False,
            "protected_openclaw_runtime_called": False,
            "scheduler_or_background_activated": False,
            "production_db_active": False,
            "protected_paths_touched": False,
            "dynamic_cleaning_triggered": False,
            "broad_live_activation": False,
        },
    }


def validate_phase14c_wide_net_evidence_report(
    evidence_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one sanitized wide-net evidence report without echoing raw input."""

    evidence = _extract_wide_net_evidence(evidence_payload)
    reasons: list[str] = []
    if evidence is None:
        reasons.append("wide_net_evidence_missing_or_not_mapping")
        evidence = {}

    status = _recognized_status(evidence.get("status"))
    if status not in _COMPLETE_PASS_STATUSES:
        reasons.append("wide_net_status_is_not_complete_pass")
    marker_matched = evidence.get("marker") == PHASE14C_WIDE_NET_REHEARSAL_MARKER
    if not marker_matched:
        reasons.append("marker_mismatch_or_missing")

    call_counts = _call_counts(evidence)
    for key, maximum in _MAX_CALL_COUNTS.items():
        value = call_counts.get(key)
        if value is None:
            reasons.append(f"{key}_missing_or_not_int")
        elif value < 0 or value > maximum:
            reasons.append(f"{key}_over_budget")

    calendar_precheck = _mapping(evidence.get("calendar_duplicate_precheck"))
    calendar_event_calls = call_counts.get("calendar_event_create_calls")
    if status in _COMPLETE_PASS_STATUSES or calendar_event_calls:
        if calendar_precheck.get("performed") is not True:
            reasons.append("calendar_duplicate_precheck_not_performed")
        if calendar_precheck.get("matching_event_count") != 0:
            reasons.append("calendar_duplicate_precheck_count_not_zero")
        if calendar_precheck.get("duplicate_marker_found") is not False:
            reasons.append("calendar_duplicate_marker_found_or_unknown")
        if calendar_precheck.get("event_details_logged") is not False:
            reasons.append("calendar_precheck_event_details_logged")
        if calendar_precheck.get("attendee_addresses_logged") is not False:
            reasons.append("calendar_precheck_attendee_addresses_logged")

    model = _mapping(evidence.get("model_diagnostic"))
    if model.get("diagnostic_only") is not True:
        reasons.append("model_diagnostic_not_marked_diagnostic_only")
    for key in _MODEL_FALSE_FLAGS:
        if model.get(key) is not False:
            reasons.append(f"{key}_not_false")

    safety = _mapping(evidence.get("safety_assertions"))
    for key in _SAFETY_FALSE_FLAGS:
        if safety.get(key) is not False:
            reasons.append(f"{key}_not_false")

    leak_reasons = redaction_failure_reasons(evidence)
    reasons.extend(leak_reasons)
    unique_reasons = unique_reason_codes(reasons)
    accepted = not unique_reasons
    return {
        "schema_version": PHASE14C_WIDE_NET_EVIDENCE_VALIDATION_SCHEMA_VERSION,
        "status": (
            PHASE14C_WIDE_NET_EVIDENCE_VALID
            if accepted
            else PHASE14C_WIDE_NET_EVIDENCE_BLOCKED
        ),
        "accepted": accepted,
        "evidence_status": status or "missing_or_unrecognized",
        "marker_matched": marker_matched,
        "failure_reasons": unique_reasons,
        "raw_evidence_returned": False,
        "input_values_echoed": False,
        "credential_values_reported": False,
        "unmasked_emails_reported": False,
        "max_input_file_size_bytes": PHASE14C_WIDE_NET_EVIDENCE_INPUT_MAX_BYTES,
        "redaction_scan_max_depth": PHASE14C_REDACTION_MAX_DEPTH,
        "redaction_scan_max_nodes": PHASE14C_REDACTION_MAX_NODES,
        "call_counts": call_counts,
        "call_budgets": dict(_MAX_CALL_COUNTS),
        "calendar_precheck_summary": {
            "performed": calendar_precheck.get("performed") is True,
            "matching_event_count": (
                calendar_precheck.get("matching_event_count")
                if isinstance(calendar_precheck.get("matching_event_count"), int)
                else None
            ),
            "duplicate_marker_found": (
                calendar_precheck.get("duplicate_marker_found")
                if isinstance(calendar_precheck.get("duplicate_marker_found"), bool)
                else None
            ),
            "event_details_logged": calendar_precheck.get("event_details_logged")
            is True,
            "attendee_addresses_logged": calendar_precheck.get(
                "attendee_addresses_logged"
            )
            is True,
        },
        "safety_summary": {
            "credential_values_logged": safety.get("credential_values_logged") is True,
            "environment_dumped": safety.get("environment_dumped") is True,
            "protected_openclaw_runtime_called": safety.get(
                "protected_openclaw_runtime_called"
            )
            is True,
            "scheduler_or_background_activated": safety.get(
                "scheduler_or_background_activated"
            )
            is True,
            "production_db_active": safety.get("production_db_active") is True,
            "protected_paths_touched": safety.get("protected_paths_touched") is True,
            "dynamic_cleaning_triggered": safety.get("dynamic_cleaning_triggered")
            is True,
            "broad_live_activation": safety.get("broad_live_activation") is True,
        },
    }


def _extract_wide_net_evidence(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    direct = payload.get("wide_net_rehearsal")
    if isinstance(direct, Mapping):
        return direct
    if payload.get("rail") == "wide_net_rehearsal":
        return payload
    if payload.get("marker") == PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        return payload
    return None


def _recognized_status(value: object) -> str | None:
    if isinstance(value, str) and value in _KNOWN_RUN_STATUSES:
        return value
    return None


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _call_counts(evidence: Mapping[str, Any]) -> dict[str, int | None]:
    call_limits = _mapping(evidence.get("call_limits"))
    return {
        key: call_limits.get(key) if isinstance(call_limits.get(key), int) else None
        for key in _MAX_CALL_COUNTS
    }


def _fillable_wide_net_evidence_shape() -> dict[str, Any]:
    return {
        "wide_net_rehearsal": {
            "status": (
                "<phase14c_wide_net_rehearsal_passed_or_"
                "passed_with_model_diagnostic_failure>"
            ),
            "rail": "wide_net_rehearsal",
            "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            "call_limits": {
                key: "<observed_integer_count_within_budget>"
                for key in _MAX_CALL_COUNTS
            },
            "calendar_duplicate_precheck": {
                "performed": "<observed_boolean_after_sanitized_precheck>",
                "matching_event_count": "<0_required>",
                "duplicate_marker_found": "<false_required>",
                "event_details_logged": False,
                "attendee_addresses_logged": False,
            },
            "model_diagnostic": {
                "diagnostic_only": "<observed_boolean_after_model_step>",
                "model_output_drives_external_writes": False,
                "prompt_logged": False,
                "raw_provider_response_logged": False,
                "generated_model_text_logged": False,
                "configured_model_ids_logged": False,
                "credential_values_logged": False,
            },
            "todoist_task_created": "<observed_boolean_after_confirmed_create>",
            "gmail_email_sent": "<observed_boolean_after_confirmed_send>",
            "calendar_event_created": "<observed_boolean_after_confirmed_create>",
            "mutation_state": "<confirmed_task_email_and_calendar_event_created>",
            "safety_assertions": {
                "credential_values_read": "<observed_boolean_after_approved_run>",
                "credential_values_logged": False,
                "credential_values_committed": False,
                "environment_dumped": False,
                "live_clients_initialized": "<observed_boolean_after_approved_run>",
                "model_provider_called": "<observed_boolean_after_model_step>",
                "external_mutation": "<observed_boolean_after_confirmed_writes>",
                "todoist_task_created": "<observed_boolean_after_confirmed_create>",
                "gmail_email_sent": "<observed_boolean_after_confirmed_send>",
                "calendar_event_created": "<observed_boolean_after_confirmed_create>",
                "protected_openclaw_runtime_called": False,
                "scheduler_or_background_activated": False,
                "production_db_active": False,
                "protected_paths_touched": False,
                "dynamic_cleaning_triggered": False,
                "broad_live_activation": False,
            },
        }
    }

"""No-live Calendar connector wiring readiness report for Phase 14-C wide-net."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from personalos.phase14c_safety_utils import (
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_calendar_app_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_STATUS,
    build_phase14c_wide_net_calendar_app_bridge_report,
)
from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_BRIDGE_SCHEMA_VERSION,
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)


PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_calendar_connector_readiness.v1"
)
PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS = (
    "phase14c_wide_net_calendar_connector_readiness_reported"
)
PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_CONTRACT_VALID = (
    "phase14c_wide_net_calendar_connector_readiness_contract_valid"
)
PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_CONTRACT_BLOCKED = (
    "phase14c_wide_net_calendar_connector_readiness_contract_blocked"
)

PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_to_request",
    "ssl_cert_file_required",
    "connector_readiness_report_complete",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
    "calendar_cli_connector_wiring_present",
    "calendar_connector_use_authorized",
    "calendar_app_connector_called",
    "calendar_client_constructed",
    "calendar_client_injected_into_runner",
    "credential_values_read",
    "external_mutation",
    "bridge_payload_summary",
    "bridge_injection_contract",
    "precheck_wiring_contract",
    "create_wiring_contract",
    "operator_run_requirements",
    "remaining_gates_before_live",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TRUE_FIELDS: tuple[str, ...] = (
    "connector_readiness_report_complete",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
)

PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "calendar_connector_use_authorized",
    "calendar_app_connector_called",
    "calendar_client_constructed",
    "calendar_client_injected_into_runner",
    "credential_values_read",
    "external_mutation",
)

PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_NON_AUTHORIZATION: dict[str, bool] = {
    "connector_readiness_report_is_not_live_authorization": True,
    "repo_merge_is_not_live_authorization": True,
    "phase14c_authorized": False,
    "candidate_approved": False,
    "candidate_authorized": False,
    "candidate_activated": False,
    "live_service_access_authorized": False,
    "credential_handling_authorized": False,
    "calendar_connector_use_authorized": False,
    "calendar_write_authorized": False,
    "calendar_connector_wiring_authorized": False,
    "openrouter_call_authorized": False,
    "todoist_write_authorized": False,
    "gmail_send_authorized": False,
    "production_db_authorized": False,
    "scheduler_or_background_authorized": False,
    "openclaw_runtime_authorized": False,
    "dynamic_cleaning_authorized": False,
}

PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_SAFETY_ASSERTIONS: dict[str, bool] = {
    "credential_values_read": False,
    "credential_values_logged": False,
    "environment_dumped": False,
    "calendar_app_connector_called": False,
    "calendar_client_constructed": False,
    "calendar_client_injected_into_runner": False,
    "calendar_duplicate_precheck_performed": False,
    "calendar_event_created": False,
    "external_mutation": False,
    "model_provider_called": False,
    "todoist_task_created": False,
    "gmail_email_sent": False,
    "protected_openclaw_runtime_called": False,
    "scheduler_or_background_activated": False,
    "production_db_active": False,
    "protected_paths_touched": False,
    "dynamic_cleaning_triggered": False,
    "broad_live_activation": False,
    "raw_calendar_details_returned": False,
    "attendee_addresses_returned": False,
}


@dataclass(frozen=True)
class WideNetCalendarConnectorReadinessContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_calendar_connector_readiness_report() -> dict[str, Any]:
    """Build a no-live report describing the Calendar connector wiring boundary."""

    bridge = build_phase14c_wide_net_calendar_app_bridge_report()
    return {
        "schema_version": (
            PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_SCHEMA_VERSION
        ),
        "status": PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "connector_readiness_report_complete": True,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "calendar_connector_use_authorized": False,
        "calendar_app_connector_called": False,
        "calendar_client_constructed": False,
        "calendar_client_injected_into_runner": False,
        "credential_values_read": False,
        "external_mutation": False,
        "bridge_payload_summary": _bridge_payload_summary(bridge),
        "bridge_injection_contract": _bridge_injection_contract(),
        "precheck_wiring_contract": _precheck_wiring_contract(bridge),
        "create_wiring_contract": _create_wiring_contract(bridge),
        "operator_run_requirements": _operator_run_requirements(),
        "remaining_gates_before_live": _remaining_gates_before_live(),
        "non_authorization": dict(
            PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_NON_AUTHORIZATION
        ),
        "safety_assertions": dict(
            PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_SAFETY_ASSERTIONS
        ),
    }


def validate_phase14c_wide_net_calendar_connector_readiness_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetCalendarConnectorReadinessContractValidation:
    """Validate the connector readiness report without granting authorization."""

    if report is None:
        return WideNetCalendarConnectorReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_calendar_connector_readiness_report_missing",),
        )

    reasons = _blocked_wide_net_calendar_connector_readiness_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetCalendarConnectorReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetCalendarConnectorReadinessContractValidation(
        report_matches_inert_contract=True,
        reasons=(
            "wide_net_calendar_connector_readiness_remains_non_authorizing",
        ),
    )


def _bridge_payload_summary(bridge: Mapping[str, Any]) -> dict[str, object]:
    surface = _mapping(bridge.get("connector_surface"))
    precheck = _mapping(bridge.get("duplicate_precheck"))
    create = _mapping(bridge.get("calendar_create"))
    search_args = _mapping(precheck.get("google_calendar_search_events_args"))
    create_args = _mapping(create.get("google_calendar_create_event_args"))
    return {
        "app_bridge_status": bridge.get("status"),
        "app_bridge_payloads_available": (
            bridge.get("status") == PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_STATUS
        ),
        "connector_type": surface.get("connector_type"),
        "duplicate_precheck_action": surface.get("duplicate_precheck_action"),
        "create_action": surface.get("create_action"),
        "repo_cli_constructs_connector": surface.get("repo_cli_constructs_connector")
        is True,
        "repo_cli_calls_connector": surface.get("repo_cli_calls_connector") is True,
        "precheck_calendar_id": search_args.get("calendar_id"),
        "precheck_max_results": search_args.get("max_results"),
        "create_calendar_id": create_args.get("calendar_id"),
        "create_attendee_count": len(create_args.get("attendees", ())),
        "create_adds_google_meet": create_args.get("add_google_meet") is True,
        "create_recurrence": create_args.get("recurrence"),
        "normalized_precheck_contract": precheck.get("normalized_response_contract"),
    }


def _bridge_injection_contract() -> dict[str, object]:
    return {
        "bridge_class": "WideNetGoogleCalendarConnectorBridge",
        "bridge_schema_version": PHASE14C_WIDE_NET_CALENDAR_BRIDGE_SCHEMA_VERSION,
        "requires_injected_search_events_callable": True,
        "requires_injected_create_event_callable": True,
        "connector_imported_or_constructed_by_this_report": False,
        "connector_callables_bound_by_this_report": False,
        "wide_net_runner_calendar_client_available": False,
        "calendar_client_injected_into_runner_by_this_report": False,
        "future_wiring_must_keep_duplicate_precheck_first": True,
    }


def _precheck_wiring_contract(bridge: Mapping[str, Any]) -> dict[str, object]:
    precheck = _mapping(bridge.get("duplicate_precheck"))
    return {
        "connector_action": "search_events",
        "max_future_connector_calls": 1,
        "runs_before_model_todoist_gmail_or_calendar_create": True,
        "exact_title_match_required_after_connector_read": True,
        "expected_normalized_response_contract": (
            PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT
        ),
        "matching_event_count_must_equal": 0,
        "event_details_logged": False,
        "attendee_addresses_logged": False,
        "raw_connector_response_returned_by_report": False,
        "expected_normalized_fields": _string_sequence(
            precheck.get("expected_normalized_fields")
        ),
    }


def _create_wiring_contract(bridge: Mapping[str, Any]) -> dict[str, object]:
    create = _mapping(bridge.get("calendar_create"))
    return {
        "connector_action": "create_event",
        "max_future_connector_calls": 1,
        "allowed_only_after_duplicate_precheck_count": 0,
        "calendar_id": "primary",
        "attendee_count": create.get("attendee_count"),
        "conference_link": create.get("conference_link"),
        "recurrence": create.get("recurrence"),
        "attachments_required": create.get("attachments_required"),
        "raw_connector_response_returned_by_report": False,
    }


def _operator_run_requirements() -> tuple[dict[str, object], ...]:
    return (
        {
            "requirement": "fresh_human_live_approval",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "requirement": "claude_code_read_only_audit",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "requirement": "audited_calendar_connector_wiring_pr",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "requirement": "calendar_transcript_recording_plan",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "requirement": "wide_net_evidence_crosscheck_after_run",
            "required": True,
            "satisfied_by_this_report": False,
        },
    )


def _remaining_gates_before_live() -> tuple[dict[str, object], ...]:
    return (
        {
            "gate": "actual_google_calendar_connector_injection",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "calendar_connector_use_authorization",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "credential_value_loading_authorization",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "fresh_wide_net_live_approval",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "post_connector_sanitized_transcript_validation",
            "required": True,
            "satisfied_by_this_report": False,
        },
    )


def _blocked_wide_net_calendar_connector_readiness_reasons(
    report: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_calendar_connector_readiness_top_level_fields_drifted")
    if (
        report.get("schema_version")
        != PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_SCHEMA_VERSION
    ):
        reasons.append("wide_net_calendar_connector_readiness_schema_version_drifted")
    if report.get("status") != PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS:
        reasons.append("wide_net_calendar_connector_readiness_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_calendar_connector_readiness_marker_drifted")
    if (
        report.get("approval_reference_to_request")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_calendar_connector_readiness_approval_drifted")
    if report.get("ssl_cert_file_required") != PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE:
        reasons.append("wide_net_calendar_connector_readiness_ssl_cert_file_drifted")

    for field in PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(
                f"wide_net_calendar_connector_readiness_{field}_must_remain_true"
            )
    for field in PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(
                f"wide_net_calendar_connector_readiness_{field}_must_remain_false"
            )

    expected = build_phase14c_wide_net_calendar_connector_readiness_report()
    for field in (
        "bridge_payload_summary",
        "bridge_injection_contract",
        "precheck_wiring_contract",
        "create_wiring_contract",
        "non_authorization",
        "safety_assertions",
    ):
        if _mapping(report.get(field)) != _mapping(expected.get(field)):
            reasons.append(f"wide_net_calendar_connector_readiness_{field}_drifted")
    for field in ("operator_run_requirements", "remaining_gates_before_live"):
        if _records(report.get(field)) != _records(expected.get(field)):
            reasons.append(f"wide_net_calendar_connector_readiness_{field}_drifted")

    return reasons


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _records(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, tuple | list):
        return ()
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return ()
        records.append(dict(item))
    return tuple(records)


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple | list):
        return ()
    if not all(isinstance(item, str) for item in value):
        return ()
    return tuple(value)

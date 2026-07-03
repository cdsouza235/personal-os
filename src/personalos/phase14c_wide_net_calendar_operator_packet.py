"""No-live Calendar operator packet for the Phase 14-C wide-net rehearsal."""

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
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
)
from personalos.phase14c_wide_net_calendar_transcript import (
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES,
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS,
    build_phase14c_wide_net_calendar_transcript_template,
)
from personalos.phase14c_wide_net_human_gate_packet import (
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_ALLOWED_STATUSES,
    build_phase14c_wide_net_human_gate_packet_report,
    validate_phase14c_wide_net_human_gate_packet_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)


PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_calendar_operator_packet.v1"
)
PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS = (
    "phase14c_wide_net_calendar_operator_packet_ready"
)
PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_CONTRACT_VALID = (
    "phase14c_wide_net_calendar_operator_packet_contract_valid"
)
PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_CONTRACT_BLOCKED = (
    "phase14c_wide_net_calendar_operator_packet_contract_blocked"
)

PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_to_request",
    "ssl_cert_file_required",
    "operator_packet_complete",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
    "calendar_cli_connector_wiring_present",
    "calendar_connector_use_authorized",
    "calendar_app_connector_called",
    "credential_values_read",
    "external_mutation",
    "calendar_bridge_summary",
    "calendar_duplicate_precheck",
    "calendar_create",
    "calendar_transcript_summary",
    "human_gate_summary",
    "operator_sequence",
    "post_run_validation_sequence",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TRUE_FIELDS: tuple[str, ...] = (
    "operator_packet_complete",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
)

PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "calendar_connector_use_authorized",
    "calendar_app_connector_called",
    "credential_values_read",
    "external_mutation",
)

PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_NON_AUTHORIZATION: dict[str, bool] = {
    "calendar_operator_packet_is_not_live_authorization": True,
    "repo_merge_is_not_live_authorization": True,
    "human_gate_packet_template_is_not_approval": True,
    "phase14c_authorized": False,
    "candidate_approved": False,
    "candidate_authorized": False,
    "candidate_activated": False,
    "live_service_access_authorized": False,
    "credential_handling_authorized": False,
    "calendar_connector_use_authorized": False,
    "calendar_write_authorized": False,
    "openrouter_call_authorized": False,
    "todoist_write_authorized": False,
    "gmail_send_authorized": False,
    "production_db_authorized": False,
    "scheduler_or_background_authorized": False,
    "openclaw_runtime_authorized": False,
    "dynamic_cleaning_authorized": False,
}

PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SAFETY_ASSERTIONS: dict[str, bool] = {
    "credential_values_read": False,
    "credential_values_logged": False,
    "environment_dumped": False,
    "calendar_app_connector_called": False,
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
    "raw_evidence_echoed": False,
}


@dataclass(frozen=True)
class WideNetCalendarOperatorPacketContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_calendar_operator_packet_report() -> dict[str, Any]:
    """Build a no-live Calendar operator packet for the future wide-net run."""

    bridge = build_phase14c_wide_net_calendar_app_bridge_report()
    transcript = build_phase14c_wide_net_calendar_transcript_template()
    human_gate = build_phase14c_wide_net_human_gate_packet_report()
    human_gate_validation = validate_phase14c_wide_net_human_gate_packet_report_contract(
        human_gate
    )

    return {
        "schema_version": PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "operator_packet_complete": True,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "calendar_connector_use_authorized": False,
        "calendar_app_connector_called": False,
        "credential_values_read": False,
        "external_mutation": False,
        "calendar_bridge_summary": _calendar_bridge_summary(bridge),
        "calendar_duplicate_precheck": _calendar_duplicate_precheck(bridge),
        "calendar_create": _calendar_create(bridge),
        "calendar_transcript_summary": _calendar_transcript_summary(transcript),
        "human_gate_summary": _human_gate_summary(
            human_gate=human_gate,
            human_gate_contract_valid=(
                human_gate_validation.report_matches_inert_contract
            ),
        ),
        "operator_sequence": _operator_sequence(),
        "post_run_validation_sequence": _post_run_validation_sequence(),
        "non_authorization": dict(
            PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_NON_AUTHORIZATION
        ),
        "safety_assertions": dict(
            PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SAFETY_ASSERTIONS
        ),
    }


def validate_phase14c_wide_net_calendar_operator_packet_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetCalendarOperatorPacketContractValidation:
    """Validate the Calendar operator packet without granting authorization."""

    if report is None:
        return WideNetCalendarOperatorPacketContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_calendar_operator_packet_report_missing",),
        )

    reasons = _blocked_wide_net_calendar_operator_packet_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetCalendarOperatorPacketContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetCalendarOperatorPacketContractValidation(
        report_matches_inert_contract=True,
        reasons=("wide_net_calendar_operator_packet_remains_non_authorizing",),
    )


def _calendar_bridge_summary(bridge: Mapping[str, Any]) -> dict[str, object]:
    surface = _mapping(bridge.get("connector_surface"))
    duplicate_precheck = _mapping(bridge.get("duplicate_precheck"))
    calendar_create = _mapping(bridge.get("calendar_create"))
    return {
        "status": bridge.get("status"),
        "calendar_bridge_payloads_available": (
            bridge.get("status") == PHASE14C_WIDE_NET_CALENDAR_APP_BRIDGE_STATUS
        ),
        "connector_type": surface.get("connector_type"),
        "duplicate_precheck_action": surface.get("duplicate_precheck_action"),
        "create_action": surface.get("create_action"),
        "repo_cli_constructs_connector": surface.get("repo_cli_constructs_connector")
        is True,
        "repo_cli_calls_connector": surface.get("repo_cli_calls_connector") is True,
        "normalized_precheck_contract": duplicate_precheck.get(
            "normalized_response_contract"
        ),
        "create_requires_prior_matching_event_count": calendar_create.get(
            "requires_prior_duplicate_precheck_count"
        ),
    }


def _calendar_duplicate_precheck(bridge: Mapping[str, Any]) -> dict[str, object]:
    duplicate_precheck = _mapping(bridge.get("duplicate_precheck"))
    args = _mapping(duplicate_precheck.get("google_calendar_search_events_args"))
    return {
        "connector_action": "search_events",
        "connector_args": dict(args),
        "must_run_before_any_write": True,
        "exact_title_match_required_after_connector_read": True,
        "expected_normalized_response_contract": (
            PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT
        ),
        "matching_event_count_must_equal": 0,
        "event_details_logged": False,
        "attendee_addresses_logged": False,
        "max_connector_calls": 1,
    }


def _calendar_create(bridge: Mapping[str, Any]) -> dict[str, object]:
    calendar_create = _mapping(bridge.get("calendar_create"))
    args = _mapping(calendar_create.get("google_calendar_create_event_args"))
    return {
        "connector_action": "create_event",
        "connector_args": dict(args),
        "allowed_only_after_duplicate_precheck_count": 0,
        "attendee_count": calendar_create.get("attendee_count"),
        "conference_link": calendar_create.get("conference_link"),
        "recurrence": calendar_create.get("recurrence"),
        "attachments_required": calendar_create.get("attachments_required"),
        "max_connector_calls": 1,
    }


def _calendar_transcript_summary(transcript: Mapping[str, Any]) -> dict[str, object]:
    expected_precheck = _mapping(transcript.get("expected_duplicate_precheck"))
    expected_create = _mapping(transcript.get("expected_calendar_create"))
    input_limits = _mapping(transcript.get("input_limits"))
    return {
        "status": transcript.get("status"),
        "calendar_transcript_template_available": (
            transcript.get("status")
            == PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS
        ),
        "raw_event_details_allowed": transcript.get("raw_event_details_allowed")
        is True,
        "attendee_addresses_allowed": transcript.get("attendee_addresses_allowed")
        is True,
        "duplicate_precheck_action": expected_precheck.get("connector_action"),
        "calendar_create_action": expected_create.get("connector_action"),
        "allowed_sanitized_result_keys": _string_sequence(
            expected_create.get("allowed_sanitized_result_keys")
        ),
        "max_input_file_size_bytes": input_limits.get(
            "max_input_file_size_bytes",
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES,
        ),
        "validator_command": (
            "PYTHONPATH=src python3 -m personalos.cli phase14c "
            "wide-net-calendar-transcript-validate --input-file "
            "<sanitized-calendar-transcript.json> --json"
        ),
    }


def _human_gate_summary(
    *,
    human_gate: Mapping[str, Any],
    human_gate_contract_valid: bool,
) -> dict[str, object]:
    approval_template = _mapping(human_gate.get("human_approval_request_template"))
    return {
        "status": human_gate.get("status"),
        "status_allowed": (
            human_gate.get("status") in PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_ALLOWED_STATUSES
        ),
        "human_gate_packet_contract_valid": human_gate_contract_valid,
        "repo_local_preconditions_met": human_gate.get("repo_local_preconditions_met")
        is True,
        "fresh_human_message_required": approval_template.get(
            "fresh_human_message_required"
        )
        is True,
        "approval_request_template_is_not_approval": approval_template.get(
            "template_is_not_approval"
        )
        is True,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "calendar_connector_wiring_still_required": True,
        "ready_for_live_execution": human_gate.get("ready_for_live_execution") is True,
        "wide_net_live_run_authorized_by_this_report": human_gate.get(
            "wide_net_live_run_authorized_by_this_report"
        )
        is True,
    }


def _operator_sequence() -> tuple[dict[str, object], ...]:
    return (
        {
            "step": "inspect_calendar_connector_args",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-bridge-payloads --json"
            ),
            "live_connector_call_by_this_packet": False,
        },
        {
            "step": "record_sanitized_calendar_transcript",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-transcript-template --json"
            ),
            "live_connector_call_by_this_packet": False,
        },
        {
            "step": "validate_sanitized_calendar_transcript",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-transcript-validate --input-file "
                "<sanitized-calendar-transcript.json> --json"
            ),
            "live_connector_call_by_this_packet": False,
        },
        {
            "step": "confirm_human_gate_packet",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-human-gate-packet --json"
            ),
            "live_connector_call_by_this_packet": False,
        },
    )


def _post_run_validation_sequence() -> tuple[dict[str, object], ...]:
    return (
        {
            "step": "validate_sanitized_wide_net_evidence",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-evidence-validate --input-file "
                "<sanitized-wide-net-report.json> --json"
            ),
            "raw_inputs_echoed": False,
        },
        {
            "step": "crosscheck_calendar_transcript_against_evidence",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-evidence-crosscheck --calendar-transcript-file "
                "<sanitized-calendar-transcript.json> --evidence-file "
                "<sanitized-wide-net-report.json> --json"
            ),
            "raw_inputs_echoed": False,
        },
    )


def _blocked_wide_net_calendar_operator_packet_reasons(
    report: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_calendar_operator_packet_top_level_fields_drifted")
    if (
        report.get("schema_version")
        != PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SCHEMA_VERSION
    ):
        reasons.append("wide_net_calendar_operator_packet_schema_version_drifted")
    if report.get("status") != PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS:
        reasons.append("wide_net_calendar_operator_packet_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_calendar_operator_packet_marker_drifted")
    if (
        report.get("approval_reference_to_request")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_calendar_operator_packet_approval_reference_drifted")
    if report.get("ssl_cert_file_required") != PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE:
        reasons.append("wide_net_calendar_operator_packet_ssl_cert_file_drifted")

    for field in PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(f"wide_net_calendar_operator_packet_{field}_must_remain_true")
    for field in PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(
                f"wide_net_calendar_operator_packet_{field}_must_remain_false"
            )

    expected = build_phase14c_wide_net_calendar_operator_packet_report()
    for field in (
        "calendar_bridge_summary",
        "calendar_duplicate_precheck",
        "calendar_create",
        "calendar_transcript_summary",
        "human_gate_summary",
    ):
        if _mapping(report.get(field)) != _mapping(expected.get(field)):
            reasons.append(f"wide_net_calendar_operator_packet_{field}_drifted")
    if _records(report.get("operator_sequence")) != _records(
        expected.get("operator_sequence")
    ):
        reasons.append("wide_net_calendar_operator_packet_operator_sequence_drifted")
    if _records(report.get("post_run_validation_sequence")) != _records(
        expected.get("post_run_validation_sequence")
    ):
        reasons.append("wide_net_calendar_operator_packet_validation_sequence_drifted")
    if (
        _mapping(report.get("non_authorization"))
        != PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_NON_AUTHORIZATION
    ):
        reasons.append("wide_net_calendar_operator_packet_non_authorization_drifted")
    if (
        _mapping(report.get("safety_assertions"))
        != PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_SAFETY_ASSERTIONS
    ):
        reasons.append("wide_net_calendar_operator_packet_safety_assertions_drifted")

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

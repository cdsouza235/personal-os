"""No-live human-gate packet for the Phase 14-C wide-net rehearsal."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from personalos.phase14c_safety_utils import (
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_execution_handoff import (
    PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS,
    build_phase14c_wide_net_execution_handoff_report,
)
from personalos.phase14c_wide_net_pre_run_checklist import (
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED,
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED,
    build_phase14c_wide_net_pre_run_checklist_report,
    validate_phase14c_wide_net_pre_run_checklist_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_human_gate_packet.v1"
)
PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED = (
    "phase14c_wide_net_human_gate_packet_blocked"
)
PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED = (
    "phase14c_wide_net_human_gate_packet_local_checks_passed_human_approval_required"
)
PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_CONTRACT_VALID = (
    "phase14c_wide_net_human_gate_packet_contract_valid"
)
PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_CONTRACT_BLOCKED = (
    "phase14c_wide_net_human_gate_packet_contract_blocked"
)

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_to_request",
    "ssl_cert_file_required",
    "packet_complete",
    "repo_local_preconditions_met",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
    "pre_run_checklist_summary",
    "execution_handoff_summary",
    "human_approval_request_template",
    "remaining_gates_before_live",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_ALLOWED_STATUSES: tuple[str, ...] = (
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED,
    PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED,
)

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TRUE_FIELDS: tuple[str, ...] = (
    "packet_complete",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
)

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
)

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_NON_AUTHORIZATION: dict[str, bool] = {
    "human_gate_packet_is_not_live_authorization": True,
    "approval_request_template_is_not_approval": True,
    "repo_merge_is_not_live_authorization": True,
    "phase14c_authorized": False,
    "candidate_approved": False,
    "candidate_authorized": False,
    "candidate_activated": False,
    "live_service_access_authorized": False,
    "credential_handling_authorized": False,
    "calendar_connector_use_authorized": False,
    "openrouter_call_authorized": False,
    "todoist_write_authorized": False,
    "gmail_send_authorized": False,
    "calendar_write_authorized": False,
    "production_db_authorized": False,
    "scheduler_or_background_authorized": False,
    "openclaw_runtime_authorized": False,
    "dynamic_cleaning_authorized": False,
}

PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SAFETY_ASSERTIONS: dict[str, bool] = {
    "credential_values_read": False,
    "credential_values_logged": False,
    "environment_dumped": False,
    "present_config_names_reported": False,
    "ssl_cert_file_content_read": False,
    "calendar_app_connector_called": False,
    "calendar_client_injected_into_runner": False,
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
}

_EXPECTED_CALL_BUDGETS: dict[str, int] = {
    "openrouter_primary_calls": 1,
    "openrouter_fallback_calls": 1,
    "todoist_task_create_calls": 1,
    "gmail_email_send_calls": 1,
    "calendar_duplicate_precheck_calls": 1,
    "calendar_event_create_calls": 1,
    "protected_openclaw_runtime_invocation_calls": 0,
}


@dataclass(frozen=True)
class WideNetHumanGatePacketContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_human_gate_packet_report(
    *,
    pre_run_checklist_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a non-authorizing human-gate packet for the future live request."""

    checklist = (
        build_phase14c_wide_net_pre_run_checklist_report()
        if pre_run_checklist_report is None
        else dict(pre_run_checklist_report)
    )
    checklist_validation = validate_phase14c_wide_net_pre_run_checklist_report_contract(
        checklist
    )
    handoff = build_phase14c_wide_net_execution_handoff_report()
    checklist_summary = _pre_run_checklist_summary(
        checklist=checklist,
        checklist_contract_valid=checklist_validation.report_matches_inert_contract,
    )
    execution_handoff_summary = _execution_handoff_summary(handoff)
    repo_local_preconditions_met = (
        checklist_summary["repo_local_preconditions_met"] is True
        and checklist_summary["pre_run_checklist_contract_valid"] is True
        and execution_handoff_summary["execution_handoff_available"] is True
    )
    status = (
        PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED
        if repo_local_preconditions_met
        else PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED
    )

    return {
        "schema_version": PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SCHEMA_VERSION,
        "status": status,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "packet_complete": True,
        "repo_local_preconditions_met": repo_local_preconditions_met,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "external_mutation": False,
        "pre_run_checklist_summary": checklist_summary,
        "execution_handoff_summary": execution_handoff_summary,
        "human_approval_request_template": _human_approval_request_template(),
        "remaining_gates_before_live": _remaining_gates_before_live(),
        "non_authorization": dict(PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_NON_AUTHORIZATION),
        "safety_assertions": dict(PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SAFETY_ASSERTIONS),
    }


def validate_phase14c_wide_net_human_gate_packet_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetHumanGatePacketContractValidation:
    """Validate the human-gate packet without granting live authorization."""

    if report is None:
        return WideNetHumanGatePacketContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_human_gate_packet_report_missing",),
        )

    reasons = _blocked_wide_net_human_gate_packet_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetHumanGatePacketContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetHumanGatePacketContractValidation(
        report_matches_inert_contract=True,
        reasons=("wide_net_human_gate_packet_remains_non_authorizing",),
    )


def _pre_run_checklist_summary(
    *,
    checklist: Mapping[str, Any],
    checklist_contract_valid: bool,
) -> dict[str, object]:
    local = _mapping(checklist.get("local_preflight_summary"))
    decision = _mapping(checklist.get("pre_run_decision"))
    return {
        "status": checklist.get("status"),
        "pre_run_checklist_contract_valid": checklist_contract_valid,
        "repo_local_preconditions_met": checklist.get("repo_local_preconditions_met")
        is True,
        "local_preflight_passed": local.get("local_preflight_passed") is True,
        "config_names_present": local.get("config_names_present") is True,
        "ssl_cert_file_available": local.get("ssl_cert_file_available") is True,
        "missing_config_entry_count": _int_or_none(
            local.get("missing_config_entry_count")
        ),
        "missing_config_entry_names": _string_sequence(
            local.get("missing_config_entry_names")
        ),
        "required_config_entry_count": len(WIDE_NET_REQUIRED_CONFIG_NAMES),
        "present_config_names_reported": local.get("present_config_names_reported")
        is True,
        "available_config_entry_names_reported": local.get(
            "available_config_entry_names_reported"
        )
        is True,
        "credential_values_read": local.get("credential_values_read") is True,
        "credential_values_logged": local.get("credential_values_logged") is True,
        "config_values_reported": local.get("config_values_reported") is True,
        "ssl_cert_file_content_read": local.get("ssl_cert_file_content_read") is True,
        "live_execution_authorized": decision.get("live_execution_authorized") is True,
    }


def _execution_handoff_summary(handoff: Mapping[str, Any]) -> dict[str, object]:
    call_budgets = _mapping(handoff.get("call_budgets"))
    return {
        "status": handoff.get("status"),
        "execution_handoff_available": (
            handoff.get("status") == PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS
        ),
        "ready_for_live_execution": handoff.get("ready_for_live_execution") is True,
        "calendar_cli_connector_wiring_present": handoff.get(
            "calendar_cli_connector_wiring_present"
        )
        is True,
        "credential_values_read": handoff.get("credential_values_read") is True,
        "external_mutation": handoff.get("external_mutation") is True,
        "calendar_app_connector_called": handoff.get("calendar_app_connector_called")
        is True,
        "call_budgets": {
            "openrouter_primary_calls": _int_or_none(
                call_budgets.get("openrouter_primary_calls")
            ),
            "openrouter_fallback_calls": _int_or_none(
                call_budgets.get("openrouter_fallback_calls")
            ),
            "todoist_task_create_calls": _int_or_none(
                call_budgets.get("todoist_task_create_calls")
            ),
            "gmail_email_send_calls": _int_or_none(
                call_budgets.get("gmail_email_send_calls")
            ),
            "calendar_duplicate_precheck_calls": _int_or_none(
                call_budgets.get("calendar_duplicate_precheck_calls")
            ),
            "calendar_event_create_calls": _int_or_none(
                call_budgets.get("calendar_event_create_calls")
            ),
            "protected_openclaw_runtime_invocation_calls": _int_or_none(
                call_budgets.get("protected_openclaw_runtime_invocation_calls")
            ),
        },
    }


def _human_approval_request_template() -> dict[str, object]:
    return {
        "template_is_not_approval": True,
        "fresh_human_message_required": True,
        "approval_reference": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "allowed_live_actions": (
            "one OpenRouter diagnostic model probe with one fallback only if primary fails validation",
            "one Todoist Inbox/default task",
            "one Gmail controlled self-send",
            "one Google Calendar duplicate-marker precheck",
            "one self-only Google Calendar event only if the precheck count is zero",
        ),
        "explicitly_forbidden_actions": (
            "Calendar attendees",
            "Calendar recurrence",
            "Calendar conference link",
            "Calendar attachments",
            "protected OpenClaw runtime invocation",
            "scheduler or background activation",
            "production DB activation",
            "dynamic cleaning",
            "bulk writes",
            "credential value reporting",
        ),
        "suggested_human_approval_text": (
            "Approved: run exactly one Phase 14-C wide-net rehearsal using approval "
            f"reference {PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE} with "
            f"SSL_CERT_FILE={PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE}. Allowed "
            "live actions: one OpenRouter diagnostic model call with one fallback "
            "only if primary validation fails, one Todoist Inbox/default task, "
            "one Gmail controlled self-send, one Google Calendar duplicate-marker "
            "precheck, and one self-only Google Calendar event only if the precheck "
            "count is zero. Do not run protected OpenClaw runtime, production DB, "
            "scheduler/background, dynamic cleaning, bulk writes, Calendar "
            "attendees, recurrence, conference links, or attachments."
        ),
    }


def _remaining_gates_before_live() -> tuple[dict[str, object], ...]:
    return (
        {
            "gate": "fresh_explicit_human_live_approval",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "claude_code_read_only_audit_before_live_run",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "audited_calendar_connector_wiring",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "openrouter_balance_or_provider_budget_checked",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "sanitized_calendar_transcript_recorded_after_connector_use",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "sanitized_wide_net_evidence_recorded_after_live_run",
            "required": True,
            "satisfied_by_packet": False,
        },
        {
            "gate": "calendar_transcript_and_wide_net_evidence_crosschecked",
            "required": True,
            "satisfied_by_packet": False,
        },
    )


def _blocked_wide_net_human_gate_packet_reasons(
    report: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_human_gate_packet_top_level_fields_drifted")
    if (
        report.get("schema_version")
        != PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SCHEMA_VERSION
    ):
        reasons.append("wide_net_human_gate_packet_schema_version_drifted")
    if report.get("status") not in PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_ALLOWED_STATUSES:
        reasons.append("wide_net_human_gate_packet_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_human_gate_packet_marker_drifted")
    if (
        report.get("approval_reference_to_request")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_human_gate_packet_approval_reference_drifted")
    if report.get("ssl_cert_file_required") != PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE:
        reasons.append("wide_net_human_gate_packet_ssl_cert_file_drifted")

    for field in PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(f"wide_net_human_gate_packet_{field}_must_remain_true")
    for field in PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(f"wide_net_human_gate_packet_{field}_must_remain_false")

    checklist = _mapping(report.get("pre_run_checklist_summary"))
    handoff = _mapping(report.get("execution_handoff_summary"))
    template = _mapping(report.get("human_approval_request_template"))

    if checklist.get("pre_run_checklist_contract_valid") is not True:
        reasons.append("wide_net_human_gate_packet_checklist_contract_invalid")
    if checklist.get("present_config_names_reported") is not False:
        reasons.append("wide_net_human_gate_packet_present_names_reported")
    if checklist.get("available_config_entry_names_reported") is not False:
        reasons.append("wide_net_human_gate_packet_available_names_reported")
    if checklist.get("credential_values_read") is not False:
        reasons.append("wide_net_human_gate_packet_credential_values_read")
    if checklist.get("credential_values_logged") is not False:
        reasons.append("wide_net_human_gate_packet_credential_values_logged")
    if checklist.get("config_values_reported") is not False:
        reasons.append("wide_net_human_gate_packet_config_values_reported")
    if checklist.get("ssl_cert_file_content_read") is not False:
        reasons.append("wide_net_human_gate_packet_ssl_cert_content_read")
    if checklist.get("live_execution_authorized") is not False:
        reasons.append("wide_net_human_gate_packet_live_execution_authorized")
    if checklist.get("required_config_entry_count") != len(WIDE_NET_REQUIRED_CONFIG_NAMES):
        reasons.append("wide_net_human_gate_packet_required_config_count_drifted")
    if not isinstance(checklist.get("missing_config_entry_count"), int):
        reasons.append("wide_net_human_gate_packet_missing_config_count_not_int")
    if not isinstance(checklist.get("missing_config_entry_names"), Sequence):
        reasons.append("wide_net_human_gate_packet_missing_config_names_invalid")

    if handoff != _expected_execution_handoff_summary(handoff):
        reasons.append("wide_net_human_gate_packet_execution_handoff_drifted")
    if template != _human_approval_request_template():
        reasons.append("wide_net_human_gate_packet_approval_template_drifted")
    if _records(report.get("remaining_gates_before_live")) != (
        _remaining_gates_before_live()
    ):
        reasons.append("wide_net_human_gate_packet_remaining_gates_drifted")
    if (
        _mapping(report.get("non_authorization"))
        != PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_NON_AUTHORIZATION
    ):
        reasons.append("wide_net_human_gate_packet_non_authorization_drifted")
    if (
        _mapping(report.get("safety_assertions"))
        != PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_SAFETY_ASSERTIONS
    ):
        reasons.append("wide_net_human_gate_packet_safety_assertions_drifted")

    expected_preconditions_met = (
        checklist.get("repo_local_preconditions_met") is True
        and checklist.get("pre_run_checklist_contract_valid") is True
        and handoff.get("execution_handoff_available") is True
    )
    if report.get("repo_local_preconditions_met") is not expected_preconditions_met:
        reasons.append("wide_net_human_gate_packet_precondition_state_drifted")
    if (
        report.get("status") == PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_LOCAL_CHECKS_PASSED
        and expected_preconditions_met is not True
    ):
        reasons.append("wide_net_human_gate_packet_pass_status_without_local_pass")
    if (
        report.get("status") == PHASE14C_WIDE_NET_HUMAN_GATE_PACKET_BLOCKED
        and expected_preconditions_met is True
    ):
        reasons.append("wide_net_human_gate_packet_blocked_status_with_local_pass")

    return reasons


def _expected_execution_handoff_summary(
    handoff: Mapping[str, Any],
) -> dict[str, object]:
    return {
        "status": PHASE14C_WIDE_NET_EXECUTION_HANDOFF_STATUS,
        "execution_handoff_available": True,
        "ready_for_live_execution": False,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "external_mutation": False,
        "calendar_app_connector_called": False,
        "call_budgets": dict(_EXPECTED_CALL_BUDGETS),
    }


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _records(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return ()
        records.append(dict(item))
    return tuple(records)


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    if not all(isinstance(item, str) for item in value):
        return ()
    return tuple(value)


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None

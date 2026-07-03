"""No-live pre-run checklist for the Phase 14-C wide-net rehearsal."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from personalos.phase14c_safety_utils import (
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_local_preflight import (
    PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS,
    build_phase14c_wide_net_local_preflight_report,
)
from personalos.phase14c_wide_net_readiness_rollup import (
    build_phase14c_wide_net_readiness_rollup_report,
    validate_phase14c_wide_net_readiness_rollup_report_contract,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_pre_run_checklist.v1"
)
PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED = (
    "phase14c_wide_net_pre_run_checklist_blocked"
)
PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED = (
    "phase14c_wide_net_pre_run_checklist_local_checks_passed_human_gates_remain"
)
PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_CONTRACT_VALID = (
    "phase14c_wide_net_pre_run_checklist_contract_valid"
)
PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_CONTRACT_BLOCKED = (
    "phase14c_wide_net_pre_run_checklist_contract_blocked"
)

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_to_request",
    "ssl_cert_file_required",
    "repo_local_checklist_complete",
    "repo_local_preconditions_met",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
    "rollup_contract",
    "local_preflight_summary",
    "remaining_human_or_external_gates",
    "pre_run_decision",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_ALLOWED_STATUSES: tuple[str, ...] = (
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED,
    PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED,
)

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
)

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_TRUE_FIELDS: tuple[str, ...] = (
    "repo_local_checklist_complete",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
)

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_NON_AUTHORIZATION: dict[str, bool] = {
    "checklist_is_not_live_authorization": True,
    "repo_merge_is_not_live_authorization": True,
    "local_preflight_pass_is_not_live_authorization": True,
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

PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SAFETY_ASSERTIONS: dict[str, bool] = {
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


@dataclass(frozen=True)
class WideNetPreRunChecklistContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_pre_run_checklist_report(
    *,
    local_preflight_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a no-live checklist from the local preflight and rollup contract."""

    local_preflight = (
        build_phase14c_wide_net_local_preflight_report()
        if local_preflight_report is None
        else dict(local_preflight_report)
    )
    rollup = build_phase14c_wide_net_readiness_rollup_report()
    rollup_validation = validate_phase14c_wide_net_readiness_rollup_report_contract(
        rollup
    )
    rollup_contract_valid = rollup_validation.report_matches_inert_contract
    local_summary = _local_preflight_summary(local_preflight)
    repo_local_preconditions_met = (
        rollup_contract_valid and local_summary["local_preflight_passed"] is True
    )
    status = (
        PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED
        if repo_local_preconditions_met
        else PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED
    )

    return {
        "schema_version": PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SCHEMA_VERSION,
        "status": status,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "repo_local_checklist_complete": True,
        "repo_local_preconditions_met": repo_local_preconditions_met,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "external_mutation": False,
        "rollup_contract": {
            "report_matches_inert_contract": rollup_contract_valid,
            "reasons": tuple(rollup_validation.reasons),
        },
        "local_preflight_summary": local_summary,
        "remaining_human_or_external_gates": _remaining_human_or_external_gates(),
        "pre_run_decision": {
            "decision": "blocked_by_human_or_external_gates",
            "local_checks_passed": repo_local_preconditions_met,
            "live_execution_authorized": False,
            "fresh_human_approval_required": True,
            "claude_code_audit_required": True,
            "calendar_connector_wiring_required": True,
            "openrouter_budget_confirmation_required": True,
            "sanitized_transcript_and_evidence_required_after_live_run": True,
        },
        "non_authorization": dict(
            PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_NON_AUTHORIZATION
        ),
        "safety_assertions": dict(
            PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SAFETY_ASSERTIONS
        ),
    }


def validate_phase14c_wide_net_pre_run_checklist_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetPreRunChecklistContractValidation:
    """Validate the pre-run checklist without granting live readiness."""

    if report is None:
        return WideNetPreRunChecklistContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_pre_run_checklist_report_missing",),
        )

    reasons = _blocked_wide_net_pre_run_checklist_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetPreRunChecklistContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetPreRunChecklistContractValidation(
        report_matches_inert_contract=True,
        reasons=("wide_net_pre_run_checklist_remains_non_authorizing",),
    )


def _local_preflight_summary(
    local_preflight: Mapping[str, Any],
) -> dict[str, object]:
    config = _mapping(local_preflight.get("config_preflight"))
    ssl_cert = _mapping(local_preflight.get("ssl_cert_file"))
    local = _mapping(local_preflight.get("local_preflight"))
    missing_names = _string_sequence(config.get("missing_config_entry_names"))
    missing_count = config.get("missing_config_entry_count")
    if not isinstance(missing_count, int):
        missing_count = len(missing_names)

    return {
        "status": local_preflight.get("status"),
        "config_names_present": local.get("config_names_present") is True,
        "ssl_cert_file_available": local.get("ssl_cert_file_available") is True,
        "local_preflight_passed": local.get("local_preflight_passed") is True,
        "missing_config_entry_count": missing_count,
        "missing_config_entry_names": missing_names,
        "required_config_entry_count": len(WIDE_NET_REQUIRED_CONFIG_NAMES),
        "present_config_names_reported": (
            local_preflight.get("present_config_names_reported") is True
        ),
        "available_config_entry_names_reported": (
            config.get("available_config_entry_names_reported") is True
        ),
        "credential_values_read": local_preflight.get("credential_values_read") is True,
        "credential_values_logged": (
            local_preflight.get("credential_values_logged") is True
        ),
        "config_values_reported": local_preflight.get("config_values_reported") is True,
        "ssl_cert_file_content_read": ssl_cert.get("content_read") is True,
    }


def _remaining_human_or_external_gates() -> tuple[dict[str, object], ...]:
    return (
        {
            "gate": "fresh_explicit_human_live_approval",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "claude_code_read_only_audit_before_live_run",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "audited_calendar_connector_wiring",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "openrouter_balance_or_provider_budget_checked",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "sanitized_calendar_transcript_recorded_after_connector_use",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "sanitized_wide_net_evidence_recorded_after_live_run",
            "required": True,
            "satisfied_by_checklist": False,
        },
        {
            "gate": "calendar_transcript_and_wide_net_evidence_crosschecked",
            "required": True,
            "satisfied_by_checklist": False,
        },
    )


def _blocked_wide_net_pre_run_checklist_reasons(
    report: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_pre_run_checklist_top_level_fields_drifted")
    if report.get("schema_version") != PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SCHEMA_VERSION:
        reasons.append("wide_net_pre_run_checklist_schema_version_drifted")
    if report.get("status") not in PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_ALLOWED_STATUSES:
        reasons.append("wide_net_pre_run_checklist_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_pre_run_checklist_marker_drifted")
    if (
        report.get("approval_reference_to_request")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_pre_run_checklist_approval_reference_drifted")
    if report.get("ssl_cert_file_required") != PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE:
        reasons.append("wide_net_pre_run_checklist_ssl_cert_file_drifted")

    for field in PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(f"wide_net_pre_run_checklist_{field}_must_remain_true")
    for field in PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(f"wide_net_pre_run_checklist_{field}_must_remain_false")

    local_summary = _mapping(report.get("local_preflight_summary"))
    rollup = _mapping(report.get("rollup_contract"))
    pre_run_decision = _mapping(report.get("pre_run_decision"))

    if rollup.get("report_matches_inert_contract") is not True:
        reasons.append("wide_net_pre_run_checklist_rollup_contract_invalid")
    if (
        _string_sequence(rollup.get("reasons"))
        != ("wide_net_readiness_rollup_remains_inert_and_non_authorizing",)
    ):
        reasons.append("wide_net_pre_run_checklist_rollup_reasons_drifted")
    if local_summary.get("status") != PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS:
        reasons.append("wide_net_pre_run_checklist_local_preflight_status_drifted")
    if local_summary.get("present_config_names_reported") is not False:
        reasons.append("wide_net_pre_run_checklist_present_names_reported")
    if local_summary.get("available_config_entry_names_reported") is not False:
        reasons.append("wide_net_pre_run_checklist_available_names_reported")
    if local_summary.get("credential_values_read") is not False:
        reasons.append("wide_net_pre_run_checklist_credential_values_read")
    if local_summary.get("credential_values_logged") is not False:
        reasons.append("wide_net_pre_run_checklist_credential_values_logged")
    if local_summary.get("config_values_reported") is not False:
        reasons.append("wide_net_pre_run_checklist_config_values_reported")
    if local_summary.get("ssl_cert_file_content_read") is not False:
        reasons.append("wide_net_pre_run_checklist_ssl_cert_content_read")
    if local_summary.get("required_config_entry_count") != len(
        WIDE_NET_REQUIRED_CONFIG_NAMES
    ):
        reasons.append("wide_net_pre_run_checklist_required_config_count_drifted")
    if not isinstance(local_summary.get("missing_config_entry_count"), int):
        reasons.append("wide_net_pre_run_checklist_missing_config_count_not_int")
    if not isinstance(local_summary.get("missing_config_entry_names"), Sequence):
        reasons.append("wide_net_pre_run_checklist_missing_config_names_invalid")

    expected_preconditions_met = (
        rollup.get("report_matches_inert_contract") is True
        and local_summary.get("local_preflight_passed") is True
    )
    if report.get("repo_local_preconditions_met") is not expected_preconditions_met:
        reasons.append("wide_net_pre_run_checklist_precondition_state_drifted")
    if (
        report.get("status") == PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_LOCAL_CHECKS_PASSED
        and expected_preconditions_met is not True
    ):
        reasons.append("wide_net_pre_run_checklist_pass_status_without_local_pass")
    if (
        report.get("status") == PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_BLOCKED
        and expected_preconditions_met is True
    ):
        reasons.append("wide_net_pre_run_checklist_blocked_status_with_local_pass")

    if _records(report.get("remaining_human_or_external_gates")) != (
        _remaining_human_or_external_gates()
    ):
        reasons.append("wide_net_pre_run_checklist_remaining_gates_drifted")
    if pre_run_decision != _expected_pre_run_decision(expected_preconditions_met):
        reasons.append("wide_net_pre_run_checklist_decision_drifted")
    if (
        _mapping(report.get("non_authorization"))
        != PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_NON_AUTHORIZATION
    ):
        reasons.append("wide_net_pre_run_checklist_non_authorization_drifted")
    if (
        _mapping(report.get("safety_assertions"))
        != PHASE14C_WIDE_NET_PRE_RUN_CHECKLIST_SAFETY_ASSERTIONS
    ):
        reasons.append("wide_net_pre_run_checklist_safety_assertions_drifted")

    return reasons


def _expected_pre_run_decision(
    local_checks_passed: bool,
) -> dict[str, object]:
    return {
        "decision": "blocked_by_human_or_external_gates",
        "local_checks_passed": local_checks_passed,
        "live_execution_authorized": False,
        "fresh_human_approval_required": True,
        "claude_code_audit_required": True,
        "calendar_connector_wiring_required": True,
        "openrouter_budget_confirmation_required": True,
        "sanitized_transcript_and_evidence_required_after_live_run": True,
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

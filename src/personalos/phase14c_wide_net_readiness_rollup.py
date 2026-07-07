"""Repo-local readiness rollup for the Phase 14-C wide-net rehearsal."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from personalos.phase14c_safety_utils import (
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_calendar_app_bridge import (
    build_phase14c_wide_net_calendar_app_bridge_report,
)
from personalos.phase14c_wide_net_calendar_connector_readiness import (
    PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS,
    build_phase14c_wide_net_calendar_connector_readiness_report,
    validate_phase14c_wide_net_calendar_connector_readiness_report_contract,
)
from personalos.phase14c_wide_net_calendar_operator_packet import (
    PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS,
    build_phase14c_wide_net_calendar_operator_packet_report,
    validate_phase14c_wide_net_calendar_operator_packet_report_contract,
)
from personalos.phase14c_wide_net_calendar_transcript import (
    build_phase14c_wide_net_calendar_transcript_template,
)
from personalos.phase14c_wide_net_dry_run import (
    PHASE14C_WIDE_NET_DRY_RUN_PASSED,
    build_phase14c_wide_net_dry_run_report,
    validate_phase14c_wide_net_dry_run_report_contract,
)
from personalos.phase14c_wide_net_execution_handoff import (
    PHASE14C_WIDE_NET_EVIDENCE_REHEARSAL_PASSED,
    build_phase14c_wide_net_evidence_rehearsal_report,
    build_phase14c_wide_net_evidence_template_report,
    build_phase14c_wide_net_execution_handoff_report,
)
from personalos.phase14c_wide_net_local_preflight import (
    PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS,
    build_phase14c_wide_net_local_preflight_report,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
    build_phase14c_wide_net_rehearsal_plan,
)
from personalos.phase14c_wide_net_rehearsal_live import WIDE_NET_REQUIRED_CONFIG_NAMES


PHASE14C_WIDE_NET_READINESS_ROLLUP_SCHEMA_VERSION = (
    "personal_os_phase14c_wide_net_readiness_rollup.v1"
)
PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS = (
    "phase14c_wide_net_readiness_rollup_ready"
)
PHASE14C_WIDE_NET_READINESS_ROLLUP_CONTRACT_VALID = (
    "phase14c_wide_net_readiness_rollup_contract_valid"
)
PHASE14C_WIDE_NET_READINESS_ROLLUP_CONTRACT_BLOCKED = (
    "phase14c_wide_net_readiness_rollup_contract_blocked"
)

PHASE14C_WIDE_NET_READINESS_ROLLUP_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_to_request",
    "ssl_cert_file_required",
    "repo_local_rollup_complete",
    "ready_for_live_execution",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
    "component_statuses",
    "component_readiness",
    "commands",
    "required_config_entry_names",
    "config_values_reported",
    "present_config_names_reported",
    "remaining_gates_before_live",
    "evidence_rehearsal_summary",
    "dry_run_summary",
    "readiness",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_READINESS_ROLLUP_TRUE_FIELDS: tuple[str, ...] = (
    "repo_local_rollup_complete",
    "template_only_not_authorization",
    "human_live_approval_still_required",
    "claude_code_audit_required_before_live_run",
)

PHASE14C_WIDE_NET_READINESS_ROLLUP_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
    "config_values_reported",
    "present_config_names_reported",
)

PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_STATUSES: dict[str, str] = {
    "wide_net_rehearsal_plan": "phase14c_wide_net_rehearsal_plan_ready",
    "calendar_bridge_payloads": "phase14c_wide_net_calendar_app_bridge_payloads_ready",
    "calendar_connector_readiness": (
        PHASE14C_WIDE_NET_CALENDAR_CONNECTOR_READINESS_STATUS
    ),
    "calendar_transcript_template": (
        "phase14c_wide_net_calendar_transcript_template_ready"
    ),
    "calendar_operator_packet": PHASE14C_WIDE_NET_CALENDAR_OPERATOR_PACKET_STATUS,
    "wide_net_dry_run": PHASE14C_WIDE_NET_DRY_RUN_PASSED,
    "execution_handoff": "phase14c_wide_net_execution_handoff_ready",
    "evidence_template": "phase14c_wide_net_evidence_template_ready",
    "evidence_rehearsal": "phase14c_wide_net_evidence_rehearsal_passed",
    "local_preflight": PHASE14C_WIDE_NET_LOCAL_PREFLIGHT_STATUS,
}

PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_READINESS: dict[str, bool] = {
    "plan_available": True,
    "calendar_bridge_payload_report_available": True,
    "calendar_connector_readiness_available": True,
    "calendar_connector_readiness_contract_valid": True,
    "calendar_transcript_template_available": True,
    "calendar_operator_packet_available": True,
    "calendar_operator_packet_contract_valid": True,
    "wide_net_dry_run_available": True,
    "wide_net_dry_run_contract_valid": True,
    "wide_net_dry_run_passed": True,
    "execution_handoff_available": True,
    "evidence_template_available": True,
    "evidence_validator_available": True,
    "evidence_crosscheck_available": True,
    "synthetic_evidence_rehearsal_passed": True,
    "local_preflight_report_available": True,
    "wide_net_runner_available_but_fail_closed": True,
    "calendar_cli_connector_wiring_present": False,
}

PHASE14C_WIDE_NET_READINESS_ROLLUP_READINESS: dict[str, object] = {
    "status": "not_ready",
    "inert_report_only": True,
    "live_rails_activated": False,
    "repo_local_wide_net_rollup_ready": True,
}

PHASE14C_WIDE_NET_READINESS_ROLLUP_NON_AUTHORIZATION: dict[str, bool] = {
    "repo_merge_is_not_live_authorization": True,
    "rollup_is_not_live_authorization": True,
    "phase14c_authorized": False,
    "candidate_approved": False,
    "candidate_authorized": False,
    "candidate_activated": False,
    "live_service_access_authorized": False,
    "credential_handling_authorized": False,
    "production_db_authorized": False,
    "scheduler_or_background_authorized": False,
    "openclaw_runtime_authorized": False,
    "dynamic_cleaning_authorized": False,
}

PHASE14C_WIDE_NET_READINESS_ROLLUP_SAFETY_ASSERTIONS: dict[str, bool] = {
    "credential_values_read": False,
    "credential_values_logged": False,
    "environment_dumped": False,
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
    "raw_fixture_payloads_returned": False,
    "raw_evidence_echoed": False,
    "raw_calendar_details_echoed": False,
    "attendee_addresses_echoed": False,
    "raw_provider_response_logged": False,
    "full_prompt_logged": False,
    "configured_model_ids_logged": False,
}


@dataclass(frozen=True)
class WideNetReadinessRollupContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_readiness_rollup_report() -> dict[str, Any]:
    """Build a no-live rollup of the wide-net preflight and evidence surfaces."""

    plan = build_phase14c_wide_net_rehearsal_plan()
    bridge = build_phase14c_wide_net_calendar_app_bridge_report()
    calendar_connector_readiness = (
        build_phase14c_wide_net_calendar_connector_readiness_report()
    )
    calendar_connector_readiness_validation = (
        validate_phase14c_wide_net_calendar_connector_readiness_report_contract(
            calendar_connector_readiness
        )
    )
    transcript_template = build_phase14c_wide_net_calendar_transcript_template()
    calendar_operator_packet = build_phase14c_wide_net_calendar_operator_packet_report()
    calendar_operator_packet_validation = (
        validate_phase14c_wide_net_calendar_operator_packet_report_contract(
            calendar_operator_packet
        )
    )
    dry_run = build_phase14c_wide_net_dry_run_report()
    dry_run_validation = validate_phase14c_wide_net_dry_run_report_contract(dry_run)
    handoff = build_phase14c_wide_net_execution_handoff_report()
    evidence_template = build_phase14c_wide_net_evidence_template_report()
    evidence_rehearsal = build_phase14c_wide_net_evidence_rehearsal_report()
    local_preflight = build_phase14c_wide_net_local_preflight_report()
    rehearsal_passed = (
        evidence_rehearsal["status"] == PHASE14C_WIDE_NET_EVIDENCE_REHEARSAL_PASSED
    )
    calendar_operator_packet_valid = (
        calendar_operator_packet_validation.report_matches_inert_contract
    )
    calendar_connector_readiness_valid = (
        calendar_connector_readiness_validation.report_matches_inert_contract
    )
    dry_run_valid = dry_run_validation.report_matches_inert_contract
    dry_run_passed = dry_run["status"] == PHASE14C_WIDE_NET_DRY_RUN_PASSED
    repo_local_rollup_complete = (
        rehearsal_passed
        and calendar_operator_packet_valid
        and calendar_connector_readiness_valid
        and dry_run_valid
        and dry_run_passed
    )

    return {
        "schema_version": PHASE14C_WIDE_NET_READINESS_ROLLUP_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "repo_local_rollup_complete": repo_local_rollup_complete,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "wide_net_live_run_authorized_by_this_report": False,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "external_mutation": False,
        "component_statuses": {
            **PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_STATUSES,
            "wide_net_rehearsal_plan": plan["status"],
            "calendar_bridge_payloads": bridge["status"],
            "calendar_connector_readiness": calendar_connector_readiness["status"],
            "calendar_transcript_template": transcript_template["status"],
            "calendar_operator_packet": calendar_operator_packet["status"],
            "wide_net_dry_run": dry_run["status"],
            "execution_handoff": handoff["status"],
            "evidence_template": evidence_template["status"],
            "evidence_rehearsal": evidence_rehearsal["status"],
            "local_preflight": local_preflight["status"],
        },
        "component_readiness": {
            **PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_READINESS,
            "synthetic_evidence_rehearsal_passed": rehearsal_passed,
            "calendar_connector_readiness_contract_valid": (
                calendar_connector_readiness_valid
            ),
            "calendar_operator_packet_contract_valid": calendar_operator_packet_valid,
            "wide_net_dry_run_contract_valid": dry_run_valid,
            "wide_net_dry_run_passed": dry_run_passed,
        },
        "commands": _commands(),
        "required_config_entry_names": tuple(WIDE_NET_REQUIRED_CONFIG_NAMES),
        "config_values_reported": False,
        "present_config_names_reported": False,
        "remaining_gates_before_live": _remaining_gates_before_live(),
        "evidence_rehearsal_summary": _evidence_rehearsal_summary(evidence_rehearsal),
        "dry_run_summary": _dry_run_summary(dry_run),
        "readiness": {
            **PHASE14C_WIDE_NET_READINESS_ROLLUP_READINESS,
            "repo_local_wide_net_rollup_ready": repo_local_rollup_complete,
        },
        "non_authorization": dict(
            PHASE14C_WIDE_NET_READINESS_ROLLUP_NON_AUTHORIZATION
        ),
        "safety_assertions": dict(
            PHASE14C_WIDE_NET_READINESS_ROLLUP_SAFETY_ASSERTIONS
        ),
    }


def validate_phase14c_wide_net_readiness_rollup_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetReadinessRollupContractValidation:
    """Validate the wide-net readiness rollup without granting live readiness."""

    if report is None:
        return WideNetReadinessRollupContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_readiness_rollup_report_missing",),
        )

    reasons = _blocked_wide_net_readiness_rollup_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetReadinessRollupContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetReadinessRollupContractValidation(
        report_matches_inert_contract=True,
        reasons=("wide_net_readiness_rollup_remains_inert_and_non_authorizing",),
    )


def _blocked_wide_net_readiness_rollup_reasons(
    report: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != PHASE14C_WIDE_NET_READINESS_ROLLUP_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_readiness_rollup_top_level_fields_drifted")
    if report.get("schema_version") != PHASE14C_WIDE_NET_READINESS_ROLLUP_SCHEMA_VERSION:
        reasons.append("wide_net_readiness_rollup_schema_version_drifted")
    if report.get("status") != PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS:
        reasons.append("wide_net_readiness_rollup_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_readiness_rollup_marker_drifted")
    if (
        report.get("approval_reference_to_request")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_readiness_rollup_approval_reference_drifted")
    if report.get("ssl_cert_file_required") != PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE:
        reasons.append("wide_net_readiness_rollup_ssl_cert_file_drifted")

    for field in PHASE14C_WIDE_NET_READINESS_ROLLUP_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(f"wide_net_readiness_rollup_{field}_must_remain_true")
    for field in PHASE14C_WIDE_NET_READINESS_ROLLUP_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(f"wide_net_readiness_rollup_{field}_must_remain_false")

    if (
        _mapping(report.get("component_statuses"))
        != PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_STATUSES
    ):
        reasons.append("wide_net_readiness_rollup_component_statuses_drifted")
    if (
        _mapping(report.get("component_readiness"))
        != PHASE14C_WIDE_NET_READINESS_ROLLUP_COMPONENT_READINESS
    ):
        reasons.append("wide_net_readiness_rollup_component_readiness_drifted")
    if _records(report.get("commands")) != _commands():
        reasons.append("wide_net_readiness_rollup_commands_drifted")
    if (
        _string_sequence(report.get("required_config_entry_names"))
        != WIDE_NET_REQUIRED_CONFIG_NAMES
    ):
        reasons.append("wide_net_readiness_rollup_config_entry_names_drifted")
    if _records(report.get("remaining_gates_before_live")) != _remaining_gates_before_live():
        reasons.append("wide_net_readiness_rollup_remaining_gates_drifted")

    expected_evidence_summary = _evidence_rehearsal_summary(
        build_phase14c_wide_net_evidence_rehearsal_report()
    )
    if _mapping(report.get("evidence_rehearsal_summary")) != expected_evidence_summary:
        reasons.append("wide_net_readiness_rollup_evidence_summary_drifted")
    expected_dry_run_summary = _dry_run_summary(build_phase14c_wide_net_dry_run_report())
    if _mapping(report.get("dry_run_summary")) != expected_dry_run_summary:
        reasons.append("wide_net_readiness_rollup_dry_run_summary_drifted")
    if _mapping(report.get("readiness")) != PHASE14C_WIDE_NET_READINESS_ROLLUP_READINESS:
        reasons.append("wide_net_readiness_rollup_readiness_drifted")
    if (
        _mapping(report.get("non_authorization"))
        != PHASE14C_WIDE_NET_READINESS_ROLLUP_NON_AUTHORIZATION
    ):
        reasons.append("wide_net_readiness_rollup_non_authorization_drifted")
    if (
        _mapping(report.get("safety_assertions"))
        != PHASE14C_WIDE_NET_READINESS_ROLLUP_SAFETY_ASSERTIONS
    ):
        reasons.append("wide_net_readiness_rollup_safety_assertions_drifted")

    return reasons


def _commands() -> tuple[dict[str, object], ...]:
    return (
        {
            "name": "plan",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-rehearsal-plan --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_bridge_payloads",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-bridge-payloads --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_connector_readiness",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-connector-readiness --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_connector_readiness_contract",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-connector-readiness-contract --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_transcript_template",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-transcript-template --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_operator_packet",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-operator-packet --json"
            ),
            "live_action": False,
        },
        {
            "name": "calendar_operator_packet_contract",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-operator-packet-contract --json"
            ),
            "live_action": False,
        },
        {
            "name": "wide_net_dry_run",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-dry-run --json"
            ),
            "live_action": False,
        },
        {
            "name": "wide_net_dry_run_contract",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-dry-run-contract --json"
            ),
            "live_action": False,
        },
        {
            "name": "execution_handoff",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-execution-handoff --json"
            ),
            "live_action": False,
        },
        {
            "name": "evidence_template",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-evidence-template --json"
            ),
            "live_action": False,
        },
        {
            "name": "evidence_rehearsal",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-evidence-rehearsal --json"
            ),
            "live_action": False,
        },
        {
            "name": "local_preflight",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-local-preflight --json"
            ),
            "live_action": False,
        },
        {
            "name": "wide_net_gate_default",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-rehearsal --json"
            ),
            "live_action": False,
        },
    )


def _remaining_gates_before_live() -> tuple[dict[str, object], ...]:
    return (
        {
            "gate": "fresh_explicit_human_live_approval",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "claude_code_read_only_audit_before_live_run",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "audited_calendar_connector_wiring",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "ssl_cert_file_available_for_live_attempt",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "openrouter_balance_or_provider_budget_checked",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "sanitized_calendar_transcript_recorded_after_connector_use",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "sanitized_wide_net_evidence_recorded_after_live_run",
            "required": True,
            "satisfied_by_this_report": False,
        },
        {
            "gate": "calendar_transcript_and_wide_net_evidence_crosschecked",
            "required": True,
            "satisfied_by_this_report": False,
        },
    )


def _evidence_rehearsal_summary(
    evidence_rehearsal: dict[str, Any],
) -> dict[str, object]:
    summary = evidence_rehearsal["summary"]
    return {
        "accepted": evidence_rehearsal["accepted"],
        "status": evidence_rehearsal["status"],
        "synthetic_fixture_only": evidence_rehearsal["synthetic_fixture_only"],
        "not_live_evidence": evidence_rehearsal["not_live_evidence"],
        "synthetic_fixture_payloads_returned": (
            evidence_rehearsal["synthetic_fixture_payloads_returned"]
        ),
        "calendar_transcript_accepted": summary["calendar_transcript_accepted"],
        "wide_net_evidence_accepted": summary["wide_net_evidence_accepted"],
        "crosscheck_accepted": summary["crosscheck_accepted"],
        "calendar_event_create_calls": summary["calendar_event_create_calls"],
        "precheck_matching_event_count": summary["precheck_matching_event_count"],
    }


def _dry_run_summary(dry_run: Mapping[str, Any]) -> dict[str, object]:
    scenarios = _records(dry_run.get("scenario_results"))
    by_name = {str(scenario.get("scenario")): scenario for scenario in scenarios}
    return {
        "status": dry_run.get("status"),
        "fake_clients_used": dry_run.get("fake_clients_used") is True,
        "not_live_evidence": dry_run.get("template_only_not_authorization") is True,
        "scenario_count": len(scenarios),
        "all_pass_status": _scenario_status(by_name, "all_pass"),
        "model_diagnostic_failure_status": _scenario_status(
            by_name,
            "model_diagnostic_failure",
        ),
        "duplicate_calendar_marker_status": _scenario_status(
            by_name,
            "duplicate_calendar_marker",
        ),
        "all_pass_calendar_event_create_calls": _scenario_call_count(
            by_name,
            "all_pass",
            "calendar_event_create_calls",
        ),
        "model_failure_fallback_calls": _scenario_call_count(
            by_name,
            "model_diagnostic_failure",
            "openrouter_fallback_calls",
        ),
        "duplicate_marker_external_mutation": (
            _scenario_bool(
                by_name,
                "duplicate_calendar_marker",
                "simulated_runner_external_mutation",
            )
        ),
        "dry_run_external_mutation": dry_run.get("external_mutation") is True,
        "credential_values_read": dry_run.get("real_credential_values_read") is True,
    }


def _scenario_status(
    scenarios: Mapping[str, Mapping[str, Any]],
    name: str,
) -> object:
    scenario = scenarios.get(name, {})
    return scenario.get("runner_status")


def _scenario_call_count(
    scenarios: Mapping[str, Mapping[str, Any]],
    name: str,
    key: str,
) -> int | None:
    scenario = scenarios.get(name, {})
    call_counts = _mapping(scenario.get("call_counts"))
    value = call_counts.get(key)
    return value if isinstance(value, int) else None


def _scenario_bool(
    scenarios: Mapping[str, Mapping[str, Any]],
    name: str,
    key: str,
) -> bool:
    scenario = scenarios.get(name, {})
    return scenario.get(key) is True


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

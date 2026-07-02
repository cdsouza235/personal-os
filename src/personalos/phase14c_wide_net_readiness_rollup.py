"""Repo-local readiness rollup for the Phase 14-C wide-net rehearsal."""

from __future__ import annotations

from typing import Any

from personalos.phase14c_wide_net_calendar_app_bridge import (
    build_phase14c_wide_net_calendar_app_bridge_report,
)
from personalos.phase14c_wide_net_calendar_transcript import (
    build_phase14c_wide_net_calendar_transcript_template,
)
from personalos.phase14c_wide_net_execution_handoff import (
    PHASE14C_WIDE_NET_EVIDENCE_REHEARSAL_PASSED,
    build_phase14c_wide_net_evidence_rehearsal_report,
    build_phase14c_wide_net_evidence_template_report,
    build_phase14c_wide_net_execution_handoff_report,
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


def build_phase14c_wide_net_readiness_rollup_report() -> dict[str, Any]:
    """Build a no-live rollup of the wide-net preflight and evidence surfaces."""

    plan = build_phase14c_wide_net_rehearsal_plan()
    bridge = build_phase14c_wide_net_calendar_app_bridge_report()
    transcript_template = build_phase14c_wide_net_calendar_transcript_template()
    handoff = build_phase14c_wide_net_execution_handoff_report()
    evidence_template = build_phase14c_wide_net_evidence_template_report()
    evidence_rehearsal = build_phase14c_wide_net_evidence_rehearsal_report()
    rehearsal_passed = (
        evidence_rehearsal["status"] == PHASE14C_WIDE_NET_EVIDENCE_REHEARSAL_PASSED
    )

    return {
        "schema_version": PHASE14C_WIDE_NET_READINESS_ROLLUP_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_READINESS_ROLLUP_STATUS,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_to_request": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "ssl_cert_file_required": PHASE14C_WIDE_NET_REHEARSAL_SSL_CERT_FILE,
        "repo_local_rollup_complete": rehearsal_passed,
        "ready_for_live_execution": False,
        "template_only_not_authorization": True,
        "human_live_approval_still_required": True,
        "claude_code_audit_required_before_live_run": True,
        "wide_net_live_run_authorized_by_this_report": False,
        "calendar_cli_connector_wiring_present": False,
        "credential_values_read": False,
        "external_mutation": False,
        "component_statuses": {
            "wide_net_rehearsal_plan": plan["status"],
            "calendar_bridge_payloads": bridge["status"],
            "calendar_transcript_template": transcript_template["status"],
            "execution_handoff": handoff["status"],
            "evidence_template": evidence_template["status"],
            "evidence_rehearsal": evidence_rehearsal["status"],
        },
        "component_readiness": {
            "plan_available": True,
            "calendar_bridge_payload_report_available": True,
            "calendar_transcript_template_available": True,
            "execution_handoff_available": True,
            "evidence_template_available": True,
            "evidence_validator_available": True,
            "evidence_crosscheck_available": True,
            "synthetic_evidence_rehearsal_passed": rehearsal_passed,
            "wide_net_runner_available_but_fail_closed": True,
            "calendar_cli_connector_wiring_present": False,
        },
        "commands": _commands(),
        "required_config_entry_names": tuple(WIDE_NET_REQUIRED_CONFIG_NAMES),
        "config_values_reported": False,
        "present_config_names_reported": False,
        "remaining_gates_before_live": _remaining_gates_before_live(),
        "evidence_rehearsal_summary": _evidence_rehearsal_summary(evidence_rehearsal),
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
            "repo_local_wide_net_rollup_ready": rehearsal_passed,
        },
        "non_authorization": {
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
        },
        "safety_assertions": {
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
        },
    }


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
            "name": "calendar_transcript_template",
            "command": (
                "PYTHONPATH=src python3 -m personalos.cli phase14c "
                "wide-net-calendar-transcript-template --json"
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

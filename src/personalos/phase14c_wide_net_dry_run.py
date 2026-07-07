"""Deterministic no-live dry run for the Phase 14-C wide-net runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from personalos.phase14c_safety_utils import (
    redaction_failure_reasons,
    unique_reason_codes,
)
from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_EXPECTED_MODEL_TEXT,
    WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
    WIDE_NET_REQUIRED_CONFIG_NAMES,
    run_phase14c_wide_net_rehearsal,
)


PHASE14C_WIDE_NET_DRY_RUN_SCHEMA_VERSION = "personal_os_phase14c_wide_net_dry_run.v1"
PHASE14C_WIDE_NET_DRY_RUN_PASSED = "phase14c_wide_net_dry_run_passed"
PHASE14C_WIDE_NET_DRY_RUN_BLOCKED = "phase14c_wide_net_dry_run_blocked"
PHASE14C_WIDE_NET_DRY_RUN_CONTRACT_VALID = (
    "phase14c_wide_net_dry_run_contract_valid"
)
PHASE14C_WIDE_NET_DRY_RUN_CONTRACT_BLOCKED = (
    "phase14c_wide_net_dry_run_contract_blocked"
)

PHASE14C_WIDE_NET_DRY_RUN_SCENARIOS: tuple[str, ...] = (
    "all_pass",
    "model_diagnostic_failure",
    "duplicate_calendar_marker",
)

PHASE14C_WIDE_NET_DRY_RUN_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "status",
    "marker",
    "approval_reference_used_for_simulation",
    "dry_run_complete",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "template_only_not_authorization",
    "fake_clients_used",
    "placeholder_values_used",
    "real_credential_values_read",
    "credential_values_logged",
    "environment_read",
    "calendar_app_connector_called",
    "external_mutation",
    "live_clients_initialized",
    "model_provider_called",
    "scenario_order",
    "scenario_results",
    "scenario_acceptance",
    "non_authorization",
    "safety_assertions",
)

PHASE14C_WIDE_NET_DRY_RUN_TRUE_FIELDS: tuple[str, ...] = (
    "dry_run_complete",
    "template_only_not_authorization",
    "fake_clients_used",
    "placeholder_values_used",
)

PHASE14C_WIDE_NET_DRY_RUN_FALSE_FIELDS: tuple[str, ...] = (
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "real_credential_values_read",
    "credential_values_logged",
    "environment_read",
    "calendar_app_connector_called",
    "external_mutation",
    "live_clients_initialized",
    "model_provider_called",
)

PHASE14C_WIDE_NET_DRY_RUN_NON_AUTHORIZATION: dict[str, bool] = {
    "dry_run_is_not_live_authorization": True,
    "repo_merge_is_not_live_authorization": True,
    "fake_client_success_is_not_live_evidence": True,
    "phase14c_authorized": False,
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

PHASE14C_WIDE_NET_DRY_RUN_SAFETY_ASSERTIONS: dict[str, bool] = {
    "credential_values_read": False,
    "credential_values_logged": False,
    "environment_dumped": False,
    "calendar_app_connector_called": False,
    "calendar_client_injected_into_live_cli": False,
    "external_mutation": False,
    "real_model_provider_called": False,
    "real_todoist_task_created": False,
    "real_gmail_email_sent": False,
    "real_calendar_event_created": False,
    "protected_openclaw_runtime_called": False,
    "scheduler_or_background_activated": False,
    "production_db_active": False,
    "protected_paths_touched": False,
    "dynamic_cleaning_triggered": False,
    "broad_live_activation": False,
    "raw_fake_payloads_returned": False,
    "raw_provider_response_logged": False,
    "full_prompt_logged": False,
    "configured_model_ids_logged": False,
    "unmasked_emails_reported": False,
}


@dataclass(frozen=True)
class WideNetDryRunContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_phase14c_wide_net_dry_run_report(
    *,
    source_date: date | None = None,
) -> dict[str, Any]:
    """Exercise the wide-net sequence with fake clients and no live services."""

    scenario_results = tuple(
        _run_dry_run_scenario(scenario, source_date=source_date)
        for scenario in PHASE14C_WIDE_NET_DRY_RUN_SCENARIOS
    )
    scenario_acceptance = {
        result["scenario"]: result["accepted"] for result in scenario_results
    }
    accepted = all(scenario_acceptance.values())
    return {
        "schema_version": PHASE14C_WIDE_NET_DRY_RUN_SCHEMA_VERSION,
        "status": PHASE14C_WIDE_NET_DRY_RUN_PASSED
        if accepted
        else PHASE14C_WIDE_NET_DRY_RUN_BLOCKED,
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "approval_reference_used_for_simulation": (
            PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
        ),
        "dry_run_complete": accepted,
        "ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "template_only_not_authorization": True,
        "fake_clients_used": True,
        "placeholder_values_used": True,
        "real_credential_values_read": False,
        "credential_values_logged": False,
        "environment_read": False,
        "calendar_app_connector_called": False,
        "external_mutation": False,
        "live_clients_initialized": False,
        "model_provider_called": False,
        "scenario_order": PHASE14C_WIDE_NET_DRY_RUN_SCENARIOS,
        "scenario_results": scenario_results,
        "scenario_acceptance": scenario_acceptance,
        "non_authorization": dict(PHASE14C_WIDE_NET_DRY_RUN_NON_AUTHORIZATION),
        "safety_assertions": dict(PHASE14C_WIDE_NET_DRY_RUN_SAFETY_ASSERTIONS),
    }


def validate_phase14c_wide_net_dry_run_report_contract(
    report: Mapping[str, Any] | None,
) -> WideNetDryRunContractValidation:
    """Validate the wide-net dry-run report without granting authorization."""

    if report is None:
        return WideNetDryRunContractValidation(
            report_matches_inert_contract=False,
            reasons=("wide_net_dry_run_report_missing",),
        )

    reasons = _blocked_wide_net_dry_run_reasons(report)
    reasons.extend(redaction_failure_reasons(report))
    unique_reasons = tuple(unique_reason_codes(reasons))
    if unique_reasons:
        return WideNetDryRunContractValidation(
            report_matches_inert_contract=False,
            reasons=unique_reasons,
        )

    return WideNetDryRunContractValidation(
        report_matches_inert_contract=True,
        reasons=("wide_net_dry_run_remains_no_live_and_non_authorizing",),
    )


def _run_dry_run_scenario(
    scenario: str,
    *,
    source_date: date | None,
) -> dict[str, Any]:
    model = _DryRunModelClient(_model_responses_for_scenario(scenario))
    todoist = _DryRunTodoistClient()
    gmail = _DryRunGmailClient()
    calendar = _DryRunCalendarClient(
        matching_event_count=1 if scenario == "duplicate_calendar_marker" else 0
    )
    runner_report = run_phase14c_wide_net_rehearsal(
        available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
        execute_live=True,
        approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        provider="openrouter",
        api_key="placeholder-openrouter-key",
        nemotron_super_model="placeholder-nemotron-model",
        glm_5_2_model="placeholder-glm-model",
        todoist_token="placeholder-todoist-token",
        gmail_sender_email="phase14c@example.invalid",
        gmail_app_password="placeholder-gmail-password",
        gmail_controlled_recipient="phase14c@example.invalid",
        calendar_connector_label="placeholder-google-calendar-connector",
        model_client=model,
        todoist_client=todoist,
        gmail_client=gmail,
        calendar_client=calendar,
        source_date=source_date or date(2026, 7, 1),
    )
    expected_status = _expected_runner_status(scenario)
    return {
        "scenario": scenario,
        "accepted": runner_report["status"] == expected_status,
        "expected_runner_status": expected_status,
        "runner_status": runner_report["status"],
        "simulated_runner_external_mutation": (
            runner_report.get("external_mutation") is True
        ),
        "external_mutation_performed_by_dry_run": False,
        "call_counts": _call_counts(runner_report),
        "model_diagnostic": _model_summary(runner_report),
        "calendar_duplicate_precheck": _calendar_precheck_summary(runner_report),
        "simulated_results": {
            "todoist_task_created": runner_report.get("todoist_task_created") is True,
            "gmail_email_sent": runner_report.get("gmail_email_sent") is True,
            "calendar_event_created": runner_report.get("calendar_event_created")
            is True,
        },
        "fake_client_call_counts": {
            "model_requests": len(model.requests),
            "todoist_payloads": len(todoist.payloads),
            "gmail_payloads": len(gmail.payloads),
            "calendar_precheck_payloads": len(calendar.precheck_payloads),
            "calendar_create_payloads": len(calendar.payloads),
        },
        "raw_fake_payloads_returned": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "unmasked_emails_reported": False,
    }


def _expected_runner_status(scenario: str) -> str:
    if scenario == "all_pass":
        return WIDE_NET_PASSED
    if scenario == "model_diagnostic_failure":
        return WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE
    if scenario == "duplicate_calendar_marker":
        return WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER
    raise ValueError("Unrecognized wide-net dry-run scenario.")


def _model_responses_for_scenario(scenario: str) -> tuple[dict[str, Any], ...]:
    if scenario == "all_pass":
        return (
            {
                "success": True,
                "response_text": WIDE_NET_EXPECTED_MODEL_TEXT,
                "provider_alias": "openrouter",
                "input_tokens": 20,
                "output_tokens": 8,
            },
        )
    return (
        {
            "success": False,
            "failure_category": "transport_or_parse_error",
        },
        {
            "success": False,
            "failure_category": "http_error",
            "http_status": 402,
        },
    )


def _call_counts(runner_report: Mapping[str, Any]) -> dict[str, int]:
    call_limits = _mapping(runner_report.get("call_limits"))
    keys = (
        "openrouter_primary_calls",
        "openrouter_fallback_calls",
        "calendar_duplicate_precheck_calls",
        "todoist_task_create_calls",
        "gmail_email_send_calls",
        "calendar_event_create_calls",
        "protected_openclaw_runtime_invocation_calls",
    )
    return {
        key: value if isinstance((value := call_limits.get(key)), int) else 0
        for key in keys
    }


def _model_summary(runner_report: Mapping[str, Any]) -> dict[str, Any]:
    model = _mapping(runner_report.get("model_diagnostic"))
    return {
        "diagnostic_only": model.get("diagnostic_only") is True,
        "model_output_drives_external_writes": (
            model.get("model_output_drives_external_writes") is True
        ),
        "prompt_logged": model.get("prompt_logged") is True,
        "raw_provider_response_logged": model.get("raw_provider_response_logged")
        is True,
        "generated_model_text_logged": model.get("generated_model_text_logged")
        is True,
        "configured_model_ids_logged": model.get("configured_model_ids_logged")
        is True,
        "credential_values_logged": model.get("credential_values_logged") is True,
        "primary_calls": model.get("primary_calls")
        if isinstance(model.get("primary_calls"), int)
        else 0,
        "fallback_calls": model.get("fallback_calls")
        if isinstance(model.get("fallback_calls"), int)
        else 0,
        "selected_validation_passed": model.get("selected_validation_passed") is True,
    }


def _calendar_precheck_summary(runner_report: Mapping[str, Any]) -> dict[str, Any]:
    precheck = _mapping(runner_report.get("calendar_duplicate_precheck"))
    return {
        "required": precheck.get("required") is True,
        "performed": precheck.get("performed") is True,
        "matching_event_count": precheck.get("matching_event_count"),
        "duplicate_marker_found": precheck.get("duplicate_marker_found") is True,
        "event_details_logged": precheck.get("event_details_logged") is True,
        "attendee_addresses_logged": precheck.get("attendee_addresses_logged") is True,
    }


def _blocked_wide_net_dry_run_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if tuple(report) != PHASE14C_WIDE_NET_DRY_RUN_TOP_LEVEL_FIELDS:
        reasons.append("wide_net_dry_run_top_level_fields_drifted")
    if report.get("schema_version") != PHASE14C_WIDE_NET_DRY_RUN_SCHEMA_VERSION:
        reasons.append("wide_net_dry_run_schema_version_drifted")
    if report.get("status") != PHASE14C_WIDE_NET_DRY_RUN_PASSED:
        reasons.append("wide_net_dry_run_status_drifted")
    if report.get("marker") != PHASE14C_WIDE_NET_REHEARSAL_MARKER:
        reasons.append("wide_net_dry_run_marker_drifted")
    if (
        report.get("approval_reference_used_for_simulation")
        != PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
    ):
        reasons.append("wide_net_dry_run_approval_reference_drifted")

    for field in PHASE14C_WIDE_NET_DRY_RUN_TRUE_FIELDS:
        if report.get(field) is not True:
            reasons.append(f"wide_net_dry_run_{field}_must_remain_true")
    for field in PHASE14C_WIDE_NET_DRY_RUN_FALSE_FIELDS:
        if report.get(field) is not False:
            reasons.append(f"wide_net_dry_run_{field}_must_remain_false")

    expected = build_phase14c_wide_net_dry_run_report()
    for field in (
        "scenario_order",
        "scenario_results",
        "scenario_acceptance",
        "non_authorization",
        "safety_assertions",
    ):
        if report.get(field) != expected[field]:
            reasons.append(f"wide_net_dry_run_{field}_drifted")
    return reasons


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


class _DryRunModelClient:
    def __init__(self, responses: tuple[dict[str, Any], ...]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def run_probe(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.requests.append(dict(request))
        return dict(self._responses.pop(0))


class _DryRunTodoistClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def create_task(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.payloads.append(dict(payload))
        return {"id": "dry-run-id-not-live", "content": str(payload["content"])}


class _DryRunGmailClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    def send_email(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.payloads.append(dict(payload))
        return {"provider": "dry_run_gmail", "message_accepted": True}


class _DryRunCalendarClient:
    def __init__(self, *, matching_event_count: int) -> None:
        self._matching_event_count = matching_event_count
        self.precheck_payloads: list[dict[str, Any]] = []
        self.payloads: list[dict[str, Any]] = []

    def find_events_by_title(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.precheck_payloads.append(dict(payload))
        return {
            "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
            "matching_event_count": self._matching_event_count,
            "event_details_logged": False,
            "attendee_addresses_logged": False,
        }

    def create_event(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.payloads.append(dict(payload))
        return {"id": "dry-run-id-not-live", "status": "confirmed"}

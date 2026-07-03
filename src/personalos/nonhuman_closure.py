"""Inert non-human closure plan report helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from personalos.mvp_readiness import (
    BLOCKED_LIVE_RAILS,
    PENDING_HUMAN_DECISIONS,
    build_mvp_readiness_gap_report,
    validate_mvp_readiness_gap_report_contract,
)
from personalos.phase14_pilot_prep import SAFETY_POSTURE


NONHUMAN_CLOSURE_SCHEMA_VERSION = "personal_os_nonhuman_closure_plan.v1"
NONHUMAN_CLOSURE_PHASE_LABEL = "Personal OS non-human closure plan"
NONHUMAN_CLOSURE_STATUS = "blocked_by_human_gates"
NONHUMAN_CLOSURE_DEFAULT_GENERATED_AT_UTC = "2026-06-26T01:30:00+00:00"

NONHUMAN_CLOSURE_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "nonhuman_closure_complete",
    "live_mvp_ready",
    "human_gates_remaining",
    "accelerated_packet_model_recorded",
    "readiness",
    "mvp_readiness",
    "packet_plan",
    "human_required_gates",
    "blocked_live_rails",
    "non_authorization",
    "safety_posture",
)

READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "inert_report_only",
    "live_rails_activated",
)

MVP_READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "contract_valid",
    "live_mvp_ready",
    "candidate_review_tracking_only",
    "phase14_c_blocked",
    "wide_net_rollup_contract_valid",
    "wide_net_ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "wide_net_calendar_cli_connector_wiring_present",
    "wide_net_credential_values_read",
    "wide_net_external_mutation",
    "wide_net_readiness_status",
    "wide_net_live_rails_activated",
    "wide_net_remaining_gate_count",
)

PACKET_PLAN_FIELDS: tuple[str, ...] = (
    "packet_id",
    "label",
    "status",
    "scope",
    "allowed_surface",
    "claude_code_audit_required",
    "contains_human_decision",
    "contains_live_access",
)

NON_AUTHORIZATION_FIELDS: tuple[str, ...] = (
    "repo_merge_is_not_live_authorization",
    "nonhuman_closure_is_not_product_approval",
    "phase14_c_authorized",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "live_service_access_authorized",
    "credentials_loaded",
    "credentials_read",
    "production_db_path_active",
    "scheduler_activated",
    "background_loop_activated",
    "openclaw_called",
    "external_services_contacted",
    "external_mutation",
    "protected_paths_touched",
    "live_model_api_called",
    "dynamic_cleaning_implemented",
    "watch_tower_adopted",
    "agent_directory_created",
    "claude_md_created",
    "runtime_operator_scaffolding_created",
)

NON_AUTHORIZATION_FALSE_FIELDS: tuple[str, ...] = NON_AUTHORIZATION_FIELDS[2:]

NONHUMAN_CLOSURE_PACKET_PLAN: tuple[dict[str, Any], ...] = (
    {
        "packet_id": "packet_1_mvp_readiness_gap_report",
        "label": "MVP readiness gap report",
        "status": "merged_on_main",
        "scope": "inert MVP readiness gap report and contract validator",
        "allowed_surface": "repo-local source/test/docs/status only",
        "claude_code_audit_required": True,
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_2_nonhuman_closure_plan",
        "label": "Non-human closure plan",
        "status": "merged_on_main",
        "scope": "accelerated packet plan, closure report, and governance docs",
        "allowed_surface": "repo-local source/test/docs/status only",
        "claude_code_audit_required": True,
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_3_weekend_test_readiness_runbook",
        "label": "Weekend test readiness runbook",
        "status": "merged_on_main",
        "scope": "manual test plan, no-go criteria, rollback checklist, evidence templates",
        "allowed_surface": "repo-local docs/tests/report-only helpers",
        "claude_code_audit_required": True,
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_4_dry_run_evidence_bundle",
        "label": "Dry-run evidence bundle",
        "status": "merged_on_main",
        "scope": "local no-send smoke commands, fake/local fixtures, report validators",
        "allowed_surface": "repo-local tests/fixtures/report-only helpers",
        "claude_code_audit_required": True,
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_5_final_nonhuman_handoff",
        "label": "Final non-human handoff",
        "status": "merged_on_main",
        "scope": (
            "final non-human closure report, wide-net blocked gate summary, "
            "and exact human gate checklist"
        ),
        "allowed_surface": "repo-local docs/tests/report-only helpers",
        "claude_code_audit_required": True,
        "contains_human_decision": False,
        "contains_live_access": False,
    },
)

HUMAN_REQUIRED_GATES: tuple[str, ...] = (
    *PENDING_HUMAN_DECISIONS,
    "actual live-service testing remains a separate human-gated activity",
    "go/no-go launch approval remains a separate human decision",
)


@dataclass(frozen=True)
class NonhumanClosureContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_nonhuman_closure_plan_report() -> dict[str, Any]:
    """Build the inert plan for closing repo-local non-human work packets."""
    mvp_report = build_mvp_readiness_gap_report()
    mvp_validation = validate_mvp_readiness_gap_report_contract(mvp_report)

    return {
        "schema_version": NONHUMAN_CLOSURE_SCHEMA_VERSION,
        "generated_at_utc": NONHUMAN_CLOSURE_DEFAULT_GENERATED_AT_UTC,
        "phase_label": NONHUMAN_CLOSURE_PHASE_LABEL,
        "status": NONHUMAN_CLOSURE_STATUS,
        "nonhuman_closure_complete": False,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "accelerated_packet_model_recorded": True,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "mvp_readiness": {
            "status": mvp_report["status"],
            "contract_valid": mvp_validation.report_matches_inert_contract,
            "live_mvp_ready": mvp_report["live_mvp_ready"],
            "candidate_review_tracking_only": mvp_report[
                "candidate_review_tracking_only"
            ],
            "phase14_c_blocked": mvp_report["phase14_c_blocked"],
            "wide_net_rollup_contract_valid": mvp_report[
                "phase14c_wide_net_readiness"
            ]["rollup_contract_valid"],
            "wide_net_ready_for_live_execution": mvp_report[
                "phase14c_wide_net_readiness"
            ]["ready_for_live_execution"],
            "wide_net_live_run_authorized_by_this_report": mvp_report[
                "phase14c_wide_net_readiness"
            ]["wide_net_live_run_authorized_by_this_report"],
            "wide_net_calendar_cli_connector_wiring_present": mvp_report[
                "phase14c_wide_net_readiness"
            ]["calendar_cli_connector_wiring_present"],
            "wide_net_credential_values_read": mvp_report[
                "phase14c_wide_net_readiness"
            ]["credential_values_read"],
            "wide_net_external_mutation": mvp_report[
                "phase14c_wide_net_readiness"
            ]["external_mutation"],
            "wide_net_readiness_status": mvp_report[
                "phase14c_wide_net_readiness"
            ]["readiness_status"],
            "wide_net_live_rails_activated": mvp_report[
                "phase14c_wide_net_readiness"
            ]["live_rails_activated"],
            "wide_net_remaining_gate_count": mvp_report[
                "phase14c_wide_net_readiness"
            ]["remaining_gate_count"],
        },
        "packet_plan": [dict(packet) for packet in NONHUMAN_CLOSURE_PACKET_PLAN],
        "human_required_gates": list(HUMAN_REQUIRED_GATES),
        "blocked_live_rails": list(BLOCKED_LIVE_RAILS),
        "non_authorization": {
            "repo_merge_is_not_live_authorization": True,
            "nonhuman_closure_is_not_product_approval": True,
            **{field: False for field in NON_AUTHORIZATION_FALSE_FIELDS},
        },
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_nonhuman_closure_plan_report_contract(
    report: Mapping[str, Any] | None,
) -> NonhumanClosureContractValidation:
    """Validate the non-human closure plan without authorizing live work."""
    if report is None:
        return NonhumanClosureContractValidation(
            report_matches_inert_contract=False,
            reasons=("No non-human closure plan report was supplied.",),
        )

    blocked_reasons = _blocked_nonhuman_closure_reasons(report)
    if blocked_reasons:
        return NonhumanClosureContractValidation(
            report_matches_inert_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return NonhumanClosureContractValidation(
        report_matches_inert_contract=True,
        reasons=(
            "Non-human closure plan remains inert and blocked by human gates.",
        ),
    )


def _blocked_nonhuman_closure_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != NONHUMAN_CLOSURE_TOP_LEVEL_FIELDS:
        reasons.append(
            "Non-human closure report top-level fields do not match the contract."
        )

    if report.get("schema_version") != NONHUMAN_CLOSURE_SCHEMA_VERSION:
        reasons.append(
            "Non-human closure report schema_version does not match the contract."
        )

    if report.get("generated_at_utc") != NONHUMAN_CLOSURE_DEFAULT_GENERATED_AT_UTC:
        reasons.append(
            "Non-human closure report generated_at_utc does not match the contract."
        )

    if report.get("phase_label") != NONHUMAN_CLOSURE_PHASE_LABEL:
        reasons.append(
            "Non-human closure report phase_label does not match the contract."
        )

    if report.get("status") != NONHUMAN_CLOSURE_STATUS:
        reasons.append(
            "Non-human closure report status must remain blocked_by_human_gates."
        )

    expected_bools = {
        "nonhuman_closure_complete": False,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "accelerated_packet_model_recorded": True,
    }
    for field, expected in expected_bools.items():
        if report.get(field) is not expected:
            reasons.append(f"Non-human closure report field {field} drifted.")

    _check_readiness(report.get("readiness"), reasons)
    _check_mvp_readiness(report.get("mvp_readiness"), reasons)
    _check_packet_plan(report.get("packet_plan"), reasons)

    if report.get("human_required_gates") != list(HUMAN_REQUIRED_GATES):
        reasons.append("Non-human closure report human gate list drifted.")

    if report.get("blocked_live_rails") != list(BLOCKED_LIVE_RAILS):
        reasons.append("Non-human closure report blocked live rail list drifted.")

    _check_non_authorization(report.get("non_authorization"), reasons)

    if report.get("safety_posture") != dict(SAFETY_POSTURE):
        reasons.append(
            "Non-human closure report safety_posture does not match the contract."
        )

    return _dedupe(reasons)


def _check_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Non-human closure report readiness payload is missing.")
        return
    if tuple(value) != READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Non-human closure report readiness fields do not match the contract."
        )
    if value.get("status") != "not_ready":
        reasons.append("Non-human closure report readiness.status must remain not_ready.")
    if value.get("inert_report_only") is not True:
        reasons.append(
            "Non-human closure report readiness.inert_report_only must remain true."
        )
    if value.get("live_rails_activated") is not False:
        reasons.append(
            "Non-human closure report readiness.live_rails_activated must remain false."
        )


def _check_mvp_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Non-human closure report MVP readiness payload is missing.")
        return
    if tuple(value) != MVP_READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Non-human closure report MVP readiness fields do not match the contract."
        )
    expected = {
        "status": "not_ready",
        "contract_valid": True,
        "live_mvp_ready": False,
        "candidate_review_tracking_only": True,
        "phase14_c_blocked": True,
        "wide_net_rollup_contract_valid": True,
        "wide_net_ready_for_live_execution": False,
        "wide_net_live_run_authorized_by_this_report": False,
        "wide_net_calendar_cli_connector_wiring_present": False,
        "wide_net_credential_values_read": False,
        "wide_net_external_mutation": False,
        "wide_net_readiness_status": "not_ready",
        "wide_net_live_rails_activated": False,
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Non-human closure report MVP readiness field {field} drifted."
            )
    if not isinstance(value.get("wide_net_remaining_gate_count"), int):
        reasons.append(
            "Non-human closure report MVP readiness wide-net gate count is missing."
        )
    elif value["wide_net_remaining_gate_count"] < 1:
        reasons.append(
            "Non-human closure report MVP readiness wide-net gates must stay explicit."
        )


def _check_packet_plan(value: Any, reasons: list[str]) -> None:
    if value != [dict(packet) for packet in NONHUMAN_CLOSURE_PACKET_PLAN]:
        reasons.append("Non-human closure report packet plan drifted.")
    if not isinstance(value, list):
        reasons.append("Non-human closure report packet plan payload is missing.")
        return
    for packet in value:
        if not isinstance(packet, Mapping):
            reasons.append("Non-human closure report packet entry is malformed.")
            continue
        if tuple(packet) != PACKET_PLAN_FIELDS:
            reasons.append(
                "Non-human closure report packet fields do not match the contract."
            )
        if packet.get("claude_code_audit_required") is not True:
            reasons.append(
                "Non-human closure report packet audit flag must remain true."
            )
        if packet.get("contains_human_decision") is not False:
            reasons.append(
                "Non-human closure report packet human-decision flag must remain false."
            )
        if packet.get("contains_live_access") is not False:
            reasons.append(
                "Non-human closure report packet live-access flag must remain false."
            )


def _check_non_authorization(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Non-human closure report non_authorization payload is missing.")
        return
    if tuple(value) != NON_AUTHORIZATION_FIELDS:
        reasons.append(
            "Non-human closure report non_authorization fields do not match the contract."
        )
    if value.get("repo_merge_is_not_live_authorization") is not True:
        reasons.append(
            "Non-human closure report merge-is-not-live-authorization flag drifted."
        )
    if value.get("nonhuman_closure_is_not_product_approval") is not True:
        reasons.append(
            "Non-human closure report nonhuman-is-not-approval flag drifted."
        )
    for field in NON_AUTHORIZATION_FALSE_FIELDS:
        if value.get(field) is not False:
            reasons.append(
                f"Non-human closure report non_authorization field {field} must remain false."
            )


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _matches_expected_value(value: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return value is expected
    return value == expected

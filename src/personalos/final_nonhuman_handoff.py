"""Inert final non-human handoff report helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from personalos.dry_run_evidence import (
    BLOCKED_LIVE_RAILS,
    build_dry_run_evidence_bundle_report,
    validate_dry_run_evidence_bundle_report_contract,
)
from personalos.nonhuman_closure import HUMAN_REQUIRED_GATES
from personalos.phase14_pilot_prep import SAFETY_POSTURE


FINAL_NONHUMAN_HANDOFF_SCHEMA_VERSION = "personal_os_final_nonhuman_handoff.v1"
FINAL_NONHUMAN_HANDOFF_PHASE_LABEL = "Personal OS final non-human handoff"
FINAL_NONHUMAN_HANDOFF_STATUS = "nonhuman_handoff_recorded_human_gates_remain"
FINAL_NONHUMAN_HANDOFF_DEFAULT_GENERATED_AT_UTC = "2026-06-26T03:30:00+00:00"

FINAL_NONHUMAN_HANDOFF_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "safe_nonhuman_packet_artifacts_complete",
    "final_packet_requires_claude_code_audit",
    "live_mvp_ready",
    "human_gates_remaining",
    "readiness",
    "dry_run_evidence",
    "closure_packet_statuses",
    "human_gate_checklist",
    "blocked_live_rails",
    "next_human_work_plan",
    "non_authorization",
    "safety_posture",
)

READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "inert_report_only",
    "live_rails_activated",
)

DRY_RUN_EVIDENCE_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "contract_valid",
    "dry_run_execution_started",
    "repo_evidence_bundle_written",
    "temp_only_smoke_supported",
    "live_mvp_ready",
    "human_gates_remaining",
)

CLOSURE_PACKET_STATUS_FIELDS: tuple[str, ...] = (
    "packet_id",
    "label",
    "repo_local_status",
    "claude_code_audit_required",
    "claude_code_audit_status",
    "merge_status",
    "contains_human_decision",
    "contains_live_access",
)

HUMAN_GATE_CHECKLIST_FIELDS: tuple[str, ...] = (
    "gate_id",
    "label",
    "required_decision",
    "status",
)

NEXT_HUMAN_WORK_FIELDS: tuple[str, ...] = (
    "step_id",
    "label",
    "blocked_until_human_decision",
    "live_action_allowed_by_this_report",
    "credential_access_allowed_by_this_report",
)

NON_AUTHORIZATION_FIELDS: tuple[str, ...] = (
    "handoff_is_not_live_authorization",
    "repo_merge_is_not_live_authorization",
    "safe_nonhuman_completion_is_not_product_approval",
    "phase14_c_authorized",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "weekend_testing_started",
    "live_testing_authorized",
    "dry_run_execution_started",
    "repo_evidence_bundle_written",
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

NON_AUTHORIZATION_TRUE_FIELDS: tuple[str, ...] = NON_AUTHORIZATION_FIELDS[:3]
NON_AUTHORIZATION_FALSE_FIELDS: tuple[str, ...] = NON_AUTHORIZATION_FIELDS[3:]

FINAL_NONHUMAN_CLOSURE_PACKET_STATUSES: tuple[dict[str, Any], ...] = (
    {
        "packet_id": "packet_1_mvp_readiness_gap_report",
        "label": "MVP readiness gap report",
        "repo_local_status": "merged_on_main",
        "claude_code_audit_required": True,
        "claude_code_audit_status": "pass_with_notes_no_required_fixes",
        "merge_status": "merged_on_main",
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_2_nonhuman_closure_plan",
        "label": "Non-human closure plan",
        "repo_local_status": "merged_on_main",
        "claude_code_audit_required": True,
        "claude_code_audit_status": "pass",
        "merge_status": "merged_on_main",
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_3_weekend_test_readiness_runbook",
        "label": "Weekend test readiness runbook",
        "repo_local_status": "merged_on_main",
        "claude_code_audit_required": True,
        "claude_code_audit_status": "pass",
        "merge_status": "merged_on_main",
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_4_dry_run_evidence_bundle",
        "label": "Dry-run evidence bundle",
        "repo_local_status": "merged_on_main",
        "claude_code_audit_required": True,
        "claude_code_audit_status": "pass",
        "merge_status": "merged_on_main",
        "contains_human_decision": False,
        "contains_live_access": False,
    },
    {
        "packet_id": "packet_5_final_nonhuman_handoff",
        "label": "Final non-human handoff",
        "repo_local_status": "current_repo_local_packet",
        "claude_code_audit_required": True,
        "claude_code_audit_status": "required_before_merge",
        "merge_status": "pending_delegated_merge_conditions",
        "contains_human_decision": False,
        "contains_live_access": False,
    },
)

HUMAN_GATE_CHECKLIST: tuple[dict[str, str], ...] = (
    {
        "gate_id": "candidate_approval",
        "label": "Candidate approval",
        "required_decision": HUMAN_REQUIRED_GATES[0],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "phase14c_authorization",
        "label": "Phase 14-C authorization",
        "required_decision": HUMAN_REQUIRED_GATES[1],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "live_service_access",
        "label": "Live-service access",
        "required_decision": HUMAN_REQUIRED_GATES[2],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "credential_auth_handling",
        "label": "Credential/auth handling",
        "required_decision": HUMAN_REQUIRED_GATES[3],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "production_db_activation",
        "label": "Production DB activation",
        "required_decision": HUMAN_REQUIRED_GATES[4],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "scheduler_background_activation",
        "label": "Scheduler/background activation",
        "required_decision": HUMAN_REQUIRED_GATES[5],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "openclaw_handoff_or_invocation",
        "label": "OpenClaw handoff or invocation",
        "required_decision": HUMAN_REQUIRED_GATES[6],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "actual_live_service_testing",
        "label": "Actual live-service testing",
        "required_decision": HUMAN_REQUIRED_GATES[7],
        "status": "pending_human_decision",
    },
    {
        "gate_id": "go_no_go_launch_approval",
        "label": "Go/no-go launch approval",
        "required_decision": HUMAN_REQUIRED_GATES[8],
        "status": "pending_human_decision",
    },
)

NEXT_HUMAN_WORK_PLAN: tuple[dict[str, Any], ...] = (
    {
        "step_id": "review_candidate_and_phase14c_scope",
        "label": "Review candidate and Phase 14-C scope",
        "blocked_until_human_decision": True,
        "live_action_allowed_by_this_report": False,
        "credential_access_allowed_by_this_report": False,
    },
    {
        "step_id": "decide_live_rail_and_test_boundaries",
        "label": "Decide live rail and test boundaries",
        "blocked_until_human_decision": True,
        "live_action_allowed_by_this_report": False,
        "credential_access_allowed_by_this_report": False,
    },
    {
        "step_id": "review_credential_and_production_db_policy",
        "label": "Review credential and production DB policy",
        "blocked_until_human_decision": True,
        "live_action_allowed_by_this_report": False,
        "credential_access_allowed_by_this_report": False,
    },
    {
        "step_id": "conduct_manual_testing_after_authorization",
        "label": "Conduct manual testing after authorization",
        "blocked_until_human_decision": True,
        "live_action_allowed_by_this_report": False,
        "credential_access_allowed_by_this_report": False,
    },
    {
        "step_id": "make_go_no_go_launch_decision",
        "label": "Make go/no-go launch decision",
        "blocked_until_human_decision": True,
        "live_action_allowed_by_this_report": False,
        "credential_access_allowed_by_this_report": False,
    },
)


@dataclass(frozen=True)
class FinalNonhumanHandoffContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_final_nonhuman_handoff_report() -> dict[str, Any]:
    """Build the final inert handoff report for human-gated work."""
    dry_run_report = build_dry_run_evidence_bundle_report()
    dry_run_validation = validate_dry_run_evidence_bundle_report_contract(
        dry_run_report
    )

    return {
        "schema_version": FINAL_NONHUMAN_HANDOFF_SCHEMA_VERSION,
        "generated_at_utc": FINAL_NONHUMAN_HANDOFF_DEFAULT_GENERATED_AT_UTC,
        "phase_label": FINAL_NONHUMAN_HANDOFF_PHASE_LABEL,
        "status": FINAL_NONHUMAN_HANDOFF_STATUS,
        "safe_nonhuman_packet_artifacts_complete": True,
        "final_packet_requires_claude_code_audit": True,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "dry_run_evidence": {
            "status": dry_run_report["status"],
            "contract_valid": dry_run_validation.report_matches_inert_contract,
            "dry_run_execution_started": dry_run_report[
                "dry_run_execution_started"
            ],
            "repo_evidence_bundle_written": dry_run_report[
                "repo_evidence_bundle_written"
            ],
            "temp_only_smoke_supported": dry_run_report[
                "temp_only_smoke_supported"
            ],
            "live_mvp_ready": dry_run_report["live_mvp_ready"],
            "human_gates_remaining": dry_run_report["human_gates_remaining"],
        },
        "closure_packet_statuses": _materialize_records(
            FINAL_NONHUMAN_CLOSURE_PACKET_STATUSES
        ),
        "human_gate_checklist": _materialize_records(HUMAN_GATE_CHECKLIST),
        "blocked_live_rails": list(BLOCKED_LIVE_RAILS),
        "next_human_work_plan": _materialize_records(NEXT_HUMAN_WORK_PLAN),
        "non_authorization": {
            "handoff_is_not_live_authorization": True,
            "repo_merge_is_not_live_authorization": True,
            "safe_nonhuman_completion_is_not_product_approval": True,
            **{field: False for field in NON_AUTHORIZATION_FALSE_FIELDS},
        },
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_final_nonhuman_handoff_report_contract(
    report: Mapping[str, Any] | None,
) -> FinalNonhumanHandoffContractValidation:
    """Validate the final handoff report without granting live readiness."""
    if report is None:
        return FinalNonhumanHandoffContractValidation(
            report_matches_inert_contract=False,
            reasons=("No final non-human handoff report was supplied.",),
        )

    blocked_reasons = _blocked_final_handoff_reasons(report)
    if blocked_reasons:
        return FinalNonhumanHandoffContractValidation(
            report_matches_inert_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return FinalNonhumanHandoffContractValidation(
        report_matches_inert_contract=True,
        reasons=(
            "Final non-human handoff remains inert and blocked by human gates.",
        ),
    )


def _blocked_final_handoff_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != FINAL_NONHUMAN_HANDOFF_TOP_LEVEL_FIELDS:
        reasons.append(
            "Final non-human handoff report top-level fields do not match the contract."
        )

    if report.get("schema_version") != FINAL_NONHUMAN_HANDOFF_SCHEMA_VERSION:
        reasons.append(
            "Final non-human handoff report schema_version does not match the contract."
        )

    if report.get("generated_at_utc") != (
        FINAL_NONHUMAN_HANDOFF_DEFAULT_GENERATED_AT_UTC
    ):
        reasons.append(
            "Final non-human handoff report generated_at_utc does not match the contract."
        )

    if report.get("phase_label") != FINAL_NONHUMAN_HANDOFF_PHASE_LABEL:
        reasons.append(
            "Final non-human handoff report phase_label does not match the contract."
        )

    if report.get("status") != FINAL_NONHUMAN_HANDOFF_STATUS:
        reasons.append(
            "Final non-human handoff report status must remain human-gated."
        )

    expected_bools = {
        "safe_nonhuman_packet_artifacts_complete": True,
        "final_packet_requires_claude_code_audit": True,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
    }
    for field, expected in expected_bools.items():
        if report.get(field) is not expected:
            reasons.append(f"Final non-human handoff report field {field} drifted.")

    _check_readiness(report.get("readiness"), reasons)
    _check_dry_run_evidence(report.get("dry_run_evidence"), reasons)
    _check_closure_packet_statuses(report.get("closure_packet_statuses"), reasons)
    _check_human_gate_checklist(report.get("human_gate_checklist"), reasons)

    if report.get("blocked_live_rails") != list(BLOCKED_LIVE_RAILS):
        reasons.append("Final non-human handoff report blocked live rail list drifted.")

    _check_next_human_work_plan(report.get("next_human_work_plan"), reasons)
    _check_non_authorization(report.get("non_authorization"), reasons)

    if report.get("safety_posture") != dict(SAFETY_POSTURE):
        reasons.append(
            "Final non-human handoff report safety_posture does not match the contract."
        )

    return _dedupe(reasons)


def _check_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Final non-human handoff report readiness payload is missing.")
        return
    if tuple(value) != READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Final non-human handoff report readiness fields do not match the contract."
        )
    if value.get("status") != "not_ready":
        reasons.append(
            "Final non-human handoff report readiness.status must remain not_ready."
        )
    if value.get("inert_report_only") is not True:
        reasons.append(
            "Final non-human handoff report readiness.inert_report_only must remain true."
        )
    if value.get("live_rails_activated") is not False:
        reasons.append(
            "Final non-human handoff report readiness.live_rails_activated must remain false."
        )


def _check_dry_run_evidence(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append(
            "Final non-human handoff report dry-run evidence payload is missing."
        )
        return
    if tuple(value) != DRY_RUN_EVIDENCE_PAYLOAD_FIELDS:
        reasons.append(
            "Final non-human handoff report dry-run evidence fields do not match the contract."
        )
    expected = {
        "status": "dry_run_contract_recorded_not_live",
        "contract_valid": True,
        "dry_run_execution_started": False,
        "repo_evidence_bundle_written": False,
        "temp_only_smoke_supported": True,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Final non-human handoff report dry-run field {field} drifted."
            )


def _check_closure_packet_statuses(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(FINAL_NONHUMAN_CLOSURE_PACKET_STATUSES):
        reasons.append("Final non-human handoff report packet status list drifted.")
    if not isinstance(value, list):
        reasons.append("Final non-human handoff report packet status payload is missing.")
        return
    for packet in value:
        if not isinstance(packet, Mapping):
            reasons.append("Final non-human handoff report packet entry is malformed.")
            continue
        if tuple(packet) != CLOSURE_PACKET_STATUS_FIELDS:
            reasons.append(
                "Final non-human handoff report packet fields do not match the contract."
            )
        if packet.get("claude_code_audit_required") is not True:
            reasons.append(
                "Final non-human handoff report packet audit flag must remain true."
            )
        if packet.get("contains_human_decision") is not False:
            reasons.append(
                "Final non-human handoff report packet human-decision flag must remain false."
            )
        if packet.get("contains_live_access") is not False:
            reasons.append(
                "Final non-human handoff report packet live-access flag must remain false."
            )


def _check_human_gate_checklist(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(HUMAN_GATE_CHECKLIST):
        reasons.append("Final non-human handoff report human gate checklist drifted.")
    if not isinstance(value, list):
        reasons.append("Final non-human handoff report human gate payload is missing.")
        return
    for gate in value:
        if not isinstance(gate, Mapping):
            reasons.append("Final non-human handoff report human gate entry is malformed.")
            continue
        if tuple(gate) != HUMAN_GATE_CHECKLIST_FIELDS:
            reasons.append(
                "Final non-human handoff report human gate fields do not match the contract."
            )
        if gate.get("status") != "pending_human_decision":
            reasons.append(
                "Final non-human handoff report human gate status must remain pending."
            )


def _check_next_human_work_plan(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(NEXT_HUMAN_WORK_PLAN):
        reasons.append("Final non-human handoff report next human work plan drifted.")
    if not isinstance(value, list):
        reasons.append(
            "Final non-human handoff report next human work payload is missing."
        )
        return
    for step in value:
        if not isinstance(step, Mapping):
            reasons.append(
                "Final non-human handoff report next human work entry is malformed."
            )
            continue
        if tuple(step) != NEXT_HUMAN_WORK_FIELDS:
            reasons.append(
                "Final non-human handoff report next human work fields do not match the contract."
            )
        if step.get("blocked_until_human_decision") is not True:
            reasons.append(
                "Final non-human handoff report human-work block flag must remain true."
            )
        for field in (
            "live_action_allowed_by_this_report",
            "credential_access_allowed_by_this_report",
        ):
            if step.get(field) is not False:
                reasons.append(
                    f"Final non-human handoff report human-work field {field} must remain false."
                )


def _check_non_authorization(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append(
            "Final non-human handoff report non_authorization payload is missing."
        )
        return
    if tuple(value) != NON_AUTHORIZATION_FIELDS:
        reasons.append(
            "Final non-human handoff report non_authorization fields do not match the contract."
        )
    for field in NON_AUTHORIZATION_TRUE_FIELDS:
        if value.get(field) is not True:
            reasons.append(
                f"Final non-human handoff report non_authorization field {field} must remain true."
            )
    for field in NON_AUTHORIZATION_FALSE_FIELDS:
        if value.get(field) is not False:
            reasons.append(
                f"Final non-human handoff report non_authorization field {field} must remain false."
            )


def _materialize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(record) for record in records]


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

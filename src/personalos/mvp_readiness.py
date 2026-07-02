"""Inert MVP readiness gap report helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus
from personalos.phase14c_candidate_decision_support import (
    build_phase14c_candidate_decision_support_report,
    validate_phase14c_candidate_decision_support_report_contract,
)
from personalos.phase14c_wide_net_readiness_rollup import (
    build_phase14c_wide_net_readiness_rollup_report,
    validate_phase14c_wide_net_readiness_rollup_report_contract,
)


MVP_READINESS_SCHEMA_VERSION = "personal_os_mvp_readiness_gap_report.v1"
MVP_READINESS_PHASE_LABEL = "Personal OS MVP readiness gap report"
MVP_READINESS_STATUS = "not_ready"
MVP_READINESS_DEFAULT_GENERATED_AT_UTC = "2026-06-26T00:00:00+00:00"

MVP_READINESS_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "live_mvp_ready",
    "inert_report_only",
    "candidate_review_tracking_only",
    "phase14_c_blocked",
    "readiness",
    "phase14c_decision_support",
    "phase14c_wide_net_readiness",
    "completed_inert_capabilities",
    "pending_human_decisions",
    "blocked_live_rails",
    "non_authorization",
    "safety_posture",
)

COMPLETED_INERT_CAPABILITIES: tuple[str, ...] = (
    "repo-local Python package and tests",
    "SQLite migrations and local dev/test state surfaces",
    "routine, priority, today-view, dashboard, report, and briefing foundations",
    "fake/local Todoist and Calendar preview foundations",
    "Composer packet and fake model-run foundations",
    "synthetic no-send end-to-end demo evidence",
    "pre-live readiness policy and read-only readiness status surfaces",
    "Phase 14-A/B first-live pilot preparation as proposed-only scaffolding",
    "Phase 14-C candidate-review tracking record",
    "Phase 14-C decision gate and decision-support report contract",
    "Phase 14-C supervised smoke and connectivity readiness evidence",
    "Phase 14-C connected rehearsal gate and live evidence packet",
    (
        "Phase 14-C wide-net rehearsal plan, fail-closed gate, evidence "
        "validators, readiness rollup, and contract guardrails"
    ),
)

PENDING_HUMAN_DECISIONS: tuple[str, ...] = (
    "candidate approval remains a separate human decision",
    "Phase 14-C authorization remains a separate human decision",
    "Phase 14-C wide-net live rehearsal approval remains a separate human decision",
    "live-service access remains a separate human decision",
    "Calendar app connector live use remains a separate human decision",
    "credential/auth handling remains a separate human decision",
    "production DB activation remains a separate human decision",
    "scheduler/background activation remains a separate human decision",
    "OpenClaw handoff or invocation remains a separate human decision",
)

BLOCKED_LIVE_RAILS: tuple[str, ...] = (
    "gmail",
    "todoist",
    "google_calendar",
    "personalos_markdown",
    "openclaw",
    "credentials",
    "production_db",
    "scheduler_background",
    "live_model_api",
    "protected_paths",
    "dynamic_cleaning",
    "watch_tower",
    ".agent",
    "CLAUDE.md",
    "runtime_operator_scaffolding",
)

NON_AUTHORIZATION_FALSE_FIELDS: tuple[str, ...] = (
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

READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "inert_report_only",
    "live_rails_activated",
)

PHASE14C_DECISION_SUPPORT_PAYLOAD_FIELDS: tuple[str, ...] = (
    "report_status",
    "report_contract_valid",
    "decision_record_validated_as_unfilled",
    "human_decision_recorded",
    "candidate_review_tracking_only",
    "phase14_c_blocked",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
)

PHASE14C_WIDE_NET_READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "rollup_status",
    "rollup_contract_valid",
    "repo_local_rollup_complete",
    "ready_for_live_execution",
    "wide_net_live_run_authorized_by_this_report",
    "calendar_cli_connector_wiring_present",
    "credential_values_read",
    "external_mutation",
    "synthetic_evidence_rehearsal_passed",
    "remaining_gate_count",
    "readiness_status",
    "inert_report_only",
    "live_rails_activated",
)

NON_AUTHORIZATION_FIELDS: tuple[str, ...] = (
    "approval_to_merge_docs_is_not_live_authorization",
    *NON_AUTHORIZATION_FALSE_FIELDS,
)


@dataclass(frozen=True)
class MvpReadinessContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_mvp_readiness_gap_report() -> dict[str, Any]:
    """Build an inert report showing why live MVP activation remains blocked."""
    decision_support_report = build_phase14c_candidate_decision_support_report()
    decision_support_contract = (
        validate_phase14c_candidate_decision_support_report_contract(
            decision_support_report
        )
    )
    wide_net_report = build_phase14c_wide_net_readiness_rollup_report()
    wide_net_contract = validate_phase14c_wide_net_readiness_rollup_report_contract(
        wide_net_report
    )

    return {
        "schema_version": MVP_READINESS_SCHEMA_VERSION,
        "generated_at_utc": MVP_READINESS_DEFAULT_GENERATED_AT_UTC,
        "phase_label": MVP_READINESS_PHASE_LABEL,
        "status": MVP_READINESS_STATUS,
        "live_mvp_ready": False,
        "inert_report_only": True,
        "candidate_review_tracking_only": True,
        "phase14_c_blocked": True,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "phase14c_decision_support": {
            "report_status": decision_support_report["status"],
            "report_contract_valid": (
                decision_support_contract.report_matches_inert_contract
            ),
            "decision_record_validated_as_unfilled": decision_support_report[
                "decision_record_validated_as_unfilled"
            ],
            "human_decision_recorded": decision_support_report[
                "human_decision_recorded"
            ],
            "candidate_review_tracking_only": decision_support_report[
                "candidate_review_tracking_only"
            ],
            "phase14_c_blocked": decision_support_report["phase14_c_blocked"],
            "candidate_approved": decision_support_report["candidate_approved"],
            "candidate_authorized": decision_support_report[
                "candidate_authorized"
            ],
            "candidate_activated": decision_support_report[
                "candidate_activated"
            ],
            "candidate_run": decision_support_report["candidate_run"],
        },
        "phase14c_wide_net_readiness": {
            "rollup_status": wide_net_report["status"],
            "rollup_contract_valid": (
                wide_net_contract.report_matches_inert_contract
            ),
            "repo_local_rollup_complete": wide_net_report[
                "repo_local_rollup_complete"
            ],
            "ready_for_live_execution": wide_net_report[
                "ready_for_live_execution"
            ],
            "wide_net_live_run_authorized_by_this_report": wide_net_report[
                "wide_net_live_run_authorized_by_this_report"
            ],
            "calendar_cli_connector_wiring_present": wide_net_report[
                "calendar_cli_connector_wiring_present"
            ],
            "credential_values_read": wide_net_report["credential_values_read"],
            "external_mutation": wide_net_report["external_mutation"],
            "synthetic_evidence_rehearsal_passed": wide_net_report[
                "component_readiness"
            ]["synthetic_evidence_rehearsal_passed"],
            "remaining_gate_count": len(
                wide_net_report["remaining_gates_before_live"]
            ),
            "readiness_status": wide_net_report["readiness"]["status"],
            "inert_report_only": wide_net_report["readiness"][
                "inert_report_only"
            ],
            "live_rails_activated": wide_net_report["readiness"][
                "live_rails_activated"
            ],
        },
        "completed_inert_capabilities": list(COMPLETED_INERT_CAPABILITIES),
        "pending_human_decisions": list(PENDING_HUMAN_DECISIONS),
        "blocked_live_rails": list(BLOCKED_LIVE_RAILS),
        "non_authorization": {
            "approval_to_merge_docs_is_not_live_authorization": True,
            **{field: False for field in NON_AUTHORIZATION_FALSE_FIELDS},
        },
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_mvp_readiness_gap_report_contract(
    report: Mapping[str, Any] | None,
) -> MvpReadinessContractValidation:
    """Validate the inert MVP readiness gap report without authorizing work."""
    if report is None:
        return MvpReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=("No MVP readiness gap report was supplied.",),
        )

    blocked_reasons = _blocked_mvp_readiness_reasons(report)
    if blocked_reasons:
        return MvpReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return MvpReadinessContractValidation(
        report_matches_inert_contract=True,
        reasons=("MVP readiness gap report remains inert and not_ready.",),
    )


def _blocked_mvp_readiness_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != MVP_READINESS_TOP_LEVEL_FIELDS:
        reasons.append("MVP readiness report top-level fields do not match the contract.")

    if report.get("schema_version") != MVP_READINESS_SCHEMA_VERSION:
        reasons.append("MVP readiness report schema_version does not match the contract.")

    if report.get("phase_label") != MVP_READINESS_PHASE_LABEL:
        reasons.append("MVP readiness report phase_label does not match the contract.")

    if report.get("generated_at_utc") != MVP_READINESS_DEFAULT_GENERATED_AT_UTC:
        reasons.append(
            "MVP readiness report generated_at_utc does not match the contract."
        )

    if report.get("status") != MVP_READINESS_STATUS:
        reasons.append("MVP readiness report status must remain not_ready.")

    for field in (
        "live_mvp_ready",
        "inert_report_only",
        "candidate_review_tracking_only",
        "phase14_c_blocked",
    ):
        expected = field != "live_mvp_ready"
        if report.get(field) is not expected:
            reasons.append(f"MVP readiness report field {field} drifted.")

    readiness = report.get("readiness")
    if not isinstance(readiness, Mapping):
        reasons.append("MVP readiness report readiness payload is missing.")
    else:
        if tuple(readiness) != READINESS_PAYLOAD_FIELDS:
            reasons.append(
                "MVP readiness report readiness fields do not match the contract."
            )
        if readiness.get("status") != "not_ready":
            reasons.append("MVP readiness report readiness.status must remain not_ready.")
        if readiness.get("inert_report_only") is not True:
            reasons.append(
                "MVP readiness report readiness.inert_report_only must remain true."
            )
        if readiness.get("live_rails_activated") is not False:
            reasons.append(
                "MVP readiness report readiness.live_rails_activated must remain false."
            )

    phase14c = report.get("phase14c_decision_support")
    if not isinstance(phase14c, Mapping):
        reasons.append("MVP readiness report Phase 14-C payload is missing.")
    else:
        if tuple(phase14c) != PHASE14C_DECISION_SUPPORT_PAYLOAD_FIELDS:
            reasons.append(
                "MVP readiness report Phase 14-C fields do not match the contract."
            )
        if phase14c.get("report_status") != PilotPrepStatus.DECISION_NEEDED.value:
            reasons.append(
                "MVP readiness report Phase 14-C status must remain decision_needed."
            )
        for field in (
            "report_contract_valid",
            "decision_record_validated_as_unfilled",
            "candidate_review_tracking_only",
            "phase14_c_blocked",
        ):
            if phase14c.get(field) is not True:
                reasons.append(f"MVP readiness report Phase 14-C field {field} drifted.")
        for field in (
            "human_decision_recorded",
            "candidate_approved",
            "candidate_authorized",
            "candidate_activated",
            "candidate_run",
        ):
            if phase14c.get(field) is not False:
                reasons.append(f"MVP readiness report Phase 14-C field {field} drifted.")

    wide_net = report.get("phase14c_wide_net_readiness")
    if not isinstance(wide_net, Mapping):
        reasons.append("MVP readiness report Phase 14-C wide-net payload is missing.")
    else:
        if tuple(wide_net) != PHASE14C_WIDE_NET_READINESS_PAYLOAD_FIELDS:
            reasons.append(
                "MVP readiness report Phase 14-C wide-net fields do not match the contract."
            )
        if (
            wide_net.get("rollup_status")
            != "phase14c_wide_net_readiness_rollup_ready"
        ):
            reasons.append(
                "MVP readiness report Phase 14-C wide-net rollup status drifted."
            )
        for field in (
            "rollup_contract_valid",
            "repo_local_rollup_complete",
            "synthetic_evidence_rehearsal_passed",
            "inert_report_only",
        ):
            if wide_net.get(field) is not True:
                reasons.append(
                    f"MVP readiness report Phase 14-C wide-net field {field} drifted."
                )
        for field in (
            "ready_for_live_execution",
            "wide_net_live_run_authorized_by_this_report",
            "calendar_cli_connector_wiring_present",
            "credential_values_read",
            "external_mutation",
            "live_rails_activated",
        ):
            if wide_net.get(field) is not False:
                reasons.append(
                    f"MVP readiness report Phase 14-C wide-net field {field} drifted."
                )
        if wide_net.get("readiness_status") != "not_ready":
            reasons.append(
                "MVP readiness report Phase 14-C wide-net readiness must remain not_ready."
            )
        if not isinstance(wide_net.get("remaining_gate_count"), int):
            reasons.append(
                "MVP readiness report Phase 14-C wide-net remaining gate count is missing."
            )
        elif wide_net["remaining_gate_count"] < 1:
            reasons.append(
                "MVP readiness report Phase 14-C wide-net remaining gates must stay explicit."
            )

    if report.get("completed_inert_capabilities") != list(COMPLETED_INERT_CAPABILITIES):
        reasons.append("MVP readiness report completed capability list drifted.")

    if report.get("pending_human_decisions") != list(PENDING_HUMAN_DECISIONS):
        reasons.append("MVP readiness report pending human decision list drifted.")

    if report.get("blocked_live_rails") != list(BLOCKED_LIVE_RAILS):
        reasons.append("MVP readiness report blocked live rail list drifted.")

    non_authorization = report.get("non_authorization")
    if not isinstance(non_authorization, Mapping):
        reasons.append("MVP readiness report non_authorization payload is missing.")
    else:
        if tuple(non_authorization) != NON_AUTHORIZATION_FIELDS:
            reasons.append(
                "MVP readiness report non_authorization fields do not match the contract."
            )
        if (
            non_authorization.get("approval_to_merge_docs_is_not_live_authorization")
            is not True
        ):
            reasons.append(
                "MVP readiness report merge-is-not-live-authorization flag drifted."
            )
        for field in NON_AUTHORIZATION_FALSE_FIELDS:
            if non_authorization.get(field) is not False:
                reasons.append(
                    f"MVP readiness report non_authorization field {field} must remain false."
                )

    if report.get("safety_posture") != dict(SAFETY_POSTURE):
        reasons.append("MVP readiness report safety_posture does not match the contract.")

    return _dedupe(reasons)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped

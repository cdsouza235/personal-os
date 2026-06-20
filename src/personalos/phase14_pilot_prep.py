"""Inert Phase 14-A/B first-live pilot preparation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from personalos.pre_live_readiness import (
    PreLiveReadinessConfig,
    evaluate_pre_live_readiness,
    readiness_report_to_summary,
)


PHASE14_AB_SCHEMA_VERSION = "phase14_ab_pilot_preparation.v1"
PILOT_NAME = "Phase 14-A/B first live pilot preparation"
PILOT_PHASE_LABEL = "Phase 14-A/B first live pilot preparation"
PROPOSED_RAIL = "todoist"
PROPOSED_OPERATION = "create_routine_task"

SAFETY_POSTURE: dict[str, Any] = {
    "readiness.status": "not_ready",
    "inert_report_only": True,
    "live_rails_activated": False,
    "credentials_loaded": False,
    "credentials_read": False,
    "production_db_path_active": False,
    "scheduler_activated": False,
    "launch_agent_installed": False,
    "crontab_modified": False,
    "daemon_started": False,
    "openclaw_called": False,
    "external_services_contacted": False,
    "external_mutation": False,
    "gmail_touched": False,
    "todoist_touched": False,
    "calendar_touched": False,
    "personalos_markdown_written": False,
    "protected_paths_touched": False,
}

NON_SELECTED_RAILS: tuple[str, ...] = (
    "gmail",
    "google_calendar",
    "personalos_markdown",
    "openclaw_runtime_workflows",
    "scheduler_launchagent_background_loop",
    "live_model_api_calls",
    "production_sqlite_state",
)

BLOCKED_LIVE_FIELDS: tuple[str, ...] = (
    "live_todoist_task_id",
    "todoist_task_id",
    "external_object_id",
    "credential",
    "credential_label",
    "oauth",
    "token",
    "api_key",
    "api_config",
)


class PilotPrepStatus(StrEnum):
    PROPOSED_ONLY = "proposed_only"
    DECISION_NEEDED = "decision_needed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CandidateValidation:
    status: PilotPrepStatus
    accepted: bool
    candidate_ref: str | None
    reasons: tuple[str, ...]
    normalized_candidate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "accepted": self.accepted,
            "candidate_ref": self.candidate_ref,
            "reasons": list(self.reasons),
            "normalized_candidate": self.normalized_candidate,
        }


def build_phase14_ab_pilot_preparation(
    candidate_records: Sequence[Mapping[str, Any]] | None = None,
    *,
    generated_at_utc: str = "2026-06-20T00:00:00+00:00",
) -> dict[str, Any]:
    """Build an inert proposed-pilot design/readiness artifact.

    The returned report is a preparation artifact only. It does not create
    clients, read credentials, open a database, contact Todoist, or write
    external state.
    """
    candidates = tuple(candidate_records or ())
    validations = tuple(validate_phase13g_todoist_candidate(candidate) for candidate in candidates)
    accepted = tuple(validation for validation in validations if validation.accepted)
    status, selected_candidate, candidate_reasons = _candidate_selection_result(
        candidates,
        validations,
        accepted,
    )
    readiness = readiness_report_to_summary(
        evaluate_pre_live_readiness(PreLiveReadinessConfig())
    )
    activation_blockers = _activation_blockers(
        status=status,
        selected_candidate=selected_candidate,
        readiness_status=str(readiness["status"]),
    )

    return {
        "schema_version": PHASE14_AB_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "pilot_name": PILOT_NAME,
        "phase_label": PILOT_PHASE_LABEL,
        "status": status.value,
        "proposed_only": True,
        "pilot_authorized": False,
        "pilot_approved": False,
        "pilot_run": False,
        "execution_allowed": False,
        "stop_before_live_activation": True,
        "selected_rail": PROPOSED_RAIL,
        "operation": PROPOSED_OPERATION,
        "candidate_source": {
            "required_source": "exactly_one_validated_phase_13g_candidate",
            "phase13g_validated_candidate_found": selected_candidate is not None,
            "candidate_ref": (
                selected_candidate.get("candidate_ref")
                if selected_candidate is not None
                else None
            ),
            "decision": _candidate_decision_text(status, selected_candidate),
            "reasons": candidate_reasons,
        },
        "selected_candidate": selected_candidate,
        "pilot_design": _pilot_design(selected_candidate),
        "readiness": {
            "status": readiness["status"],
            "inert_report_only": readiness["inert_report_only"],
            "live_rails_activated": readiness["live_rails_activated"],
            "blocked_or_missing_gate_count": readiness["blocked_or_missing_gate_count"],
            "blocked_or_non_disabled_rail_count": (
                readiness["blocked_or_non_disabled_rail_count"]
            ),
        },
        "activation_blockers": activation_blockers,
        "rollback_abort_criteria": _rollback_abort_criteria(),
        "evidence_required_before_live_attempt": _required_evidence(),
        "preflight_checklist": render_phase14_ab_preflight_checklist(
            status=status,
            selected_candidate=selected_candidate,
            activation_blockers=activation_blockers,
        ),
        "non_selected_rails": [
            {
                "rail": rail,
                "status": "disabled",
                "credentials_loaded": False,
                "client_initialized": False,
                "external_mutation": False,
            }
            for rail in NON_SELECTED_RAILS
        ],
        "safety_posture": dict(SAFETY_POSTURE),
        "candidate_validations": [validation.to_dict() for validation in validations],
    }


def validate_phase13g_todoist_candidate(
    candidate: Mapping[str, Any] | None,
) -> CandidateValidation:
    """Validate that a candidate is exactly one inert Phase 13G Todoist candidate."""
    if candidate is None:
        return CandidateValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            accepted=False,
            candidate_ref=None,
            reasons=("No candidate was supplied; human selection is required.",),
        )

    candidate_ref = _candidate_ref(candidate)
    blocked_reasons = _blocked_candidate_reasons(candidate)
    if blocked_reasons:
        return CandidateValidation(
            status=PilotPrepStatus.BLOCKED,
            accepted=False,
            candidate_ref=candidate_ref,
            reasons=tuple(blocked_reasons),
        )

    missing_or_ambiguous = _missing_or_ambiguous_candidate_reasons(candidate)
    if missing_or_ambiguous:
        return CandidateValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            accepted=False,
            candidate_ref=candidate_ref,
            reasons=tuple(missing_or_ambiguous),
        )

    normalized_candidate = {
        "candidate_ref": candidate_ref,
        "source_phase": "Phase 13G",
        "validation_status": "validated",
        "rail": PROPOSED_RAIL,
        "operation": PROPOSED_OPERATION,
        "candidate_type": "routine_todoist_task",
        "task_title": str(candidate["task_title"]).strip(),
        "risk_level": "low",
        "self_only": True,
        "foreground_only": True,
        "future_only": True,
        "routine_task_oriented": True,
        "approved": False,
        "live_todoist_task_created": False,
    }
    return CandidateValidation(
        status=PilotPrepStatus.PROPOSED_ONLY,
        accepted=True,
        candidate_ref=candidate_ref,
        reasons=(
            "Candidate is recorded as Phase 13G.",
            "Candidate validation_status is validated.",
            "Candidate is a Todoist routine-task create candidate.",
            "Candidate is low-risk, self-only, foreground-only, and future-only.",
            "Candidate is not approved and has no live Todoist object identifier.",
        ),
        normalized_candidate=normalized_candidate,
    )


def guard_phase14_ab_live_execution(preparation_report: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed for any attempted live execution from this prep artifact."""
    readiness = preparation_report.get("readiness")
    readiness_status = (
        readiness.get("status", "unknown") if isinstance(readiness, Mapping) else "unknown"
    )
    blockers = list(preparation_report.get("activation_blockers", ()))
    if readiness_status != "ready":
        blockers.insert(0, f"readiness.status={readiness_status}; live execution is blocked.")
    if not preparation_report.get("pilot_authorized", False):
        blockers.append("Pilot is not authorized.")
    if not preparation_report.get("pilot_approved", False):
        blockers.append("Pilot is not approved.")

    return {
        "status": "blocked",
        "live_action_attempted": False,
        "todoist_touched": False,
        "external_services_contacted": False,
        "external_mutation": False,
        "scheduler_activated": False,
        "openclaw_called": False,
        "reason": "Phase 14-A/B preparation is inert and has no live execution path.",
        "blockers": _dedupe(blockers),
        "safety_posture": dict(SAFETY_POSTURE),
    }


def render_phase14_ab_preflight_checklist(
    *,
    status: PilotPrepStatus,
    selected_candidate: Mapping[str, Any] | None,
    activation_blockers: Sequence[str],
) -> list[str]:
    candidate_line = (
        f"candidate_ref={selected_candidate['candidate_ref']}"
        if selected_candidate is not None
        else "candidate_ref=human_selection_required"
    )
    return [
        f"Phase label: {PILOT_PHASE_LABEL}",
        "Pilot is proposed only; it is not authorized.",
        f"Candidate source: {candidate_line}",
        f"Preparation status: {status.value}",
        "Readiness must remain not_ready during this packet.",
        "Todoist credentials, clients, API calls, and task IDs are not configured.",
        "Gmail, Calendar, PersonalOS Markdown, scheduler, OpenClaw, production DB, "
        "and live model/API rails stay disabled.",
        "Stop before live activation.",
        "Activation blockers: " + "; ".join(activation_blockers),
    ]


def _candidate_selection_result(
    candidates: Sequence[Mapping[str, Any]],
    validations: Sequence[CandidateValidation],
    accepted: Sequence[CandidateValidation],
) -> tuple[PilotPrepStatus, dict[str, Any] | None, list[str]]:
    if not candidates:
        return (
            PilotPrepStatus.DECISION_NEEDED,
            None,
            [
                "No concrete Phase 13G candidate record exists in this preparation input.",
                "Human selection is required before Phase 14 can proceed.",
            ],
        )
    blocked = [
        validation
        for validation in validations
        if validation.status is PilotPrepStatus.BLOCKED
    ]
    if blocked:
        return (
            PilotPrepStatus.BLOCKED,
            None,
            _dedupe(reason for validation in blocked for reason in validation.reasons),
        )
    if len(accepted) == 1:
        return (
            PilotPrepStatus.PROPOSED_ONLY,
            dict(accepted[0].normalized_candidate or {}),
            list(accepted[0].reasons),
        )
    if len(accepted) > 1:
        return (
            PilotPrepStatus.DECISION_NEEDED,
            None,
            [
                "Multiple validated Phase 13G candidates were supplied.",
                "Choosing between candidates is a human decision before Phase 14 can proceed.",
            ],
        )
    return (
        PilotPrepStatus.DECISION_NEEDED,
        None,
        _dedupe(reason for validation in validations for reason in validation.reasons),
    )


def _blocked_candidate_reasons(candidate: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _truthy(candidate.get("approved")) or _truthy(candidate.get("pilot_approved")):
        reasons.append("Candidate is already marked approved; this packet cannot approve pilots.")
    for field in BLOCKED_LIVE_FIELDS:
        if _present(candidate.get(field)):
            reasons.append(f"Candidate contains prohibited live field: {field}.")
    if _truthy(candidate.get("live_todoist_task_created")):
        reasons.append("Candidate indicates a live Todoist task was already created.")
    if _normalize(candidate.get("rail")) not in {"", PROPOSED_RAIL}:
        reasons.append("Candidate rail is not Todoist.")
    high_stakes_domain = _normalize(candidate.get("domain")) in {
        "tax",
        "legal_estate",
        "portfolio_crypto_investments",
        "health_medical",
        "relationship_messages",
    }
    if high_stakes_domain:
        reasons.append("Candidate domain is high-stakes and cannot be the first pilot.")
    return reasons


def _missing_or_ambiguous_candidate_reasons(candidate: Mapping[str, Any]) -> list[str]:
    checks = (
        (
            _normalize(candidate.get("source_phase")) == "phase_13g",
            "Candidate is not recorded as a Phase 13G candidate.",
        ),
        (
            _normalize(candidate.get("validation_status")) == "validated",
            "Candidate is not recorded as validated.",
        ),
        (
            _normalize(candidate.get("rail")) == PROPOSED_RAIL,
            "Candidate is not a Todoist candidate.",
        ),
        (
            _normalize(candidate.get("operation")) in {PROPOSED_OPERATION, "create_task"},
            "Candidate is not a Todoist routine-task creation candidate.",
        ),
        (
            _normalize(candidate.get("candidate_type")) == "routine_todoist_task",
            "Candidate type is not routine_todoist_task.",
        ),
        (_normalize(candidate.get("risk_level")) == "low", "Candidate is not low-risk."),
        (_truthy(candidate.get("self_only")), "Candidate is not explicitly self-only."),
        (
            _truthy(candidate.get("foreground_only")),
            "Candidate is not explicitly foreground-only.",
        ),
        (_truthy(candidate.get("future_only")), "Candidate is not explicitly future-only."),
        (
            _truthy(candidate.get("routine_task_oriented")),
            "Candidate is not explicitly routine-task oriented.",
        ),
        (_present(candidate.get("task_title")), "Candidate task title is missing."),
    )
    return [reason for passed, reason in checks if not passed]


def _pilot_design(selected_candidate: Mapping[str, Any] | None) -> dict[str, Any]:
    if selected_candidate is None:
        candidate_rationale = {
            "low_risk": "No candidate selected; no candidate-specific low-risk claim is made.",
            "self_only": "No candidate selected; self-only status requires human selection.",
            "foreground_only": (
                "No candidate selected; foreground-only status requires human selection."
            ),
            "future_only": "No candidate selected; future-only status requires human selection.",
        }
    else:
        candidate_rationale = {
            "low_risk": "The candidate is labeled low risk and creates one visible routine task.",
            "self_only": "The candidate is labeled self_only and has no recipients or attendees.",
            "foreground_only": (
                "The candidate is labeled foreground_only and excludes background execution."
            ),
            "future_only": "The candidate is labeled future_only and is not a past-dated task.",
        }

    return {
        "candidate_rationale": candidate_rationale,
        "allowed_future_human_decision_needed": (
            "Chris must select and explicitly approve exactly one candidate in a later phase."
        ),
        "approval_state": "not_authorized",
        "live_write_state": "not_attempted",
        "max_live_items_if_later_approved": 1,
        "foreground_only": True,
        "self_only": True,
        "future_only": True,
        "low_risk_only": True,
        "instructions_that_would_cause_live_write": False,
        "real_todoist_task_ids": [],
        "credential_configuration": None,
    }


def _activation_blockers(
    *,
    status: PilotPrepStatus,
    selected_candidate: Mapping[str, Any] | None,
    readiness_status: str,
) -> list[str]:
    blockers = [
        "Pilot is proposed only and is not authorized.",
        f"readiness.status={readiness_status}; live activation requires a later gate.",
        "Chris approval for a selected pilot is missing.",
        "Credential label and scopes are not approved.",
        "No live Todoist client or API path exists in this packet.",
        "Side-effect ledger, idempotency, duplicate prevention, completion report, "
        "and rollback evidence are not approved for a live attempt.",
        "Stop before live activation.",
    ]
    if selected_candidate is None:
        blockers.insert(0, "No exact validated Phase 13G candidate is selected.")
    if status is PilotPrepStatus.BLOCKED:
        blockers.insert(0, "Candidate input is blocked.")
    return blockers


def _rollback_abort_criteria() -> list[str]:
    return [
        "Abort if candidate selection is missing, ambiguous, not Phase 13G, or not validated.",
        "Abort if any live rail, credential, production DB, scheduler, OpenClaw, or protected "
        "path boundary is required.",
        "Abort if readiness.status is not ready or if inert_report_only is false.",
        "Abort if Chris approval is missing, stale, or not specific to the selected pilot.",
        "Abort if the exact dry-run evidence, ledger intent, idempotency key, duplicate check, "
        "completion report target, or rollback plan is missing.",
        "Future Todoist rollback options must be named before activation: delete, close, "
        "reopen, annotate, or create a corrective task.",
    ]


def _required_evidence() -> list[str]:
    return [
        "Exactly one validated Phase 13G Todoist routine-task candidate.",
        "Exact future-only candidate preview generated from the same input.",
        "Explicit Chris approval naming rail, operation, operator, host, commit, input, "
        "credential label if any, stop condition, and undo plan.",
        "Readiness and activation checklist evidence for the selected pilot.",
        "Idempotency key and payload fingerprint.",
        "Ledger intent before any live attempt.",
        "Duplicate-prevention result.",
        "Completion report target and required fields.",
        "Rollback or undo plan.",
        "Proof that non-selected rails remain disabled.",
    ]


def _candidate_decision_text(
    status: PilotPrepStatus,
    selected_candidate: Mapping[str, Any] | None,
) -> str:
    if selected_candidate is not None:
        return "Exactly one validated Phase 13G candidate is proposed only."
    if status is PilotPrepStatus.BLOCKED:
        return "Candidate input is blocked; no pilot can proceed."
    return "Human selection is required before Phase 14 can proceed."


def _candidate_ref(candidate: Mapping[str, Any]) -> str:
    for key in ("candidate_ref", "source_id", "id", "dedupe_key", "task_title"):
        value = candidate.get(key)
        if _present(value):
            return str(value).strip()
    return "unnamed-candidate"


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _truthy(value: Any) -> bool:
    return value is True or _normalize(value) in {"true", "yes", "1"}


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = str(value)
        if text not in seen:
            deduped.append(text)
            seen.add(text)
    return deduped

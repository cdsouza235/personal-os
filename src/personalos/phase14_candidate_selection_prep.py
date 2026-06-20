"""Inert pre-Phase-14-C candidate-selection preparation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus


PHASE14_CANDIDATE_SELECTION_SCHEMA_VERSION = "phase14_candidate_selection_prep.v1"
PACKET_NAME = "pre-Phase-14-C candidate-selection preparation"
PHASE_LABEL = "pre-Phase-14-C candidate-selection preparation"

REQUIRED_TEXT_FIELDS: tuple[str, ...] = (
    "candidate_label",
    "routine_task_description",
    "intended_future_window",
    "self_only_reason",
    "low_risk_reason",
    "foreground_only_reason",
    "future_only_reason",
    "abort_criteria",
    "evidence_required_before_live_authorization",
)

REQUIRED_CONFIRMATION_FIELDS: tuple[str, ...] = (
    "no_sensitive_domain_confirmation",
    "no_external_dependency_confirmation",
    "no_gmail_or_calendar_dependency_confirmation",
    "no_credentials_or_live_ids_confirmation",
    "no_protected_path_interaction_confirmation",
    "no_scheduler_background_or_openclaw_confirmation",
    "safe_to_dry_run_inertly_confirmation",
)

PROHIBITED_LIVE_FIELDS: tuple[str, ...] = (
    "todoist_task_id",
    "todoist_id",
    "todoist_url",
    "todoist_project_id",
    "live_todoist_task_id",
    "live_todoist_id",
    "live_api_field",
    "live_api_config",
    "live_object_id",
    "external_object_id",
    "external_id",
    "api_config",
    "api_url",
)

PROHIBITED_SECRET_FIELDS: tuple[str, ...] = (
    "credential",
    "credentials",
    "credential_label",
    "credential_path",
    "oauth",
    "oauth_file",
    "oauth_token",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "todoist_api_token",
    "secret",
    "client_secret",
)

PROHIBITED_APPROVAL_FIELDS: tuple[str, ...] = (
    "selected",
    "approved",
    "authorized",
    "candidate_selected",
    "candidate_approved",
    "candidate_authorized",
    "pilot_approved",
    "pilot_authorized",
    "live_pilot_authorized",
    "live_authorized",
    "live_pilot_run",
    "pilot_run",
)

PROHIBITED_DEPENDENCY_FIELDS: tuple[str, ...] = (
    "requires_scheduler",
    "scheduler_required",
    "requires_background",
    "background_required",
    "requires_daemon",
    "daemon_required",
    "requires_launchagent",
    "launchagent_required",
    "requires_crontab",
    "crontab_required",
    "requires_openclaw",
    "openclaw_required",
    "requires_protected_path",
    "protected_path_required",
    "protected_path_interaction",
    "protected_path",
    "protected_paths",
    "requires_gmail",
    "gmail_required",
    "requires_calendar",
    "calendar_required",
    "external_dependency",
    "external_service_dependency",
)

HIGH_STAKES_DOMAINS: tuple[str, ...] = (
    "legal",
    "tax",
    "estate",
    "medical",
    "health",
    "investment",
    "portfolio",
    "crypto",
    "trading",
    "financial_execution",
    "relationship",
    "family_sensitive",
    "external_message",
    "external_meeting",
    "large_financial_commitment",
)


@dataclass(frozen=True)
class CandidateSelectionValidation:
    status: PilotPrepStatus
    accepted_for_human_review: bool
    candidate_label: str | None
    reasons: tuple[str, ...]
    normalized_candidate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "accepted_for_human_review": self.accepted_for_human_review,
            "candidate_label": self.candidate_label,
            "reasons": list(self.reasons),
            "normalized_candidate": self.normalized_candidate,
        }


def blank_phase14_candidate_selection_template() -> dict[str, Any]:
    """Return an inert human-fillable template with fail-closed defaults."""
    return {
        "schema_version": PHASE14_CANDIDATE_SELECTION_SCHEMA_VERSION,
        "packet_name": PACKET_NAME,
        "candidate_label": "",
        "routine_task_description": "",
        "intended_future_window": "",
        "self_only_reason": "",
        "low_risk_reason": "",
        "foreground_only_reason": "",
        "future_only_reason": "",
        "no_sensitive_domain_confirmation": False,
        "no_external_dependency_confirmation": False,
        "no_gmail_or_calendar_dependency_confirmation": False,
        "no_credentials_or_live_ids_confirmation": False,
        "no_protected_path_interaction_confirmation": False,
        "no_scheduler_background_or_openclaw_confirmation": False,
        "safe_to_dry_run_inertly_confirmation": False,
        "abort_criteria": "",
        "evidence_required_before_live_authorization": "",
        "selected": False,
        "approved": False,
        "authorized": False,
        "live_pilot_run": False,
        "readiness.status": "not_ready",
    }


def build_phase14_candidate_selection_report(
    candidate_records: Sequence[Mapping[str, Any]] | None = None,
    *,
    generated_at_utc: str = "2026-06-20T00:00:00+00:00",
) -> dict[str, Any]:
    """Build an inert decision artifact for later human candidate selection."""
    candidates = tuple(candidate_records or ())
    validations = tuple(validate_phase14_candidate_selection_candidate(candidate) for candidate in candidates)
    accepted = tuple(validation for validation in validations if validation.accepted_for_human_review)
    status, proposed_candidate, reasons = _selection_report_result(
        candidates=candidates,
        validations=validations,
        accepted=accepted,
    )

    return {
        "schema_version": PHASE14_CANDIDATE_SELECTION_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "packet_name": PACKET_NAME,
        "phase_label": PHASE_LABEL,
        "status": status.value,
        "candidate_selected": False,
        "selected_candidate": None,
        "candidate_proposed_for_human_review": proposed_candidate,
        "candidate_approved": False,
        "candidate_authorized": False,
        "live_pilot_authorized": False,
        "live_pilot_run": False,
        "phase14_c_blocked": True,
        "selection_is_not_live_authorization": True,
        "activation_requires_later_packet": True,
        "phase13e_d_synthetic_todoist_fixture_rejected": True,
        "todoist_touched": False,
        "external_services_contacted": False,
        "external_mutation": False,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "minimum_candidate_criteria": _minimum_candidate_criteria(),
        "human_decision_needed": _human_decision_needed(status, proposed_candidate),
        "reasons": reasons,
        "candidate_validations": [validation.to_dict() for validation in validations],
        "candidate_template": blank_phase14_candidate_selection_template(),
        "preflight_checklist": render_phase14_candidate_selection_checklist(
            status=status,
            reasons=reasons,
        ),
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_phase14_candidate_selection_candidate(
    candidate: Mapping[str, Any] | None,
) -> CandidateSelectionValidation:
    """Validate a human-review candidate without selecting or authorizing it."""
    if candidate is None:
        return CandidateSelectionValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            accepted_for_human_review=False,
            candidate_label=None,
            reasons=("No candidate was supplied; human selection is required.",),
        )

    label = _candidate_label(candidate)
    blocked_reasons = _blocked_candidate_reasons(candidate)
    if blocked_reasons:
        return CandidateSelectionValidation(
            status=PilotPrepStatus.BLOCKED,
            accepted_for_human_review=False,
            candidate_label=label,
            reasons=tuple(blocked_reasons),
        )

    missing_reasons = _missing_candidate_reasons(candidate)
    if missing_reasons:
        return CandidateSelectionValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            accepted_for_human_review=False,
            candidate_label=label,
            reasons=tuple(missing_reasons),
        )

    normalized_candidate = {
        "candidate_label": label,
        "routine_task_description": str(candidate["routine_task_description"]).strip(),
        "intended_future_window": str(candidate["intended_future_window"]).strip(),
        "self_only_reason": str(candidate["self_only_reason"]).strip(),
        "low_risk_reason": str(candidate["low_risk_reason"]).strip(),
        "foreground_only_reason": str(candidate["foreground_only_reason"]).strip(),
        "future_only_reason": str(candidate["future_only_reason"]).strip(),
        "abort_criteria": str(candidate["abort_criteria"]).strip(),
        "evidence_required_before_live_authorization": str(
            candidate["evidence_required_before_live_authorization"]
        ).strip(),
        "proposed_only": True,
        "selected": False,
        "approved": False,
        "authorized": False,
        "live_pilot_run": False,
        "readiness.status": "not_ready",
    }
    return CandidateSelectionValidation(
        status=PilotPrepStatus.PROPOSED_ONLY,
        accepted_for_human_review=True,
        candidate_label=label,
        reasons=(
            "Candidate has the required inert selection fields.",
            "Candidate is Todoist routine-task oriented, self-only, low-risk, "
            "future-only, and foreground-only by explicit rationale.",
            "Candidate is proposed only; it is not selected, approved, authorized, or live.",
        ),
        normalized_candidate=normalized_candidate,
    )


def render_phase14_candidate_selection_checklist(
    *,
    status: PilotPrepStatus,
    reasons: Sequence[str],
) -> list[str]:
    return [
        f"Phase label: {PHASE_LABEL}",
        "No candidate is currently selected.",
        "Phase 13E-D synthetic Todoist fixture remains rejected.",
        "Phase 14-C remains blocked.",
        "Candidate selection does not equal live authorization.",
        "Candidate approval and live activation approval are separate decisions.",
        "Live activation requires a later explicit packet.",
        f"Selection preparation status: {status.value}",
        "readiness.status remains not_ready.",
        "Todoist credentials, live IDs, API clients, and API configuration are absent.",
        "Gmail, Calendar, protected paths, scheduler/background work, OpenClaw, "
        "production DB, external writes, and live model/API rails remain blocked.",
        "Decision reasons: " + "; ".join(reasons),
    ]


def _selection_report_result(
    *,
    candidates: Sequence[Mapping[str, Any]],
    validations: Sequence[CandidateSelectionValidation],
    accepted: Sequence[CandidateSelectionValidation],
) -> tuple[PilotPrepStatus, dict[str, Any] | None, list[str]]:
    if not candidates:
        return (
            PilotPrepStatus.DECISION_NEEDED,
            None,
            [
                "No candidate records were supplied.",
                "Chris must later select exactly one candidate or decide none is ready.",
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

    if len(accepted) == 1 and len(candidates) == 1:
        return (
            PilotPrepStatus.PROPOSED_ONLY,
            dict(accepted[0].normalized_candidate or {}),
            list(accepted[0].reasons),
        )

    if len(candidates) > 1:
        return (
            PilotPrepStatus.DECISION_NEEDED,
            None,
            [
                "Multiple candidate records were supplied.",
                "This prep packet cannot auto-select between candidates.",
            ],
        )

    return (
        PilotPrepStatus.DECISION_NEEDED,
        None,
        _dedupe(reason for validation in validations for reason in validation.reasons),
    )


def _blocked_candidate_reasons(candidate: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    flattened = tuple(_flatten_mapping(candidate))
    keys = {_normalize(key) for key, _value in flattened}

    for field in PROHIBITED_LIVE_FIELDS:
        if _field_present(flattened, field):
            reasons.append(f"Candidate contains prohibited live Todoist/API field: {field}.")

    for field in PROHIBITED_SECRET_FIELDS:
        if _field_present(flattened, field):
            reasons.append(f"Candidate contains prohibited credential/secret field: {field}.")

    for field in PROHIBITED_APPROVAL_FIELDS:
        if _field_truthy(flattened, field):
            reasons.append(
                f"Candidate is marked {field}; this packet cannot select, approve, "
                "authorize, or run a pilot."
            )

    for field in PROHIBITED_DEPENDENCY_FIELDS:
        if _field_present_or_truthy(flattened, field):
            reasons.append(
                f"Candidate declares prohibited dependency or boundary crossing: {field}."
            )

    if _field_truthy(flattened, "high_stakes") or _field_truthy(flattened, "sensitive_domain"):
        reasons.append("Candidate is marked high-stakes or sensitive.")

    for field in ("domain", "risk_domain", "sensitive_category"):
        value = _first_field_value(flattened, field)
        if _normalize(value) in HIGH_STAKES_DOMAINS:
            reasons.append(f"Candidate domain is prohibited for first selection: {value}.")

    if "live_write" in keys and _field_truthy(flattened, "live_write"):
        reasons.append("Candidate claims live_write=true; live authorization is blocked.")

    return _dedupe(reasons)


def _missing_candidate_reasons(candidate: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for field in REQUIRED_TEXT_FIELDS:
        if not _present(candidate.get(field)):
            reasons.append(f"Candidate required field is missing: {field}.")
    for field in REQUIRED_CONFIRMATION_FIELDS:
        if not _truthy(candidate.get(field)):
            reasons.append(f"Candidate required confirmation is missing or false: {field}.")
    if candidate.get("readiness.status") != "not_ready":
        reasons.append("Candidate template must keep readiness.status=not_ready.")
    return reasons


def _minimum_candidate_criteria() -> list[str]:
    return [
        "Todoist routine-task oriented.",
        "Self-only.",
        "Low-risk.",
        "Future-only.",
        "Foreground-only.",
        "No sensitive or high-stakes domain.",
        "No external dependency.",
        "No Gmail or Calendar dependency.",
        "No protected path interaction.",
        "No credentials, tokens, OAuth material, API keys, or real live Todoist IDs.",
        "No scheduler or background requirement.",
        "No OpenClaw requirement.",
        "Safe to dry-run inertly.",
    ]


def _human_decision_needed(
    status: PilotPrepStatus,
    proposed_candidate: Mapping[str, Any] | None,
) -> str:
    if proposed_candidate is not None:
        return (
            "Chris may later select this one proposed-only candidate or decide no "
            "candidate is ready; either choice requires a separate packet."
        )
    if status is PilotPrepStatus.BLOCKED:
        return (
            "Candidate input is blocked; Chris must reject it or provide a new inert "
            "candidate-selection artifact."
        )
    return "Chris must later select exactly one candidate or decide no candidate is ready."


def _candidate_label(candidate: Mapping[str, Any]) -> str | None:
    value = candidate.get("candidate_label")
    if _present(value):
        return str(value).strip()
    return None


def _flatten_mapping(mapping: Mapping[str, Any], prefix: str = "") -> Iterable[tuple[str, Any]]:
    for key, value in mapping.items():
        key_text = str(key)
        path = f"{prefix}.{key_text}" if prefix else key_text
        yield path, value
        if isinstance(value, Mapping):
            yield from _flatten_mapping(value, path)


def _field_present(flattened: Sequence[tuple[str, Any]], field: str) -> bool:
    normalized_field = _normalize(field)
    return any(_normalize(_leaf_key(key)) == normalized_field and _present(value) for key, value in flattened)


def _field_truthy(flattened: Sequence[tuple[str, Any]], field: str) -> bool:
    normalized_field = _normalize(field)
    return any(_normalize(_leaf_key(key)) == normalized_field and _truthy(value) for key, value in flattened)


def _field_present_or_truthy(flattened: Sequence[tuple[str, Any]], field: str) -> bool:
    normalized_field = _normalize(field)
    for key, value in flattened:
        if _normalize(_leaf_key(key)) != normalized_field:
            continue
        if isinstance(value, bool):
            return value
        if _present(value):
            return True
    return False


def _first_field_value(flattened: Sequence[tuple[str, Any]], field: str) -> Any:
    normalized_field = _normalize(field)
    for key, value in flattened:
        if _normalize(_leaf_key(key)) == normalized_field:
            return value
    return None


def _leaf_key(path: str) -> str:
    return path.rsplit(".", 1)[-1]


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
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped

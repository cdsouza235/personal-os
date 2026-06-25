"""Inert Phase 14-C candidate decision-support record helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from personalos.phase14_candidate_selection_prep import (
    CANDIDATE_REVIEW_TRACKING_STATUS,
    phase14_cleaning_candidate_review_tracking_record,
)
from personalos.phase14_pilot_prep import SAFETY_POSTURE, PilotPrepStatus


PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION = "phase14c_candidate_decision_support.v1"
PHASE14C_DECISION_SUPPORT_CONTRACT_SCHEMA_VERSION = (
    "phase14c_candidate_decision_support_contract.v1"
)
PHASE_LABEL = "Phase 14-C candidate decision support validator"
RECORDED_CANDIDATE = "Clean Kitchen Countertops and Stovetop"
RECORDED_WEEKDAY = "Monday"
RECORDED_AREA = "Kitchen"
CURRENT_STATUS = "candidate-review tracking only"
DECISION_STATUS_UNFILLED = "unfilled"
DECISION_OPTION_UNSELECTED = "unselected"

REQUIRED_FALSE_FIELDS: tuple[str, ...] = (
    "approval_wording_provided",
    "evidence_review_complete",
    "manual_validation_complete",
    "phase14_c_approved",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "candidate_execution_authorized",
    "live_rails_activated",
    "todoist_access_authorized",
    "todoist_write_authorized",
    "gmail_access_authorized",
    "gmail_write_authorized",
    "calendar_access_authorized",
    "calendar_write_authorized",
    "openclaw_authorized",
    "credentials_auth_handling_authorized",
    "production_db_activation_authorized",
    "scheduler_background_activation_authorized",
    "protected_path_access_authorized",
    "external_writes_authorized",
    "live_model_api_calls_authorized",
    "dynamic_cleaning_authorized",
    "fifteen_task_import_authorized",
    "skip_push_bump_behavior_authorized",
    "automatic_rescheduling_authorized",
    "watch_tower_adoption_authorized",
    "agent_directory_authorized",
    "claude_md_authorized",
    "runtime_operator_scaffolding_authorized",
)

REQUIRED_TEXT_DEFAULTS: dict[str, str] = {
    "schema_version": PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
    "decision_status": DECISION_STATUS_UNFILLED,
    "decision_option": DECISION_OPTION_UNSELECTED,
    "candidate": RECORDED_CANDIDATE,
    "weekday": RECORDED_WEEKDAY,
    "area": RECORDED_AREA,
    "current_status": CURRENT_STATUS,
}

FILLABLE_DECISION_FIELDS: tuple[str, ...] = (
    "decision_date",
    "decision_maker",
    "future_packet_scope",
    "manual_validation_expected",
    "remaining_separate_gates",
    "stop_conditions_reviewed",
    "notes",
)

KNOWN_DECISION_RECORD_FIELDS: frozenset[str] = frozenset(
    (
        *REQUIRED_TEXT_DEFAULTS.keys(),
        *REQUIRED_FALSE_FIELDS,
        *FILLABLE_DECISION_FIELDS,
        "readiness.status",
    )
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

REPORT_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "decision_record_validated_as_unfilled",
    "human_decision_recorded",
    "decision_option_selected",
    "decision_option",
    "candidate_review_tracking_only",
    "candidate_review_tracking",
    "phase14_c_blocked",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "candidate_execution_authorized",
    "live_pilot_authorized",
    "live_pilot_run",
    "approval_to_merge_docs_is_not_live_authorization",
    "gmail_touched",
    "todoist_touched",
    "calendar_touched",
    "openclaw_called",
    "scheduler_activated",
    "background_loop_activated",
    "launch_agent_installed",
    "crontab_modified",
    "daemon_started",
    "credentials_loaded",
    "credentials_read",
    "production_db_path_active",
    "personalos_markdown_written",
    "protected_paths_touched",
    "live_model_api_called",
    "watch_tower_adopted_or_merged",
    "agent_directory_created",
    "claude_md_created",
    "runtime_operator_scaffolding_created",
    "external_services_contacted",
    "external_mutation",
    "readiness",
    "decision_record_validation",
    "decision_record_template",
    "preflight_checklist",
    "safety_posture",
)

REPORT_INERT_FALSE_FIELDS: tuple[str, ...] = (
    "human_decision_recorded",
    "decision_option_selected",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "candidate_execution_authorized",
    "live_pilot_authorized",
    "live_pilot_run",
    "gmail_touched",
    "todoist_touched",
    "calendar_touched",
    "openclaw_called",
    "scheduler_activated",
    "background_loop_activated",
    "launch_agent_installed",
    "crontab_modified",
    "daemon_started",
    "credentials_loaded",
    "credentials_read",
    "production_db_path_active",
    "personalos_markdown_written",
    "protected_paths_touched",
    "live_model_api_called",
    "watch_tower_adopted_or_merged",
    "agent_directory_created",
    "claude_md_created",
    "runtime_operator_scaffolding_created",
    "external_services_contacted",
    "external_mutation",
)

REPORT_INERT_TRUE_FIELD_PATHS: tuple[str, ...] = (
    "candidate_review_tracking_only",
    "phase14_c_blocked",
    "approval_to_merge_docs_is_not_live_authorization",
    "candidate_review_tracking.exactly_one_candidate_recorded",
    "candidate_review_tracking.candidate.review_tracking_only",
    "readiness.inert_report_only",
)

REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT: tuple[str, ...] = (
    "raw_decision_record",
    "input_record",
    "unsafe_input",
)

ALLOWED_VALIDATION_STATUS_VALUES: tuple[str, ...] = (
    PilotPrepStatus.DECISION_NEEDED.value,
    PilotPrepStatus.BLOCKED.value,
)


@dataclass(frozen=True)
class CandidateDecisionSupportValidation:
    status: PilotPrepStatus
    record_accepted_as_unfilled_template: bool
    human_decision_recorded: bool
    reasons: tuple[str, ...]
    normalized_record: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "record_accepted_as_unfilled_template": (
                self.record_accepted_as_unfilled_template
            ),
            "human_decision_recorded": self.human_decision_recorded,
            "reasons": list(self.reasons),
            "normalized_record": self.normalized_record,
        }


def blank_phase14c_candidate_decision_support_record() -> dict[str, Any]:
    """Return the inert false-default decision-record template."""
    return {
        "schema_version": PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
        "decision_status": DECISION_STATUS_UNFILLED,
        "decision_option": DECISION_OPTION_UNSELECTED,
        "decision_date": "",
        "decision_maker": "",
        "candidate": RECORDED_CANDIDATE,
        "weekday": RECORDED_WEEKDAY,
        "area": RECORDED_AREA,
        "current_status": CURRENT_STATUS,
        "readiness.status": "not_ready",
        "approval_wording_provided": False,
        "evidence_review_complete": False,
        "manual_validation_complete": False,
        "phase14_c_approved": False,
        "candidate_approved": False,
        "candidate_authorized": False,
        "candidate_activated": False,
        "candidate_run": False,
        "candidate_execution_authorized": False,
        "live_rails_activated": False,
        "todoist_access_authorized": False,
        "todoist_write_authorized": False,
        "gmail_access_authorized": False,
        "gmail_write_authorized": False,
        "calendar_access_authorized": False,
        "calendar_write_authorized": False,
        "openclaw_authorized": False,
        "credentials_auth_handling_authorized": False,
        "production_db_activation_authorized": False,
        "scheduler_background_activation_authorized": False,
        "protected_path_access_authorized": False,
        "external_writes_authorized": False,
        "live_model_api_calls_authorized": False,
        "dynamic_cleaning_authorized": False,
        "fifteen_task_import_authorized": False,
        "skip_push_bump_behavior_authorized": False,
        "automatic_rescheduling_authorized": False,
        "watch_tower_adoption_authorized": False,
        "agent_directory_authorized": False,
        "claude_md_authorized": False,
        "runtime_operator_scaffolding_authorized": False,
        "future_packet_scope": "",
        "manual_validation_expected": "",
        "remaining_separate_gates": "",
        "stop_conditions_reviewed": "",
        "notes": "",
    }


def build_phase14c_candidate_decision_support_report(
    decision_record: Mapping[str, Any] | None = None,
    *,
    generated_at_utc: str = "2026-06-25T00:00:00+00:00",
) -> dict[str, Any]:
    """Build an inert report for the unfilled decision-support record.

    The returned report is a repository-local validation artifact only. It
    does not select a decision option, create clients, read credentials, open
    production state, contact Todoist/Gmail/Calendar, or write external state.
    """
    record = (
        blank_phase14c_candidate_decision_support_record()
        if decision_record is None
        else decision_record
    )
    validation = validate_phase14c_candidate_decision_record(record)
    candidate_record = phase14_cleaning_candidate_review_tracking_record()

    return {
        "schema_version": PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "phase_label": PHASE_LABEL,
        "status": validation.status.value,
        "decision_record_validated_as_unfilled": (
            validation.record_accepted_as_unfilled_template
        ),
        "human_decision_recorded": False,
        "decision_option_selected": False,
        "decision_option": DECISION_OPTION_UNSELECTED,
        "candidate_review_tracking_only": True,
        "candidate_review_tracking": {
            "status": CANDIDATE_REVIEW_TRACKING_STATUS,
            "candidate_count": 1,
            "exactly_one_candidate_recorded": True,
            "candidate": {
                "candidate_name": candidate_record["candidate_name"],
                "task_title": candidate_record["task_title"],
                "weekday": candidate_record["weekday"],
                "home_area": candidate_record["home_area"],
                "candidate_type": candidate_record["candidate_type"],
                "candidate_scope": candidate_record["candidate_scope"],
                "candidate_review_tracking_status": (
                    candidate_record["candidate_review_tracking_status"]
                ),
                "review_tracking_only": True,
                "selected": False,
                "approved": False,
                "authorized": False,
                "live_pilot_run": False,
            },
        },
        "phase14_c_blocked": True,
        "candidate_approved": False,
        "candidate_authorized": False,
        "candidate_activated": False,
        "candidate_run": False,
        "candidate_execution_authorized": False,
        "live_pilot_authorized": False,
        "live_pilot_run": False,
        "approval_to_merge_docs_is_not_live_authorization": True,
        "gmail_touched": False,
        "todoist_touched": False,
        "calendar_touched": False,
        "openclaw_called": False,
        "scheduler_activated": False,
        "background_loop_activated": False,
        "launch_agent_installed": False,
        "crontab_modified": False,
        "daemon_started": False,
        "credentials_loaded": False,
        "credentials_read": False,
        "production_db_path_active": False,
        "personalos_markdown_written": False,
        "protected_paths_touched": False,
        "live_model_api_called": False,
        "watch_tower_adopted_or_merged": False,
        "agent_directory_created": False,
        "claude_md_created": False,
        "runtime_operator_scaffolding_created": False,
        "external_services_contacted": False,
        "external_mutation": False,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "decision_record_validation": validation.to_dict(),
        "decision_record_template": blank_phase14c_candidate_decision_support_record(),
        "preflight_checklist": render_phase14c_candidate_decision_support_checklist(
            status=validation.status,
            reasons=validation.reasons,
        ),
        "safety_posture": dict(SAFETY_POSTURE),
    }


def build_phase14c_candidate_decision_support_contract_manifest() -> dict[str, Any]:
    """Return the inert schema/report contract used by audits and tests."""
    return {
        "schema_version": PHASE14C_DECISION_SUPPORT_CONTRACT_SCHEMA_VERSION,
        "decision_support_schema_version": PHASE14C_DECISION_SUPPORT_SCHEMA_VERSION,
        "phase_label": PHASE_LABEL,
        "allowed_validation_statuses": list(ALLOWED_VALIDATION_STATUS_VALUES),
        "decision_record_schema": {
            "known_fields": sorted(KNOWN_DECISION_RECORD_FIELDS),
            "required_text_defaults": dict(REQUIRED_TEXT_DEFAULTS),
            "required_false_fields": list(REQUIRED_FALSE_FIELDS),
            "fillable_decision_fields": list(FILLABLE_DECISION_FIELDS),
            "readiness_status_field": "readiness.status",
            "readiness_status_required_value": "not_ready",
            "raw_input_echo_fields_absent": list(REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT),
        },
        "blocked_field_groups": {
            "required_false_fields": list(REQUIRED_FALSE_FIELDS),
            "fillable_decision_fields": list(FILLABLE_DECISION_FIELDS),
            "prohibited_live_fields": list(PROHIBITED_LIVE_FIELDS),
            "prohibited_secret_fields": list(PROHIBITED_SECRET_FIELDS),
        },
        "report_contract": {
            "top_level_fields": list(REPORT_TOP_LEVEL_FIELDS),
            "inert_false_fields": list(REPORT_INERT_FALSE_FIELDS),
            "inert_true_field_paths": list(REPORT_INERT_TRUE_FIELD_PATHS),
            "raw_input_echo_fields_absent": list(REPORT_RAW_INPUT_ECHO_FIELDS_ABSENT),
        },
        "non_authorization_contract": {
            "candidate_review_tracking_only": True,
            "phase14_c_blocked": True,
            "readiness.status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
            "human_decision_recorded": False,
            "decision_option_selected": False,
            "candidate_approved": False,
            "candidate_authorized": False,
            "candidate_activated_or_run": False,
            "live_service_access_authorized": False,
            "credentials_auth_handling_authorized": False,
            "production_db_activation_authorized": False,
            "scheduler_background_activation_authorized": False,
            "openclaw_invocation_authorized": False,
            "protected_path_access_authorized": False,
            "runtime_operator_scaffolding_authorized": False,
        },
    }


def validate_phase14c_candidate_decision_record(
    decision_record: Mapping[str, Any] | None,
) -> CandidateDecisionSupportValidation:
    """Validate a decision-support record without recording a human decision."""
    if decision_record is None:
        return CandidateDecisionSupportValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            record_accepted_as_unfilled_template=False,
            human_decision_recorded=False,
            reasons=(
                "No decision-support record was supplied; the false-default "
                "template remains required.",
            ),
        )

    blocked_reasons = _blocked_decision_record_reasons(decision_record)
    if blocked_reasons:
        return CandidateDecisionSupportValidation(
            status=PilotPrepStatus.BLOCKED,
            record_accepted_as_unfilled_template=False,
            human_decision_recorded=_human_decision_appears_recorded(decision_record),
            reasons=tuple(blocked_reasons),
        )

    missing_reasons = _missing_decision_record_reasons(decision_record)
    if missing_reasons:
        return CandidateDecisionSupportValidation(
            status=PilotPrepStatus.DECISION_NEEDED,
            record_accepted_as_unfilled_template=False,
            human_decision_recorded=False,
            reasons=tuple(missing_reasons),
        )

    normalized = {
        **REQUIRED_TEXT_DEFAULTS,
        **{field: False for field in REQUIRED_FALSE_FIELDS},
        **{field: "" for field in FILLABLE_DECISION_FIELDS},
        "phase14_c_blocked": True,
        "candidate_review_tracking_only": True,
        "human_decision_recorded": False,
        "readiness.status": "not_ready",
    }
    return CandidateDecisionSupportValidation(
        status=PilotPrepStatus.DECISION_NEEDED,
        record_accepted_as_unfilled_template=True,
        human_decision_recorded=False,
        reasons=(
            "Decision-support record remains unfilled.",
            "Decision option remains unselected.",
            "All approval, authorization, activation, execution, and live-service "
            "fields remain false.",
            "Phase 14-C remains blocked and readiness.status remains not_ready.",
        ),
        normalized_record=normalized,
    )


def render_phase14c_candidate_decision_support_checklist(
    *,
    status: PilotPrepStatus,
    reasons: Sequence[str],
) -> list[str]:
    return [
        f"Phase label: {PHASE_LABEL}",
        "Decision record is unfilled by default.",
        "Decision option remains unselected.",
        "Candidate remains Clean Kitchen Countertops and Stovetop.",
        "Candidate-review tracking only remains the current state.",
        "No approve, reject, or defer decision is recorded.",
        "Phase 14-C remains blocked.",
        "Candidate is not approved, authorized, activated, or run.",
        "Todoist, Gmail, Calendar, OpenClaw, credentials, production DB, "
        "scheduler/background, protected paths, external writes, live model/API, "
        "dynamic cleaning, Watch Tower, .agent, CLAUDE.md, and runtime/operator "
        "scaffolding remain blocked.",
        f"Decision-support status: {status.value}",
        "Validation reasons: " + "; ".join(reasons),
    ]


def _blocked_decision_record_reasons(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    flattened = tuple(_flatten_mapping(record))

    if _unknown_schema_fields(record):
        reasons.append(
            "Decision record contains unknown schema fields; only the "
            "false-default template schema is accepted."
        )

    for field in REQUIRED_FALSE_FIELDS:
        if _field_truthy(flattened, field):
            reasons.append(
                f"Decision record is marked {field}; this packet cannot approve, "
                "authorize, activate, execute, or grant live access."
            )
        elif field in record and record[field] is not False:
            reasons.append(
                f"Decision record changes {field}; expected boolean false."
            )

    for field in FILLABLE_DECISION_FIELDS:
        if (
            field in record
            and record[field] != ""
            and not _field_present(flattened, field)
        ):
            reasons.append(
                f"Decision record changes {field}; expected an empty unfilled value."
            )
        if _field_present(flattened, field):
            reasons.append(
                f"Decision record fills {field}; recording a human decision is out of scope."
            )

    for field in PROHIBITED_LIVE_FIELDS:
        if _field_present(flattened, field):
            reasons.append(f"Decision record contains prohibited live/API field: {field}.")

    for field in PROHIBITED_SECRET_FIELDS:
        if _field_present(flattened, field):
            reasons.append(
                f"Decision record contains prohibited credential/secret field: {field}."
            )

    decision_status = record.get("decision_status")
    if _present(decision_status) and _normalize(decision_status) != DECISION_STATUS_UNFILLED:
        reasons.append(
            "Decision record selects decision_status; this packet cannot record a "
            "human decision."
        )

    decision_option = record.get("decision_option")
    if _present(decision_option) and _normalize(decision_option) != DECISION_OPTION_UNSELECTED:
        reasons.append(
            "Decision record selects decision_option; this packet cannot select "
            "approve, reject, or defer."
        )

    for field, expected in REQUIRED_TEXT_DEFAULTS.items():
        value = record.get(field)
        if not _present(value):
            continue
        if value != expected:
            reasons.append(
                f"Decision record changes {field}; expected the unfilled false-default "
                "template value."
            )

    readiness_status = record.get("readiness.status")
    if _present(readiness_status) and readiness_status != "not_ready":
        reasons.append("Decision record changes readiness.status; expected 'not_ready'.")

    return _dedupe(reasons)


def _unknown_schema_fields(record: Mapping[str, Any]) -> list[str]:
    return [
        str(key)
        for key in record
        if str(key) not in KNOWN_DECISION_RECORD_FIELDS
    ]


def _missing_decision_record_reasons(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for field, expected in REQUIRED_TEXT_DEFAULTS.items():
        if not _present(record.get(field)):
            reasons.append(
                f"Decision-support record required field is missing: {field}={expected}."
            )
    for field in REQUIRED_FALSE_FIELDS:
        if field not in record:
            reasons.append(
                f"Decision-support record required false field is missing: {field}."
            )
    for field in FILLABLE_DECISION_FIELDS:
        if field not in record:
            reasons.append(
                f"Decision-support record required unfilled field is missing: {field}."
            )
    if not _present(record.get("readiness.status")):
        reasons.append(
            "Decision-support record required field is missing: "
            "readiness.status=not_ready."
        )
    return reasons


def _human_decision_appears_recorded(record: Mapping[str, Any]) -> bool:
    flattened = tuple(_flatten_mapping(record))
    if any(_field_present(flattened, field) for field in FILLABLE_DECISION_FIELDS):
        return True
    if _field_present(flattened, "decision_date") or _field_present(flattened, "decision_maker"):
        return True
    decision_status = record.get("decision_status")
    decision_option = record.get("decision_option")
    return (
        _present(decision_status)
        and _normalize(decision_status) != DECISION_STATUS_UNFILLED
    ) or (
        _present(decision_option)
        and _normalize(decision_option) != DECISION_OPTION_UNSELECTED
    )


def _flatten_mapping(mapping: Mapping[str, Any], prefix: str = "") -> Iterable[tuple[str, Any]]:
    for key, value in mapping.items():
        key_text = str(key)
        path = f"{prefix}.{key_text}" if prefix else key_text
        yield path, value
        if isinstance(value, Mapping):
            yield from _flatten_mapping(value, path)


def _field_present(flattened: Sequence[tuple[str, Any]], field: str) -> bool:
    normalized_field = _normalize(field)
    return any(
        _normalize(_leaf_key(key)) == normalized_field and _present(value)
        for key, value in flattened
    )


def _field_truthy(flattened: Sequence[tuple[str, Any]], field: str) -> bool:
    normalized_field = _normalize(field)
    return any(
        _normalize(_leaf_key(key)) == normalized_field and _truthy(value)
        for key, value in flattened
    )


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

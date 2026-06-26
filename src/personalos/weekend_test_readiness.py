"""Inert weekend test readiness runbook report helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from personalos.nonhuman_closure import (
    BLOCKED_LIVE_RAILS,
    HUMAN_REQUIRED_GATES,
    build_nonhuman_closure_plan_report,
    validate_nonhuman_closure_plan_report_contract,
)
from personalos.phase14_pilot_prep import SAFETY_POSTURE


WEEKEND_TEST_READINESS_SCHEMA_VERSION = "personal_os_weekend_test_readiness.v1"
WEEKEND_TEST_READINESS_PHASE_LABEL = "Personal OS weekend test readiness runbook"
WEEKEND_TEST_READINESS_STATUS = "test_plan_recorded_not_live"
WEEKEND_TEST_READINESS_DEFAULT_GENERATED_AT_UTC = "2026-06-26T02:15:00+00:00"

WEEKEND_TEST_READINESS_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "weekend_testing_started",
    "live_testing_authorized",
    "live_mvp_ready",
    "human_gates_remaining",
    "inert_report_only",
    "readiness",
    "source_documents",
    "nonhuman_closure",
    "manual_test_categories",
    "evidence_templates",
    "no_go_criteria",
    "rollback_rehearsal_templates",
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

NONHUMAN_CLOSURE_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "contract_valid",
    "nonhuman_closure_complete",
    "human_gates_remaining",
    "live_mvp_ready",
    "accelerated_packet_model_recorded",
    "current_packet_id",
)

MANUAL_TEST_CATEGORY_FIELDS: tuple[str, ...] = (
    "category_id",
    "label",
    "source_document",
    "objective",
    "evidence_required",
    "allowed_surface",
    "contains_human_decision",
    "contains_live_access",
    "credentials_required",
    "production_db_required",
    "scheduler_required",
    "openclaw_required",
)

EVIDENCE_TEMPLATE_FIELDS: tuple[str, ...] = (
    "template_id",
    "label",
    "required_fields",
    "captures_secret_values",
    "records_live_object_ids",
    "authorizes_live_access",
)

ROLLBACK_REHEARSAL_TEMPLATE_FIELDS: tuple[str, ...] = (
    "template_id",
    "rail",
    "rehearsal_only",
    "live_action_authorized",
    "required_fields",
)

SOURCE_DOCUMENTS: tuple[str, ...] = (
    "docs/PRE_LIVE_READINESS.md",
    "docs/ACTIVATION_CHECKLIST.md",
    "docs/FIRST_LIVE_PILOT_PROTOCOL.md",
    "docs/LIVE_RAIL_ACTIVATION_POLICY.md",
    "docs/OPERATOR_HANDOFF_CONTRACT.md",
    "docs/NON_HUMAN_CLOSURE_PLAN.md",
)

MANUAL_TEST_CATEGORIES: tuple[dict[str, Any], ...] = (
    {
        "category_id": "repo_validation_capture",
        "label": "Repo validation capture",
        "source_document": "docs/PRE_LIVE_READINESS.md",
        "objective": "record local test, ResourceWarning, diff, and artifact hygiene results",
        "evidence_required": True,
        "allowed_surface": "repo-local validation commands only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "readiness_status_capture",
        "label": "Readiness status capture",
        "source_document": "docs/PRE_LIVE_READINESS.md",
        "objective": "record not_ready and inert_report_only status outputs for review",
        "evidence_required": True,
        "allowed_surface": "read-only readiness/status commands only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "activation_checklist_review",
        "label": "Activation checklist review",
        "source_document": "docs/ACTIVATION_CHECKLIST.md",
        "objective": "identify missing activation evidence without completing the checklist",
        "evidence_required": True,
        "allowed_surface": "repo-local checklist review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "first_live_pilot_protocol_review",
        "label": "First-live pilot protocol review",
        "source_document": "docs/FIRST_LIVE_PILOT_PROTOCOL.md",
        "objective": "prepare pilot evidence expectations without selecting or running a pilot",
        "evidence_required": True,
        "allowed_surface": "repo-local protocol review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "live_rail_policy_review",
        "label": "Live rail policy review",
        "source_document": "docs/LIVE_RAIL_ACTIVATION_POLICY.md",
        "objective": "confirm selected-rail requirements remain blocked until human approval",
        "evidence_required": True,
        "allowed_surface": "repo-local policy review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "operator_handoff_boundary_review",
        "label": "Operator handoff boundary review",
        "source_document": "docs/OPERATOR_HANDOFF_CONTRACT.md",
        "objective": "verify any future handoff needs exact operator, inputs, outputs, and stop condition",
        "evidence_required": True,
        "allowed_surface": "repo-local handoff-template review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "no_go_and_halt_review",
        "label": "No-go and halt review",
        "source_document": "docs/FIRST_LIVE_PILOT_PROTOCOL.md",
        "objective": "record stop criteria that require preserving evidence and escalating",
        "evidence_required": True,
        "allowed_surface": "repo-local no-go criteria review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
    {
        "category_id": "rollback_tabletop_review",
        "label": "Rollback tabletop review",
        "source_document": "docs/FIRST_LIVE_PILOT_PROTOCOL.md",
        "objective": "prepare rail-specific rollback questions without performing rollback",
        "evidence_required": True,
        "allowed_surface": "repo-local rollback/recovery review only",
        "contains_human_decision": False,
        "contains_live_access": False,
        "credentials_required": False,
        "production_db_required": False,
        "scheduler_required": False,
        "openclaw_required": False,
    },
)

EVIDENCE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "template_id": "validation_evidence",
        "label": "Validation evidence",
        "required_fields": (
            "repo_commit",
            "full_suite_result",
            "resource_warning_suite_result",
            "diff_check_result",
            "artifact_scan_result",
        ),
        "captures_secret_values": False,
        "records_live_object_ids": False,
        "authorizes_live_access": False,
    },
    {
        "template_id": "readiness_evidence",
        "label": "Readiness evidence",
        "required_fields": (
            "readiness_status",
            "inert_report_only",
            "live_rails_activated",
            "credentials_loaded",
            "production_db_path_active",
            "scheduler_activated",
            "openclaw_called",
        ),
        "captures_secret_values": False,
        "records_live_object_ids": False,
        "authorizes_live_access": False,
    },
    {
        "template_id": "dry_run_preview_evidence",
        "label": "Dry-run preview evidence",
        "required_fields": (
            "input_reference",
            "selected_rail_label",
            "operation_label",
            "validation_result",
            "idempotency_key_label",
            "confirmation_of_no_external_write",
        ),
        "captures_secret_values": False,
        "records_live_object_ids": False,
        "authorizes_live_access": False,
    },
    {
        "template_id": "rollback_tabletop_evidence",
        "label": "Rollback tabletop evidence",
        "required_fields": (
            "rail_label",
            "undo_or_recovery_path",
            "verification_step",
            "known_irreversible_behavior",
            "escalation_path",
        ),
        "captures_secret_values": False,
        "records_live_object_ids": False,
        "authorizes_live_access": False,
    },
)

NO_GO_CRITERIA: tuple[str, ...] = (
    "readiness.status is anything other than not_ready before explicit live approval",
    "any live rail reports activated before approval",
    "any credential, OAuth token, API key, or secret handling is required",
    "any production DB path is needed or inferred",
    "any scheduler, LaunchAgent, crontab, daemon, watcher, or background loop is needed",
    "OpenClaw handoff or invocation is requested without a separate approved handoff",
    "protected path access is needed",
    "dry-run evidence is missing, stale, or uses different input than the proposed pilot",
    "rollback or recovery behavior is ambiguous",
    "go/no-go launch approval is missing",
)

ROLLBACK_REHEARSAL_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "template_id": "todoist_rollback_tabletop",
        "rail": "todoist",
        "rehearsal_only": True,
        "live_action_authorized": False,
        "required_fields": (
            "delete_or_close_path",
            "reopen_or_annotation_path",
            "verification_step",
            "stop_condition",
        ),
    },
    {
        "template_id": "calendar_rollback_tabletop",
        "rail": "google_calendar",
        "rehearsal_only": True,
        "live_action_authorized": False,
        "required_fields": (
            "delete_cancel_or_update_path",
            "calendar_label",
            "verification_step",
            "stop_condition",
        ),
    },
    {
        "template_id": "gmail_draft_recovery_tabletop",
        "rail": "gmail",
        "rehearsal_only": True,
        "live_action_authorized": False,
        "required_fields": (
            "draft_delete_path",
            "sent_message_irreversibility_note",
            "verification_step",
            "escalation_path",
        ),
    },
    {
        "template_id": "production_db_restore_tabletop",
        "rail": "production_db",
        "rehearsal_only": True,
        "live_action_authorized": False,
        "required_fields": (
            "backup_label",
            "restore_test_label",
            "integrity_check_result",
            "rollback_condition",
        ),
    },
)

NON_AUTHORIZATION_FIELDS: tuple[str, ...] = (
    "weekend_runbook_is_not_live_testing_authorization",
    "repo_merge_is_not_live_authorization",
    "phase14_c_authorized",
    "candidate_approved",
    "candidate_authorized",
    "candidate_activated",
    "candidate_run",
    "live_testing_authorized",
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

NON_AUTHORIZATION_TRUE_FIELDS: tuple[str, ...] = NON_AUTHORIZATION_FIELDS[:2]
NON_AUTHORIZATION_FALSE_FIELDS: tuple[str, ...] = NON_AUTHORIZATION_FIELDS[2:]


@dataclass(frozen=True)
class WeekendTestReadinessContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


def build_weekend_test_readiness_report() -> dict[str, Any]:
    """Build the inert weekend test readiness runbook report."""
    closure_report = build_nonhuman_closure_plan_report()
    closure_validation = validate_nonhuman_closure_plan_report_contract(
        closure_report
    )

    return {
        "schema_version": WEEKEND_TEST_READINESS_SCHEMA_VERSION,
        "generated_at_utc": WEEKEND_TEST_READINESS_DEFAULT_GENERATED_AT_UTC,
        "phase_label": WEEKEND_TEST_READINESS_PHASE_LABEL,
        "status": WEEKEND_TEST_READINESS_STATUS,
        "weekend_testing_started": False,
        "live_testing_authorized": False,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "inert_report_only": True,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "source_documents": list(SOURCE_DOCUMENTS),
        "nonhuman_closure": {
            "status": closure_report["status"],
            "contract_valid": closure_validation.report_matches_inert_contract,
            "nonhuman_closure_complete": closure_report[
                "nonhuman_closure_complete"
            ],
            "human_gates_remaining": closure_report["human_gates_remaining"],
            "live_mvp_ready": closure_report["live_mvp_ready"],
            "accelerated_packet_model_recorded": closure_report[
                "accelerated_packet_model_recorded"
            ],
            "current_packet_id": "packet_3_weekend_test_readiness_runbook",
        },
        "manual_test_categories": _materialize_records(MANUAL_TEST_CATEGORIES),
        "evidence_templates": _materialize_records(EVIDENCE_TEMPLATES),
        "no_go_criteria": list(NO_GO_CRITERIA),
        "rollback_rehearsal_templates": _materialize_records(
            ROLLBACK_REHEARSAL_TEMPLATES
        ),
        "human_required_gates": list(HUMAN_REQUIRED_GATES),
        "blocked_live_rails": list(BLOCKED_LIVE_RAILS),
        "non_authorization": {
            "weekend_runbook_is_not_live_testing_authorization": True,
            "repo_merge_is_not_live_authorization": True,
            **{field: False for field in NON_AUTHORIZATION_FALSE_FIELDS},
        },
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_weekend_test_readiness_report_contract(
    report: Mapping[str, Any] | None,
) -> WeekendTestReadinessContractValidation:
    """Validate the weekend test readiness runbook without authorizing testing."""
    if report is None:
        return WeekendTestReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=("No weekend test readiness report was supplied.",),
        )

    blocked_reasons = _blocked_weekend_readiness_reasons(report)
    if blocked_reasons:
        return WeekendTestReadinessContractValidation(
            report_matches_inert_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return WeekendTestReadinessContractValidation(
        report_matches_inert_contract=True,
        reasons=(
            "Weekend test readiness report remains inert and not live testing.",
        ),
    )


def _blocked_weekend_readiness_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != WEEKEND_TEST_READINESS_TOP_LEVEL_FIELDS:
        reasons.append(
            "Weekend test readiness report top-level fields do not match the contract."
        )

    if report.get("schema_version") != WEEKEND_TEST_READINESS_SCHEMA_VERSION:
        reasons.append(
            "Weekend test readiness report schema_version does not match the contract."
        )

    if report.get("generated_at_utc") != WEEKEND_TEST_READINESS_DEFAULT_GENERATED_AT_UTC:
        reasons.append(
            "Weekend test readiness report generated_at_utc does not match the contract."
        )

    if report.get("phase_label") != WEEKEND_TEST_READINESS_PHASE_LABEL:
        reasons.append(
            "Weekend test readiness report phase_label does not match the contract."
        )

    if report.get("status") != WEEKEND_TEST_READINESS_STATUS:
        reasons.append(
            "Weekend test readiness report status must remain test_plan_recorded_not_live."
        )

    expected_bools = {
        "weekend_testing_started": False,
        "live_testing_authorized": False,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "inert_report_only": True,
    }
    for field, expected in expected_bools.items():
        if report.get(field) is not expected:
            reasons.append(f"Weekend test readiness report field {field} drifted.")

    _check_readiness(report.get("readiness"), reasons)

    if report.get("source_documents") != list(SOURCE_DOCUMENTS):
        reasons.append("Weekend test readiness report source document list drifted.")

    _check_nonhuman_closure(report.get("nonhuman_closure"), reasons)
    _check_manual_test_categories(report.get("manual_test_categories"), reasons)
    _check_evidence_templates(report.get("evidence_templates"), reasons)

    if report.get("no_go_criteria") != list(NO_GO_CRITERIA):
        reasons.append("Weekend test readiness report no-go criteria drifted.")

    _check_rollback_templates(report.get("rollback_rehearsal_templates"), reasons)

    if report.get("human_required_gates") != list(HUMAN_REQUIRED_GATES):
        reasons.append("Weekend test readiness report human gate list drifted.")

    if report.get("blocked_live_rails") != list(BLOCKED_LIVE_RAILS):
        reasons.append("Weekend test readiness report blocked live rail list drifted.")

    _check_non_authorization(report.get("non_authorization"), reasons)

    if report.get("safety_posture") != dict(SAFETY_POSTURE):
        reasons.append(
            "Weekend test readiness report safety_posture does not match the contract."
        )

    return _dedupe(reasons)


def _check_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Weekend test readiness report readiness payload is missing.")
        return
    if tuple(value) != READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Weekend test readiness report readiness fields do not match the contract."
        )
    if value.get("status") != "not_ready":
        reasons.append(
            "Weekend test readiness report readiness.status must remain not_ready."
        )
    if value.get("inert_report_only") is not True:
        reasons.append(
            "Weekend test readiness report readiness.inert_report_only must remain true."
        )
    if value.get("live_rails_activated") is not False:
        reasons.append(
            "Weekend test readiness report readiness.live_rails_activated must remain false."
        )


def _check_nonhuman_closure(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append(
            "Weekend test readiness report non-human closure payload is missing."
        )
        return
    if tuple(value) != NONHUMAN_CLOSURE_PAYLOAD_FIELDS:
        reasons.append(
            "Weekend test readiness report non-human closure fields do not match the contract."
        )
    expected = {
        "status": "blocked_by_human_gates",
        "contract_valid": True,
        "nonhuman_closure_complete": False,
        "human_gates_remaining": True,
        "live_mvp_ready": False,
        "accelerated_packet_model_recorded": True,
        "current_packet_id": "packet_3_weekend_test_readiness_runbook",
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Weekend test readiness report non-human closure field {field} drifted."
            )


def _check_manual_test_categories(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(MANUAL_TEST_CATEGORIES):
        reasons.append("Weekend test readiness report manual test category list drifted.")
    if not isinstance(value, list):
        reasons.append(
            "Weekend test readiness report manual test category payload is missing."
        )
        return
    for category in value:
        if not isinstance(category, Mapping):
            reasons.append("Weekend test readiness report manual test category is malformed.")
            continue
        if tuple(category) != MANUAL_TEST_CATEGORY_FIELDS:
            reasons.append(
                "Weekend test readiness report manual test category fields do not match the contract."
            )
        if category.get("evidence_required") is not True:
            reasons.append(
                "Weekend test readiness report manual test evidence flag must remain true."
            )
        for field in (
            "contains_human_decision",
            "contains_live_access",
            "credentials_required",
            "production_db_required",
            "scheduler_required",
            "openclaw_required",
        ):
            if category.get(field) is not False:
                reasons.append(
                    f"Weekend test readiness report manual test field {field} must remain false."
                )


def _check_evidence_templates(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(EVIDENCE_TEMPLATES):
        reasons.append("Weekend test readiness report evidence template list drifted.")
    if not isinstance(value, list):
        reasons.append(
            "Weekend test readiness report evidence template payload is missing."
        )
        return
    for template in value:
        if not isinstance(template, Mapping):
            reasons.append("Weekend test readiness report evidence template is malformed.")
            continue
        if tuple(template) != EVIDENCE_TEMPLATE_FIELDS:
            reasons.append(
                "Weekend test readiness report evidence template fields do not match the contract."
            )
        for field in (
            "captures_secret_values",
            "records_live_object_ids",
            "authorizes_live_access",
        ):
            if template.get(field) is not False:
                reasons.append(
                    f"Weekend test readiness report evidence template field {field} must remain false."
                )


def _check_rollback_templates(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(ROLLBACK_REHEARSAL_TEMPLATES):
        reasons.append("Weekend test readiness report rollback template list drifted.")
    if not isinstance(value, list):
        reasons.append(
            "Weekend test readiness report rollback template payload is missing."
        )
        return
    for template in value:
        if not isinstance(template, Mapping):
            reasons.append("Weekend test readiness report rollback template is malformed.")
            continue
        if tuple(template) != ROLLBACK_REHEARSAL_TEMPLATE_FIELDS:
            reasons.append(
                "Weekend test readiness report rollback template fields do not match the contract."
            )
        if template.get("rehearsal_only") is not True:
            reasons.append(
                "Weekend test readiness report rollback rehearsal flag must remain true."
            )
        if template.get("live_action_authorized") is not False:
            reasons.append(
                "Weekend test readiness report rollback live-action flag must remain false."
            )


def _check_non_authorization(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append(
            "Weekend test readiness report non_authorization payload is missing."
        )
        return
    if tuple(value) != NON_AUTHORIZATION_FIELDS:
        reasons.append(
            "Weekend test readiness report non_authorization fields do not match the contract."
        )
    for field in NON_AUTHORIZATION_TRUE_FIELDS:
        if value.get(field) is not True:
            reasons.append(
                f"Weekend test readiness report non_authorization field {field} must remain true."
            )
    for field in NON_AUTHORIZATION_FALSE_FIELDS:
        if value.get(field) is not False:
            reasons.append(
                f"Weekend test readiness report non_authorization field {field} must remain false."
            )


def _materialize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_materialize_record(record) for record in records]


def _materialize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    materialized: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, tuple):
            materialized[key] = list(value)
        else:
            materialized[key] = value
    return materialized


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

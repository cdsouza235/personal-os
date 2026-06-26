"""Inert dry-run evidence bundle report helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from personalos.demo.fixtures import COMMAND_CONTRACT, DEMO_NAME, PHASE_NAME
from personalos.demo.no_send_e2e import ARTIFACT_NAMES
from personalos.mvp_readiness import BLOCKED_LIVE_RAILS
from personalos.nonhuman_closure import HUMAN_REQUIRED_GATES
from personalos.phase14_pilot_prep import SAFETY_POSTURE
from personalos.weekend_test_readiness import (
    build_weekend_test_readiness_report,
    validate_weekend_test_readiness_report_contract,
)


DRY_RUN_EVIDENCE_SCHEMA_VERSION = "personal_os_dry_run_evidence_bundle.v1"
DRY_RUN_EVIDENCE_PHASE_LABEL = "Personal OS dry-run evidence bundle"
DRY_RUN_EVIDENCE_STATUS = "dry_run_contract_recorded_not_live"
DRY_RUN_EVIDENCE_DEFAULT_GENERATED_AT_UTC = "2026-06-26T02:45:00+00:00"

DRY_RUN_EVIDENCE_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "dry_run_execution_started",
    "repo_evidence_bundle_written",
    "temp_only_smoke_supported",
    "live_mvp_ready",
    "human_gates_remaining",
    "readiness",
    "weekend_test_readiness",
    "no_send_demo_contract",
    "smoke_command_templates",
    "fake_local_fixture_surfaces",
    "completion_report_contract",
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

WEEKEND_TEST_READINESS_PAYLOAD_FIELDS: tuple[str, ...] = (
    "status",
    "contract_valid",
    "weekend_testing_started",
    "live_testing_authorized",
    "human_gates_remaining",
)

NO_SEND_DEMO_CONTRACT_FIELDS: tuple[str, ...] = (
    "demo_name",
    "phase_name",
    "command_contract",
    "artifact_names",
    "requires_explicit_safe_output_dir",
    "output_dir_must_be_temp",
    "repo_local_var_allowed",
    "repo_local_db_allowed",
    "demo_sqlite_name",
    "writes_repo_files",
    "external_writes_allowed",
)

SMOKE_COMMAND_TEMPLATE_FIELDS: tuple[str, ...] = (
    "command_id",
    "command_template",
    "mode",
    "writes_only_temp_output",
    "requires_credentials",
    "uses_production_db",
    "activates_scheduler",
    "calls_openclaw",
    "external_write",
)

FAKE_LOCAL_FIXTURE_SURFACE_FIELDS: tuple[str, ...] = (
    "surface_id",
    "label",
    "fixture_source",
    "mode",
    "fake_or_preview_only",
    "live_client_allowed",
    "credential_required",
    "external_write",
)

COMPLETION_REPORT_CONTRACT_FIELDS: tuple[str, ...] = (
    "required_top_level_fields",
    "required_safety_assertions",
    "required_artifacts",
    "requires_phase14_blocked",
    "requires_no_deviations",
    "allows_secret_values",
    "allows_live_object_ids",
    "authorizes_live_access",
)

NO_SEND_COMPLETION_REPORT_FIELDS: tuple[str, ...] = (
    "demo_name",
    "phase_name",
    "command_contract",
    "status",
    "summary_status",
    "output_dir",
    "generated_db_path",
    "workflow_steps_attempted",
    "workflow_steps_completed",
    "workflow_steps",
    "artifact_list",
    "artifact_paths",
    "safety_assertions",
    "no_send_export_summary",
    "blocked_live_action_summary",
    "status_readiness_summary",
    "fixture_manifest_hash",
    "state_counts",
    "phase_14_blocked",
    "deviations",
)

NO_SEND_SAFETY_ASSERTION_FIELDS: tuple[str, ...] = (
    "readiness.status",
    "inert_report_only",
    "live_rails_activated",
    "credentials_loaded",
    "credentials_read",
    "production_db_path_active",
    "scheduler_activated",
    "launch_agent_installed",
    "crontab_modified",
    "daemon_started",
    "openclaw_called",
    "external_services_contacted",
    "external_mutation",
    "gmail_touched",
    "todoist_touched",
    "calendar_touched",
    "personalos_markdown_written",
    "protected_paths_touched",
    "scheduler_preview_status",
    "operator_status_readiness",
    "operator_status_live_rails_activated",
    "all_required_assertions_passed",
)

NO_SEND_SAFETY_FALSE_FIELDS: tuple[str, ...] = (
    "live_rails_activated",
    "credentials_loaded",
    "credentials_read",
    "production_db_path_active",
    "scheduler_activated",
    "launch_agent_installed",
    "crontab_modified",
    "daemon_started",
    "openclaw_called",
    "external_services_contacted",
    "external_mutation",
    "gmail_touched",
    "todoist_touched",
    "calendar_touched",
    "personalos_markdown_written",
    "protected_paths_touched",
    "operator_status_live_rails_activated",
)

SMOKE_COMMAND_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "command_id": "phase13e_d_no_send_e2e",
        "command_template": COMMAND_CONTRACT,
        "mode": "inert / no-send / synthetic fixture demo",
        "writes_only_temp_output": True,
        "requires_credentials": False,
        "uses_production_db": False,
        "activates_scheduler": False,
        "calls_openclaw": False,
        "external_write": False,
    },
    {
        "command_id": "readiness_status_json",
        "command_template": "PYTHONPATH=src python3 -m personalos.cli readiness status --json",
        "mode": "inert / report-only",
        "writes_only_temp_output": False,
        "requires_credentials": False,
        "uses_production_db": False,
        "activates_scheduler": False,
        "calls_openclaw": False,
        "external_write": False,
    },
    {
        "command_id": "workflow_catalog_json",
        "command_template": "PYTHONPATH=src python3 -m personalos.cli workflows --json",
        "mode": "inert / report-only",
        "writes_only_temp_output": False,
        "requires_credentials": False,
        "uses_production_db": False,
        "activates_scheduler": False,
        "calls_openclaw": False,
        "external_write": False,
    },
)

FAKE_LOCAL_FIXTURE_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "surface_id": "todoist_fake_client",
        "label": "Todoist simulated write fake client",
        "fixture_source": "src/personalos/todoist.py",
        "mode": "simulated write with fake external task IDs",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
    {
        "surface_id": "calendar_fake_client",
        "label": "Google Calendar simulated write fake client",
        "fixture_source": "src/personalos/calendar_blocks.py",
        "mode": "simulated write with fake external event IDs",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
    {
        "surface_id": "fake_composer_adapter",
        "label": "Composer fake model adapter",
        "fixture_source": "src/personalos/composer.py",
        "mode": "fake model run only",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
    {
        "surface_id": "synthesis_fake_fixture",
        "label": "Synthetic ChatGPT synthesis fixture",
        "fixture_source": "src/personalos/demo/fixtures.py",
        "mode": "local preview and approved local SQLite apply only",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
    {
        "surface_id": "side_effect_dry_run_ledger",
        "label": "Side-effect dry-run ledger",
        "fixture_source": "src/personalos/side_effects.py",
        "mode": "dry-run ledger intent and attempt only",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
    {
        "surface_id": "scheduler_simulated_preview",
        "label": "Scheduler simulated preview",
        "fixture_source": "src/personalos/scheduler.py",
        "mode": "foreground simulated preview only",
        "fake_or_preview_only": True,
        "live_client_allowed": False,
        "credential_required": False,
        "external_write": False,
    },
)

NON_AUTHORIZATION_FIELDS: tuple[str, ...] = (
    "dry_run_bundle_is_not_live_testing_authorization",
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
class DryRunEvidenceContractValidation:
    report_matches_inert_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_inert_contract": self.report_matches_inert_contract,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class NoSendCompletionReportValidation:
    report_matches_dry_run_contract: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_matches_dry_run_contract": (
                self.report_matches_dry_run_contract
            ),
            "reasons": list(self.reasons),
        }


def build_dry_run_evidence_bundle_report() -> dict[str, Any]:
    """Build the inert dry-run evidence bundle contract report."""
    weekend_report = build_weekend_test_readiness_report()
    weekend_validation = validate_weekend_test_readiness_report_contract(
        weekend_report
    )

    return {
        "schema_version": DRY_RUN_EVIDENCE_SCHEMA_VERSION,
        "generated_at_utc": DRY_RUN_EVIDENCE_DEFAULT_GENERATED_AT_UTC,
        "phase_label": DRY_RUN_EVIDENCE_PHASE_LABEL,
        "status": DRY_RUN_EVIDENCE_STATUS,
        "dry_run_execution_started": False,
        "repo_evidence_bundle_written": False,
        "temp_only_smoke_supported": True,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "weekend_test_readiness": {
            "status": weekend_report["status"],
            "contract_valid": weekend_validation.report_matches_inert_contract,
            "weekend_testing_started": weekend_report["weekend_testing_started"],
            "live_testing_authorized": weekend_report["live_testing_authorized"],
            "human_gates_remaining": weekend_report["human_gates_remaining"],
        },
        "no_send_demo_contract": {
            "demo_name": DEMO_NAME,
            "phase_name": PHASE_NAME,
            "command_contract": COMMAND_CONTRACT,
            "artifact_names": list(ARTIFACT_NAMES),
            "requires_explicit_safe_output_dir": True,
            "output_dir_must_be_temp": True,
            "repo_local_var_allowed": False,
            "repo_local_db_allowed": False,
            "demo_sqlite_name": "demo.sqlite3",
            "writes_repo_files": False,
            "external_writes_allowed": False,
        },
        "smoke_command_templates": _materialize_records(SMOKE_COMMAND_TEMPLATES),
        "fake_local_fixture_surfaces": _materialize_records(
            FAKE_LOCAL_FIXTURE_SURFACES
        ),
        "completion_report_contract": {
            "required_top_level_fields": list(NO_SEND_COMPLETION_REPORT_FIELDS),
            "required_safety_assertions": list(NO_SEND_SAFETY_ASSERTION_FIELDS),
            "required_artifacts": list(ARTIFACT_NAMES),
            "requires_phase14_blocked": True,
            "requires_no_deviations": True,
            "allows_secret_values": False,
            "allows_live_object_ids": False,
            "authorizes_live_access": False,
        },
        "human_required_gates": list(HUMAN_REQUIRED_GATES),
        "blocked_live_rails": list(BLOCKED_LIVE_RAILS),
        "non_authorization": {
            "dry_run_bundle_is_not_live_testing_authorization": True,
            "repo_merge_is_not_live_authorization": True,
            **{field: False for field in NON_AUTHORIZATION_FALSE_FIELDS},
        },
        "safety_posture": dict(SAFETY_POSTURE),
    }


def validate_dry_run_evidence_bundle_report_contract(
    report: Mapping[str, Any] | None,
) -> DryRunEvidenceContractValidation:
    """Validate the dry-run evidence contract without authorizing live work."""
    if report is None:
        return DryRunEvidenceContractValidation(
            report_matches_inert_contract=False,
            reasons=("No dry-run evidence bundle report was supplied.",),
        )

    blocked_reasons = _blocked_dry_run_evidence_reasons(report)
    if blocked_reasons:
        return DryRunEvidenceContractValidation(
            report_matches_inert_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return DryRunEvidenceContractValidation(
        report_matches_inert_contract=True,
        reasons=(
            "Dry-run evidence bundle report remains inert and not live testing.",
        ),
    )


def validate_no_send_completion_report_contract(
    report: Mapping[str, Any] | None,
) -> NoSendCompletionReportValidation:
    """Validate a no-send demo completion report without reading artifacts."""
    if report is None:
        return NoSendCompletionReportValidation(
            report_matches_dry_run_contract=False,
            reasons=("No no-send completion report was supplied.",),
        )

    blocked_reasons = _blocked_no_send_completion_reasons(report)
    if blocked_reasons:
        return NoSendCompletionReportValidation(
            report_matches_dry_run_contract=False,
            reasons=tuple(blocked_reasons),
        )

    return NoSendCompletionReportValidation(
        report_matches_dry_run_contract=True,
        reasons=(
            "No-send completion report matches the dry-run evidence contract.",
        ),
    )


def _blocked_dry_run_evidence_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != DRY_RUN_EVIDENCE_TOP_LEVEL_FIELDS:
        reasons.append(
            "Dry-run evidence report top-level fields do not match the contract."
        )

    if report.get("schema_version") != DRY_RUN_EVIDENCE_SCHEMA_VERSION:
        reasons.append(
            "Dry-run evidence report schema_version does not match the contract."
        )

    if report.get("generated_at_utc") != DRY_RUN_EVIDENCE_DEFAULT_GENERATED_AT_UTC:
        reasons.append(
            "Dry-run evidence report generated_at_utc does not match the contract."
        )

    if report.get("phase_label") != DRY_RUN_EVIDENCE_PHASE_LABEL:
        reasons.append(
            "Dry-run evidence report phase_label does not match the contract."
        )

    if report.get("status") != DRY_RUN_EVIDENCE_STATUS:
        reasons.append(
            "Dry-run evidence report status must remain dry_run_contract_recorded_not_live."
        )

    expected_bools = {
        "dry_run_execution_started": False,
        "repo_evidence_bundle_written": False,
        "temp_only_smoke_supported": True,
        "live_mvp_ready": False,
        "human_gates_remaining": True,
    }
    for field, expected in expected_bools.items():
        if report.get(field) is not expected:
            reasons.append(f"Dry-run evidence report field {field} drifted.")

    _check_readiness(report.get("readiness"), reasons)
    _check_weekend_readiness(report.get("weekend_test_readiness"), reasons)
    _check_no_send_demo_contract(report.get("no_send_demo_contract"), reasons)
    _check_smoke_commands(report.get("smoke_command_templates"), reasons)
    _check_fake_local_surfaces(report.get("fake_local_fixture_surfaces"), reasons)
    _check_completion_contract(report.get("completion_report_contract"), reasons)

    if report.get("human_required_gates") != list(HUMAN_REQUIRED_GATES):
        reasons.append("Dry-run evidence report human gate list drifted.")

    if report.get("blocked_live_rails") != list(BLOCKED_LIVE_RAILS):
        reasons.append("Dry-run evidence report blocked live rail list drifted.")

    _check_non_authorization(report.get("non_authorization"), reasons)

    if report.get("safety_posture") != dict(SAFETY_POSTURE):
        reasons.append(
            "Dry-run evidence report safety_posture does not match the contract."
        )

    return _dedupe(reasons)


def _blocked_no_send_completion_reasons(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []

    if tuple(report) != NO_SEND_COMPLETION_REPORT_FIELDS:
        reasons.append(
            "No-send completion report top-level fields do not match the contract."
        )

    expected = {
        "demo_name": DEMO_NAME,
        "phase_name": PHASE_NAME,
        "command_contract": COMMAND_CONTRACT,
        "status": "completed",
        "summary_status": "completed_no_send_evidence_generated",
        "phase_14_blocked": True,
        "deviations": [],
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(report.get(field), expected_value):
            reasons.append(f"No-send completion report field {field} drifted.")

    if not _non_empty_string(report.get("output_dir")):
        reasons.append("No-send completion report output_dir is missing.")

    generated_db_path = report.get("generated_db_path")
    if not _non_empty_string(generated_db_path) or not str(generated_db_path).endswith(
        "/demo.sqlite3"
    ):
        reasons.append(
            "No-send completion report generated_db_path must end with demo.sqlite3."
        )

    _check_completion_artifacts(report.get("artifact_list"), reasons)
    _check_completion_artifact_paths(report.get("artifact_paths"), reasons)
    _check_completion_safety(report.get("safety_assertions"), reasons)
    _check_completion_no_send_summary(report.get("no_send_export_summary"), reasons)
    _check_completion_blocked_summary(
        report.get("blocked_live_action_summary"),
        reasons,
    )

    return _dedupe(reasons)


def _check_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Dry-run evidence report readiness payload is missing.")
        return
    if tuple(value) != READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Dry-run evidence report readiness fields do not match the contract."
        )
    if value.get("status") != "not_ready":
        reasons.append("Dry-run evidence report readiness.status must remain not_ready.")
    if value.get("inert_report_only") is not True:
        reasons.append(
            "Dry-run evidence report readiness.inert_report_only must remain true."
        )
    if value.get("live_rails_activated") is not False:
        reasons.append(
            "Dry-run evidence report readiness.live_rails_activated must remain false."
        )


def _check_weekend_readiness(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Dry-run evidence report weekend readiness payload is missing.")
        return
    if tuple(value) != WEEKEND_TEST_READINESS_PAYLOAD_FIELDS:
        reasons.append(
            "Dry-run evidence report weekend readiness fields do not match the contract."
        )
    expected = {
        "status": "test_plan_recorded_not_live",
        "contract_valid": True,
        "weekend_testing_started": False,
        "live_testing_authorized": False,
        "human_gates_remaining": True,
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Dry-run evidence report weekend readiness field {field} drifted."
            )


def _check_no_send_demo_contract(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Dry-run evidence report no-send demo contract is missing.")
        return
    if tuple(value) != NO_SEND_DEMO_CONTRACT_FIELDS:
        reasons.append(
            "Dry-run evidence report no-send demo contract fields do not match the contract."
        )
    expected = {
        "demo_name": DEMO_NAME,
        "phase_name": PHASE_NAME,
        "command_contract": COMMAND_CONTRACT,
        "artifact_names": list(ARTIFACT_NAMES),
        "requires_explicit_safe_output_dir": True,
        "output_dir_must_be_temp": True,
        "repo_local_var_allowed": False,
        "repo_local_db_allowed": False,
        "demo_sqlite_name": "demo.sqlite3",
        "writes_repo_files": False,
        "external_writes_allowed": False,
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Dry-run evidence report no-send demo field {field} drifted."
            )


def _check_smoke_commands(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(SMOKE_COMMAND_TEMPLATES):
        reasons.append("Dry-run evidence report smoke command template list drifted.")
    if not isinstance(value, list):
        reasons.append("Dry-run evidence report smoke command payload is missing.")
        return
    for command in value:
        if not isinstance(command, Mapping):
            reasons.append("Dry-run evidence report smoke command is malformed.")
            continue
        if tuple(command) != SMOKE_COMMAND_TEMPLATE_FIELDS:
            reasons.append(
                "Dry-run evidence report smoke command fields do not match the contract."
            )
        for field in (
            "requires_credentials",
            "uses_production_db",
            "activates_scheduler",
            "calls_openclaw",
            "external_write",
        ):
            if command.get(field) is not False:
                reasons.append(
                    f"Dry-run evidence report smoke command field {field} must remain false."
                )


def _check_fake_local_surfaces(value: Any, reasons: list[str]) -> None:
    if value != _materialize_records(FAKE_LOCAL_FIXTURE_SURFACES):
        reasons.append("Dry-run evidence report fake/local fixture surface list drifted.")
    if not isinstance(value, list):
        reasons.append(
            "Dry-run evidence report fake/local fixture surface payload is missing."
        )
        return
    for surface in value:
        if not isinstance(surface, Mapping):
            reasons.append(
                "Dry-run evidence report fake/local fixture surface is malformed."
            )
            continue
        if tuple(surface) != FAKE_LOCAL_FIXTURE_SURFACE_FIELDS:
            reasons.append(
                "Dry-run evidence report fake/local fixture fields do not match the contract."
            )
        if surface.get("fake_or_preview_only") is not True:
            reasons.append(
                "Dry-run evidence report fake/local fixture marker must remain true."
            )
        for field in ("live_client_allowed", "credential_required", "external_write"):
            if surface.get(field) is not False:
                reasons.append(
                    f"Dry-run evidence report fake/local fixture field {field} must remain false."
                )


def _check_completion_contract(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append(
            "Dry-run evidence report completion report contract payload is missing."
        )
        return
    if tuple(value) != COMPLETION_REPORT_CONTRACT_FIELDS:
        reasons.append(
            "Dry-run evidence report completion report contract fields do not match the contract."
        )
    expected = {
        "required_top_level_fields": list(NO_SEND_COMPLETION_REPORT_FIELDS),
        "required_safety_assertions": list(NO_SEND_SAFETY_ASSERTION_FIELDS),
        "required_artifacts": list(ARTIFACT_NAMES),
        "requires_phase14_blocked": True,
        "requires_no_deviations": True,
        "allows_secret_values": False,
        "allows_live_object_ids": False,
        "authorizes_live_access": False,
    }
    for field, expected_value in expected.items():
        if not _matches_expected_value(value.get(field), expected_value):
            reasons.append(
                f"Dry-run evidence report completion contract field {field} drifted."
            )


def _check_non_authorization(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("Dry-run evidence report non_authorization payload is missing.")
        return
    if tuple(value) != NON_AUTHORIZATION_FIELDS:
        reasons.append(
            "Dry-run evidence report non_authorization fields do not match the contract."
        )
    for field in NON_AUTHORIZATION_TRUE_FIELDS:
        if value.get(field) is not True:
            reasons.append(
                f"Dry-run evidence report non_authorization field {field} must remain true."
            )
    for field in NON_AUTHORIZATION_FALSE_FIELDS:
        if value.get(field) is not False:
            reasons.append(
                f"Dry-run evidence report non_authorization field {field} must remain false."
            )


def _check_completion_artifacts(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, list):
        reasons.append("No-send completion report artifact_list is missing.")
        return
    artifact_names = [
        item.get("name")
        for item in value
        if isinstance(item, Mapping)
    ]
    if set(artifact_names) != set(ARTIFACT_NAMES):
        reasons.append("No-send completion report artifact names drifted.")
    for item in value:
        if not isinstance(item, Mapping):
            reasons.append("No-send completion report artifact entry is malformed.")
            continue
        if item.get("under_output_dir") is not True:
            reasons.append(
                "No-send completion report artifact must remain under output_dir."
            )
        if item.get("expected") is not True:
            reasons.append("No-send completion report artifact expected flag drifted.")


def _check_completion_artifact_paths(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("No-send completion report artifact_paths payload is missing.")
        return
    if set(value) != set(ARTIFACT_NAMES):
        reasons.append("No-send completion report artifact_paths keys drifted.")
    for artifact_name in ARTIFACT_NAMES:
        path = value.get(artifact_name)
        if not _non_empty_string(path):
            reasons.append(
                f"No-send completion report artifact path {artifact_name} is missing."
            )


def _check_completion_safety(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("No-send completion report safety_assertions payload is missing.")
        return
    if tuple(value) != NO_SEND_SAFETY_ASSERTION_FIELDS:
        reasons.append(
            "No-send completion report safety assertion fields do not match the contract."
        )
    if value.get("readiness.status") != "not_ready":
        reasons.append(
            "No-send completion report readiness.status must remain not_ready."
        )
    if value.get("inert_report_only") is not True:
        reasons.append(
            "No-send completion report inert_report_only must remain true."
        )
    if value.get("scheduler_preview_status") != "simulated_preview_only":
        reasons.append(
            "No-send completion report scheduler preview must remain simulated only."
        )
    if value.get("operator_status_readiness") != "not_ready":
        reasons.append(
            "No-send completion report operator readiness must remain not_ready."
        )
    if value.get("all_required_assertions_passed") is not True:
        reasons.append(
            "No-send completion report required safety assertions must remain true."
        )
    for field in NO_SEND_SAFETY_FALSE_FIELDS:
        if value.get(field) is not False:
            reasons.append(
                f"No-send completion report safety assertion {field} must remain false."
            )


def _check_completion_no_send_summary(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("No-send completion report no-send summary is missing.")
        return
    expected_false_fields = (
        "gmail_send",
        "gmail_draft",
        "todoist_writes",
        "calendar_writes",
        "personalos_markdown_writes",
    )
    if value.get("delivery_mode") != "no_send":
        reasons.append("No-send completion report delivery_mode must remain no_send.")
    for field in expected_false_fields:
        if value.get(field) is not False:
            reasons.append(
                f"No-send completion report summary field {field} must remain false."
            )


def _check_completion_blocked_summary(value: Any, reasons: list[str]) -> None:
    if not isinstance(value, Mapping):
        reasons.append("No-send completion report blocked-live summary is missing.")
        return
    for field in (
        "live_tasks_created",
        "live_calendar_events_created",
        "gmail_sent_or_drafted",
        "markdown_written",
    ):
        if value.get(field) is not False:
            reasons.append(
                f"No-send completion report blocked-live field {field} must remain false."
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


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value != ""

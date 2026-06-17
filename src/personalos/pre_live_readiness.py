"""Inert pre-live readiness gate model and evaluator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from personalos.path_safety import (
    reject_protected_path,
    reject_sensitive_path,
    resolve_explicit_path,
)


class ReadinessStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"
    BLOCKED = "blocked"


class GateStatus(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    BLOCKED = "blocked"


class LiveRailStatus(StrEnum):
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    REQUIRES_APPROVAL = "requires_approval"
    ACTIVE = "active"
    BLOCKED = "blocked"


class ExecutionMode(StrEnum):
    PREVIEW = "preview"
    DRY_RUN = "dry_run"
    SIMULATED_WRITE = "simulated_write"
    INTERNAL_APPLY = "internal_apply"
    LIVE_WRITE = "live_write"


class LiveRail(StrEnum):
    GMAIL = "gmail"
    TODOIST = "todoist"
    GOOGLE_CALENDAR = "google_calendar"
    PERSONALOS_MARKDOWN = "personalos_markdown"
    OPENCLAW_RUNTIME = "openclaw_runtime_workflows"
    SCHEDULER = "scheduler_launchagent_background_loop"
    LIVE_MODEL_API = "live_model_api_calls"
    PRODUCTION_SQLITE = "production_sqlite_state"


class ReadinessGate(StrEnum):
    CONFIG_PROVIDED = "config_provided"
    LIVE_PERMISSIONS_DISABLED_BY_DEFAULT = "live_permissions_disabled_by_default"
    MODE_SEPARATION_CONFIRMED = "mode_separation_confirmed"
    CREDENTIALS_POLICY_ACKNOWLEDGED = "credentials_policy_acknowledged"
    CREDENTIALS_NOT_LOADED = "credentials_not_loaded"
    PRODUCTION_DB_PATH_INACTIVE_BY_DEFAULT = "production_db_path_inactive_by_default"
    PRODUCTION_DB_PATH_APPROVED = "production_db_path_approved"
    PRODUCTION_MIGRATION_INACTIVE_BY_DEFAULT = "production_migration_inactive_by_default"
    PRODUCTION_MIGRATION_POLICY_APPROVED = "production_migration_policy_approved"
    BACKUP_RESTORE_VERIFIED = "backup_restore_verified"
    IDEMPOTENCY_POLICY_APPROVED = "idempotency_policy_approved"
    SIDE_EFFECT_LEDGER_APPROVED = "side_effect_ledger_approved"
    COMPLETION_REPORT_APPROVED = "completion_report_approved"
    ROLLBACK_RECOVERY_APPROVED = "rollback_recovery_approved"
    GLOBAL_KILL_SWITCH_DEFINED = "global_kill_switch_defined"
    SCHEDULER_ACTIVATION_REQUIREMENT_APPROVED = "scheduler_activation_requirement_approved"
    OPERATOR_HANDOFF_APPROVED = "operator_handoff_approved"
    FIRST_LIVE_PILOT_APPROVED = "first_live_pilot_approved"
    TEST_DOCUMENTATION_CURRENT = "test_documentation_current"
    CHRIS_APPROVAL_RECORDED = "chris_approval_recorded"


LIVE_RAILS: tuple[LiveRail, ...] = (
    LiveRail.GMAIL,
    LiveRail.TODOIST,
    LiveRail.GOOGLE_CALENDAR,
    LiveRail.PERSONALOS_MARKDOWN,
    LiveRail.OPENCLAW_RUNTIME,
    LiveRail.SCHEDULER,
    LiveRail.LIVE_MODEL_API,
    LiveRail.PRODUCTION_SQLITE,
)

EXECUTION_MODES: tuple[ExecutionMode, ...] = (
    ExecutionMode.PREVIEW,
    ExecutionMode.DRY_RUN,
    ExecutionMode.SIMULATED_WRITE,
    ExecutionMode.INTERNAL_APPLY,
    ExecutionMode.LIVE_WRITE,
)

DEFAULT_LIVE_RAIL_REASONS: dict[LiveRail, str] = {
    LiveRail.GMAIL: "Gmail live draft/send rail is disabled; no Gmail client or credential loading is implemented.",
    LiveRail.TODOIST: "Todoist live write rail is disabled; only dev/test fake or preview paths exist.",
    LiveRail.GOOGLE_CALENDAR: "Google Calendar live write rail is disabled; only dev/test fake or preview paths exist.",
    LiveRail.PERSONALOS_MARKDOWN: "PersonalOS Markdown live write rail is disabled; protected paths remain off limits.",
    LiveRail.OPENCLAW_RUNTIME: "OpenClaw runtime workflow rail is disabled; no OpenClaw operation is implemented.",
    LiveRail.SCHEDULER: "Scheduler, LaunchAgent, and background loop activation rail is disabled.",
    LiveRail.LIVE_MODEL_API: "Live model/API call rail is disabled; no provider client is implemented.",
    LiveRail.PRODUCTION_SQLITE: "Production SQLite rail is disabled; no production DB path is active.",
}


@dataclass(frozen=True)
class LiveRailConfig:
    status: LiveRailStatus | str = LiveRailStatus.DISABLED
    active: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class PreLiveReadinessConfig:
    mode_separation_confirmed: bool = False
    credentials_policy_acknowledged: bool = False
    credentials_loaded: bool = False
    production_db_path: str | Path | None = None
    production_db_path_active: bool = False
    production_db_path_approved: bool = False
    production_migration_active: bool = False
    production_migration_policy_approved: bool = False
    backup_restore_verified: bool = False
    idempotency_policy_approved: bool = False
    side_effect_ledger_policy_approved: bool = False
    completion_report_policy_approved: bool = False
    rollback_recovery_policy_approved: bool = False
    global_kill_switch_defined: bool = False
    global_kill_switch_reference: str | None = None
    scheduler_activation_requirement_approved: bool = False
    operator_handoff_approved: bool = False
    first_live_pilot_approved: bool = False
    first_live_pilot_scope: str | None = None
    tests_and_docs_current: bool = False
    chris_approval_recorded: bool = False
    chris_approval_reference: str | None = None
    rails: Mapping[LiveRail | str, LiveRailConfig | Mapping[str, Any]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class GateResult:
    gate: ReadinessGate
    status: GateStatus
    satisfied: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "status": self.status.value,
            "satisfied": self.satisfied,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RailResult:
    rail: LiveRail
    status: LiveRailStatus
    active: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rail": self.rail.value,
            "status": self.status.value,
            "active": self.active,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PreLiveReadinessReport:
    status: ReadinessStatus
    gates: tuple[GateResult, ...]
    rails: tuple[RailResult, ...]
    reasons: tuple[str, ...]
    execution_modes: tuple[ExecutionMode, ...] = EXECUTION_MODES
    credentials_loaded: bool = False
    production_db_path_active: bool = False
    production_migration_active: bool = False
    external_services_contacted: bool = False
    credentials_read: bool = False
    files_created: bool = False
    runtime_state_mutated: bool = False
    scheduler_activated: bool = False
    openclaw_called: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "gates": [gate.to_dict() for gate in self.gates],
            "rails": [rail.to_dict() for rail in self.rails],
            "reasons": list(self.reasons),
            "execution_modes": [mode.value for mode in self.execution_modes],
            "credentials_loaded": self.credentials_loaded,
            "production_db_path_active": self.production_db_path_active,
            "production_migration_active": self.production_migration_active,
            "external_services_contacted": self.external_services_contacted,
            "credentials_read": self.credentials_read,
            "files_created": self.files_created,
            "runtime_state_mutated": self.runtime_state_mutated,
            "scheduler_activated": self.scheduler_activated,
            "openclaw_called": self.openclaw_called,
        }


def default_live_rail_statuses() -> tuple[RailResult, ...]:
    return tuple(_disabled_rail_result(rail) for rail in LIVE_RAILS)


def create_default_pre_live_readiness_report() -> dict[str, Any]:
    return readiness_report_to_summary(evaluate_pre_live_readiness())


def readiness_report_to_summary(report: PreLiveReadinessReport) -> dict[str, Any]:
    report_dict = report.to_dict()
    return {
        **report_dict,
        "inert_report_only": True,
        "read_only": True,
        "database_write": False,
        "external_mutation": False,
        "live_rails_activated": False,
        "no_live_rails_activated": True,
        "no_external_writes": True,
        "no_credentials_loaded": not report.credentials_loaded,
        "no_production_db_active": not report.production_db_path_active,
        "no_scheduler_activation": not report.scheduler_activated,
        "no_openclaw_call": not report.openclaw_called,
        "summary_text": (
            "Inert pre-live readiness report only; no live rails are activated."
        ),
        "disabled_rail_names": [
            rail["rail"]
            for rail in report_dict["rails"]
            if rail["status"] == LiveRailStatus.DISABLED.value
        ],
        "blocked_or_missing_gate_count": sum(
            1 for gate in report_dict["gates"] if not gate["satisfied"]
        ),
        "blocked_or_non_disabled_rail_count": sum(
            1
            for rail in report_dict["rails"]
            if rail["status"] != LiveRailStatus.DISABLED.value or rail["active"]
        ),
    }


def evaluate_pre_live_readiness(
    config: PreLiveReadinessConfig | None = None,
) -> PreLiveReadinessReport:
    rail_configs, unknown_rails = _normalize_rail_configs(config.rails if config else {})
    rail_results = tuple(_evaluate_rail(rail, rail_configs.get(rail)) for rail in LIVE_RAILS)
    gates = _evaluate_gates(config, rail_results=rail_results, unknown_rails=unknown_rails)

    gate_blocked = any(gate.status is GateStatus.BLOCKED for gate in gates)
    rail_blocked = any(rail.status is LiveRailStatus.BLOCKED for rail in rail_results)
    all_gates_satisfied = all(gate.satisfied for gate in gates)
    all_rails_disabled = all(
        rail.status is LiveRailStatus.DISABLED and not rail.active for rail in rail_results
    )

    if gate_blocked or rail_blocked:
        status = ReadinessStatus.BLOCKED
    elif all_gates_satisfied and all_rails_disabled:
        status = ReadinessStatus.READY
    else:
        status = ReadinessStatus.NOT_READY

    reasons = tuple(
        result.reason
        for result in (*gates, *rail_results)
        if _result_is_not_ready_reason(result)
    )
    return PreLiveReadinessReport(
        status=status,
        gates=tuple(gates),
        rails=rail_results,
        reasons=reasons,
        credentials_loaded=False,
        production_db_path_active=False,
        production_migration_active=False,
        external_services_contacted=False,
        credentials_read=False,
        files_created=False,
        runtime_state_mutated=False,
        scheduler_activated=False,
        openclaw_called=False,
    )


def _evaluate_gates(
    config: PreLiveReadinessConfig | None,
    *,
    rail_results: tuple[RailResult, ...],
    unknown_rails: tuple[str, ...],
) -> list[GateResult]:
    return [
        _gate(
            ReadinessGate.CONFIG_PROVIDED,
            config is not None,
            "Explicit pre-live readiness config was provided.",
            "Missing readiness config fails closed.",
        ),
        _live_permissions_gate(rail_results, unknown_rails),
        _gate_from_bool(
            config,
            ReadinessGate.MODE_SEPARATION_CONFIRMED,
            "mode_separation_confirmed",
            "Preview, dry-run, simulated write, internal apply, and live write modes are explicitly separated.",
            "Mode separation has not been explicitly confirmed.",
        ),
        _credentials_policy_gate(config),
        _credentials_not_loaded_gate(config),
        _production_path_inactive_gate(config),
        _production_path_approval_gate(config),
        _production_migration_inactive_gate(config),
        _gate_from_bool(
            config,
            ReadinessGate.PRODUCTION_MIGRATION_POLICY_APPROVED,
            "production_migration_policy_approved",
            "Production migration policy is explicitly approved.",
            "Production migration policy approval is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.BACKUP_RESTORE_VERIFIED,
            "backup_restore_verified",
            "Backup and restore verification is recorded.",
            "Backup and restore verification is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.IDEMPOTENCY_POLICY_APPROVED,
            "idempotency_policy_approved",
            "Idempotency policy is explicitly approved.",
            "Idempotency policy approval is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.SIDE_EFFECT_LEDGER_APPROVED,
            "side_effect_ledger_policy_approved",
            "Side-effect ledger requirement is explicitly approved.",
            "Side-effect ledger requirement approval is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.COMPLETION_REPORT_APPROVED,
            "completion_report_policy_approved",
            "Completion report requirement is explicitly approved.",
            "Completion report requirement approval is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.ROLLBACK_RECOVERY_APPROVED,
            "rollback_recovery_policy_approved",
            "Rollback and recovery requirement is explicitly approved.",
            "Rollback and recovery requirement approval is missing.",
        ),
        _text_gate(
            config,
            ReadinessGate.GLOBAL_KILL_SWITCH_DEFINED,
            "global_kill_switch_defined",
            "global_kill_switch_reference",
            "Global kill switch or disable mechanism is defined.",
            "Global kill switch or disable mechanism is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.SCHEDULER_ACTIVATION_REQUIREMENT_APPROVED,
            "scheduler_activation_requirement_approved",
            "Scheduler activation requirement is explicitly approved.",
            "Scheduler activation requirement approval is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.OPERATOR_HANDOFF_APPROVED,
            "operator_handoff_approved",
            "Operator handoff requirement is explicitly approved.",
            "Operator handoff approval is missing.",
        ),
        _text_gate(
            config,
            ReadinessGate.FIRST_LIVE_PILOT_APPROVED,
            "first_live_pilot_approved",
            "first_live_pilot_scope",
            "First-live pilot scope is explicitly approved.",
            "First-live pilot approval or scope is missing.",
        ),
        _gate_from_bool(
            config,
            ReadinessGate.TEST_DOCUMENTATION_CURRENT,
            "tests_and_docs_current",
            "Tests and documentation are marked current for this readiness gate.",
            "Current test and documentation evidence is missing.",
        ),
        _text_gate(
            config,
            ReadinessGate.CHRIS_APPROVAL_RECORDED,
            "chris_approval_recorded",
            "chris_approval_reference",
            "Explicit Chris approval marker is recorded.",
            "Explicit Chris approval marker is missing.",
        ),
    ]


def _live_permissions_gate(
    rail_results: tuple[RailResult, ...],
    unknown_rails: tuple[str, ...],
) -> GateResult:
    if unknown_rails:
        return _blocked_gate(
            ReadinessGate.LIVE_PERMISSIONS_DISABLED_BY_DEFAULT,
            f"Unknown live rail config keys are blocked: {', '.join(unknown_rails)}.",
        )
    non_disabled = [
        rail.rail.value
        for rail in rail_results
        if rail.status is not LiveRailStatus.DISABLED or rail.active
    ]
    if non_disabled:
        return _blocked_gate(
            ReadinessGate.LIVE_PERMISSIONS_DISABLED_BY_DEFAULT,
            f"Live rail permissions must remain disabled; non-disabled rails: {', '.join(non_disabled)}.",
        )
    return _satisfied_gate(
        ReadinessGate.LIVE_PERMISSIONS_DISABLED_BY_DEFAULT,
        "All live rail permissions are disabled by default.",
    )


def _credentials_policy_gate(config: PreLiveReadinessConfig | None) -> GateResult:
    if config is None:
        return _missing_gate(
            ReadinessGate.CREDENTIALS_POLICY_ACKNOWLEDGED,
            "Credentials policy acknowledgement is missing.",
        )
    if config.credentials_loaded:
        return _blocked_gate(
            ReadinessGate.CREDENTIALS_POLICY_ACKNOWLEDGED,
            "Credentials were marked loaded; pre-live readiness evaluation must never load credentials.",
        )
    return _gate(
        ReadinessGate.CREDENTIALS_POLICY_ACKNOWLEDGED,
        config.credentials_policy_acknowledged,
        "Credentials policy is acknowledged without loading credentials.",
        "Credentials policy acknowledgement is missing.",
    )


def _credentials_not_loaded_gate(config: PreLiveReadinessConfig | None) -> GateResult:
    if config is not None and config.credentials_loaded:
        return _blocked_gate(
            ReadinessGate.CREDENTIALS_NOT_LOADED,
            "Credentials are marked loaded; this phase is credential-inert.",
        )
    return _satisfied_gate(
        ReadinessGate.CREDENTIALS_NOT_LOADED,
        "Readiness evaluation does not load or read credentials.",
    )


def _production_path_inactive_gate(config: PreLiveReadinessConfig | None) -> GateResult:
    if config is not None and config.production_db_path_active:
        return _blocked_gate(
            ReadinessGate.PRODUCTION_DB_PATH_INACTIVE_BY_DEFAULT,
            "Production DB path was marked active; Phase 13F-B cannot activate production SQLite.",
        )
    return _satisfied_gate(
        ReadinessGate.PRODUCTION_DB_PATH_INACTIVE_BY_DEFAULT,
        "Production DB path is inactive by default.",
    )


def _production_path_approval_gate(config: PreLiveReadinessConfig | None) -> GateResult:
    if config is None:
        return _missing_gate(
            ReadinessGate.PRODUCTION_DB_PATH_APPROVED,
            "Production DB path approval is missing.",
        )
    if config.production_db_path is None:
        return _missing_gate(
            ReadinessGate.PRODUCTION_DB_PATH_APPROVED,
            "No explicit production DB path approval is configured.",
        )
    try:
        resolved = resolve_explicit_path(
            config.production_db_path,
            path_label="production_db_path",
        )
        reject_protected_path(resolved, path_label="production_db_path")
        reject_sensitive_path(resolved, path_label="production_db_path")
    except ValueError as exc:
        return _blocked_gate(ReadinessGate.PRODUCTION_DB_PATH_APPROVED, str(exc))
    return _gate(
        ReadinessGate.PRODUCTION_DB_PATH_APPROVED,
        config.production_db_path_approved,
        "Explicit production DB path approval is configured.",
        "Production DB path approval flag is missing.",
    )


def _production_migration_inactive_gate(config: PreLiveReadinessConfig | None) -> GateResult:
    if config is not None and config.production_migration_active:
        return _blocked_gate(
            ReadinessGate.PRODUCTION_MIGRATION_INACTIVE_BY_DEFAULT,
            "Production migration was marked active; Phase 13F-B cannot run production migrations.",
        )
    return _satisfied_gate(
        ReadinessGate.PRODUCTION_MIGRATION_INACTIVE_BY_DEFAULT,
        "Production migration policy is inactive by default.",
    )


def _gate_from_bool(
    config: PreLiveReadinessConfig | None,
    gate: ReadinessGate,
    attribute: str,
    satisfied_reason: str,
    missing_reason: str,
) -> GateResult:
    if config is None:
        return _missing_gate(gate, missing_reason)
    return _gate(gate, bool(getattr(config, attribute)), satisfied_reason, missing_reason)


def _text_gate(
    config: PreLiveReadinessConfig | None,
    gate: ReadinessGate,
    flag_attribute: str,
    text_attribute: str,
    satisfied_reason: str,
    missing_reason: str,
) -> GateResult:
    if config is None:
        return _missing_gate(gate, missing_reason)
    flag = bool(getattr(config, flag_attribute))
    text = getattr(config, text_attribute)
    text_present = isinstance(text, str) and bool(text.strip())
    return _gate(gate, flag and text_present, satisfied_reason, missing_reason)


def _evaluate_rail(rail: LiveRail, config: LiveRailConfig | None) -> RailResult:
    if config is None:
        return _disabled_rail_result(rail)

    try:
        status = _normalize_rail_status(config.status)
    except ValueError:
        return RailResult(
            rail=rail,
            status=LiveRailStatus.BLOCKED,
            active=False,
            reason=f"{rail.value} has an invalid live rail status and is blocked.",
        )
    activation_requested = config.active or status is LiveRailStatus.ACTIVE
    if activation_requested:
        return RailResult(
            rail=rail,
            status=LiveRailStatus.BLOCKED,
            active=False,
            reason=(
                f"{rail.value} activation was requested, but Phase 13F-B is inert "
                "and implements no live activation path."
            ),
        )
    if status is LiveRailStatus.BLOCKED:
        return RailResult(
            rail=rail,
            status=LiveRailStatus.BLOCKED,
            active=False,
            reason=config.reason or f"{rail.value} is explicitly blocked.",
        )
    if status is LiveRailStatus.REQUIRES_APPROVAL:
        return RailResult(
            rail=rail,
            status=LiveRailStatus.REQUIRES_APPROVAL,
            active=False,
            reason=config.reason or f"{rail.value} requires explicit approval and is not active.",
        )
    if status is LiveRailStatus.NOT_CONFIGURED:
        return RailResult(
            rail=rail,
            status=LiveRailStatus.NOT_CONFIGURED,
            active=False,
            reason=config.reason or f"{rail.value} is not configured and is not active.",
        )
    return RailResult(
        rail=rail,
        status=LiveRailStatus.DISABLED,
        active=False,
        reason=config.reason or DEFAULT_LIVE_RAIL_REASONS[rail],
    )


def _disabled_rail_result(rail: LiveRail) -> RailResult:
    return RailResult(
        rail=rail,
        status=LiveRailStatus.DISABLED,
        active=False,
        reason=DEFAULT_LIVE_RAIL_REASONS[rail],
    )


def _normalize_rail_configs(
    rails: Mapping[LiveRail | str, LiveRailConfig | Mapping[str, Any]],
) -> tuple[dict[LiveRail, LiveRailConfig], tuple[str, ...]]:
    normalized: dict[LiveRail, LiveRailConfig] = {}
    unknown: list[str] = []
    for rail_key, raw_config in rails.items():
        try:
            rail = rail_key if isinstance(rail_key, LiveRail) else LiveRail(str(rail_key))
        except ValueError:
            unknown.append(str(rail_key))
            continue
        if isinstance(raw_config, LiveRailConfig):
            normalized[rail] = raw_config
            continue
        if not isinstance(raw_config, Mapping):
            normalized[rail] = LiveRailConfig(
                status=LiveRailStatus.BLOCKED,
                reason=f"{rail.value} has an invalid live rail config and is blocked.",
            )
            continue
        normalized[rail] = LiveRailConfig(
            status=raw_config.get("status", LiveRailStatus.DISABLED),
            active=bool(raw_config.get("active", False)),
            reason=raw_config.get("reason"),
        )
    return normalized, tuple(unknown)


def _normalize_rail_status(status: LiveRailStatus | str) -> LiveRailStatus:
    if isinstance(status, LiveRailStatus):
        return status
    return LiveRailStatus(status)


def _result_is_not_ready_reason(result: GateResult | RailResult) -> bool:
    if isinstance(result, GateResult):
        return not result.satisfied
    return result.status is not LiveRailStatus.DISABLED or result.active


def _gate(
    gate: ReadinessGate,
    satisfied: bool,
    satisfied_reason: str,
    missing_reason: str,
) -> GateResult:
    if satisfied:
        return _satisfied_gate(gate, satisfied_reason)
    return _missing_gate(gate, missing_reason)


def _satisfied_gate(gate: ReadinessGate, reason: str) -> GateResult:
    return GateResult(gate=gate, status=GateStatus.SATISFIED, satisfied=True, reason=reason)


def _missing_gate(gate: ReadinessGate, reason: str) -> GateResult:
    return GateResult(gate=gate, status=GateStatus.MISSING, satisfied=False, reason=reason)


def _blocked_gate(gate: ReadinessGate, reason: str) -> GateResult:
    return GateResult(gate=gate, status=GateStatus.BLOCKED, satisfied=False, reason=reason)

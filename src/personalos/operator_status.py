"""Unified operator status report for inert/no-send Personal OS surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from personalos.path_safety import is_under_repo, is_under_temp
from personalos.pre_live_readiness import create_default_pre_live_readiness_report

OPERATOR_STATUS_SCHEMA_VERSION = "operator_status.v1"

SAFE_LOCAL_ACTIONS: tuple[str, ...] = (
    "Run readiness report",
    "Inspect local status",
    "Preview ChatGPT synthesis import",
    "Apply approved synthesis preview to local SQLite state only",
    "Generate no-send briefing preview",
    "Inspect side-effect/idempotency ledgers",
    "Preview simulated scheduler jobs",
)

BLOCKED_ACTIONS: tuple[str, ...] = (
    "Send Gmail",
    "Write Todoist",
    "Write Google Calendar",
    "Write PersonalOS Markdown",
    "Load credentials",
    "Activate scheduler/LaunchAgent/crontab/daemon/background loop",
    "Use production DB",
    "Call live model/API",
    "Call OpenClaw runtime",
)

_LIVE_RAIL_ALIASES: dict[str, str] = {
    "gmail": "gmail",
    "todoist": "todoist",
    "calendar": "google_calendar",
    "personalos_markdown": "personalos_markdown",
    "model_api": "live_model_api_calls",
    "openclaw": "openclaw_runtime_workflows",
}


def create_operator_status_report(
    *,
    readiness: Mapping[str, Any] | None = None,
    generated_at_utc: str | None = None,
    database_path: str | Path | None = None,
    database_access: str = "not_applicable",
    database_write: bool = False,
    external_write_ledger_counts: Mapping[str, int] | None = None,
    scheduler_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Build a stable, copy/paste-friendly operator status report.

    The report is assembled from existing inert/read-only readiness and local
    summary data. It does not open files, connect to providers, load
    credentials, mutate SQLite, or initialize external write clients.
    """
    readiness_summary = dict(readiness or create_default_pre_live_readiness_report())
    generated_at = generated_at_utc or _utc_now()
    live_rails = _live_rails(readiness_summary)
    live_rails_activated = bool(readiness_summary.get("live_rails_activated", False))
    readiness_status = str(readiness_summary.get("status", "unknown"))

    credential_status = _credential_status(readiness_summary)
    scheduler_status = _scheduler_status(
        readiness_summary,
        scheduler_counts=scheduler_counts,
    )
    production_db_status = _production_db_status(
        readiness_summary,
        database_path=database_path,
        database_access=database_access,
    )
    external_write_status = _external_write_status(
        readiness_summary,
        ledger_counts=external_write_ledger_counts,
    )

    evidence = {
        "readiness_evaluator_result": readiness_status,
        "inert_report_only": bool(readiness_summary.get("inert_report_only", False)),
        "live_rails_activated": live_rails_activated,
        "live_rails_disabled": _all_live_rails_disabled(live_rails),
        "disabled_live_rails": [
            rail_name
            for rail_name, rail in live_rails.items()
            if rail["status"] == "disabled" and rail["active"] is False
        ],
        "credential_loading": credential_status["evidence"],
        "external_write_clients_initialized": False,
        "scheduler_activated": scheduler_status["activated"],
        "production_db_active": production_db_status["active"],
        "database_write": database_write,
        "database_path_classification": production_db_status["path_classification"],
        "openclaw_called": bool(readiness_summary.get("openclaw_called", False)),
        "no_external_writes": external_write_status["no_external_writes"],
    }

    return {
        "schema_version": OPERATOR_STATUS_SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "source": {
            "component": "personalos.operator_status",
            "readiness_source": "personalos.pre_live_readiness",
        },
        "readiness_status": readiness_status,
        "mode": "inert_report_only",
        "inert_report_only": bool(readiness_summary.get("inert_report_only", False)),
        "live_rails_activated": live_rails_activated,
        "live_rails": live_rails,
        "scheduler_status": scheduler_status,
        "production_db_status": production_db_status,
        "credential_status": credential_status,
        "external_write_status": external_write_status,
        "safe_local_actions": list(SAFE_LOCAL_ACTIONS),
        "blocked_actions": list(BLOCKED_ACTIONS),
        "evidence": evidence,
        "warnings_or_blockers": _warnings_or_blockers(readiness_summary),
        "readiness_blocked_or_missing_gate_count": int(
            readiness_summary.get("blocked_or_missing_gate_count", 0)
        ),
        "readiness_blocked_or_non_disabled_rail_count": int(
            readiness_summary.get("blocked_or_non_disabled_rail_count", 0)
        ),
    }


def _live_rails(readiness: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    readiness_rails = {
        str(rail.get("rail")): rail
        for rail in readiness.get("rails", [])
        if isinstance(rail, Mapping)
    }
    rails: dict[str, dict[str, Any]] = {}
    for report_name, readiness_name in _LIVE_RAIL_ALIASES.items():
        source = readiness_rails.get(readiness_name, {})
        status = str(source.get("status", "unknown"))
        active = bool(source.get("active", False))
        rails[report_name] = {
            "status": status,
            "active": active,
            "source_rail": readiness_name,
            "reason": str(source.get("reason", "unavailable")),
        }
    return rails


def _all_live_rails_disabled(live_rails: Mapping[str, Mapping[str, Any]]) -> bool:
    return all(
        rail.get("status") == "disabled" and rail.get("active") is False
        for rail in live_rails.values()
    )


def _credential_status(readiness: Mapping[str, Any]) -> dict[str, Any]:
    loaded = bool(readiness.get("credentials_loaded", False))
    read = bool(readiness.get("credentials_read", False))
    return {
        "status": "not_loaded" if not loaded and not read else "loaded_or_read",
        "loaded": loaded,
        "read": read,
        "evidence": (
            "no credentials loaded/read"
            if not loaded and not read
            else "credential activity detected"
        ),
    }


def _scheduler_status(
    readiness: Mapping[str, Any],
    *,
    scheduler_counts: Mapping[str, int] | None,
) -> dict[str, Any]:
    activated = bool(readiness.get("scheduler_activated", False))
    counts = dict(scheduler_counts or {})
    return {
        "status": "active" if activated else "inactive",
        "activated": activated,
        "activation": "activated" if activated else "not_activated",
        "mode": "simulated_only",
        "scheduler_job_count": counts.get("scheduler_job_count"),
        "scheduler_run_count": counts.get("scheduler_run_count"),
    }


def _production_db_status(
    readiness: Mapping[str, Any],
    *,
    database_path: str | Path | None,
    database_access: str,
) -> dict[str, Any]:
    active = bool(readiness.get("production_db_path_active", False))
    path_report = _database_path_report(database_path)
    return {
        "status": "active" if active else "not_active",
        "active": active,
        "access": database_access,
        **path_report,
    }


def _database_path_report(database_path: str | Path | None) -> dict[str, Any]:
    if database_path is None:
        return {
            "path": None,
            "path_classification": "unavailable",
        }
    path = Path(database_path).expanduser().resolve()
    if is_under_temp(path):
        classification = "temp_dev_test_sqlite"
    elif is_under_repo(path):
        classification = "repo_local_dev_sqlite"
    else:
        classification = "unknown_explicit_sqlite"
    return {
        "path": str(path),
        "path_classification": classification,
    }


def _external_write_status(
    readiness: Mapping[str, Any],
    *,
    ledger_counts: Mapping[str, int] | None,
) -> dict[str, Any]:
    no_external_writes = bool(readiness.get("no_external_writes", True))
    external_services_contacted = bool(readiness.get("external_services_contacted", False))
    counts = dict(ledger_counts or {})
    return {
        "status": "none" if no_external_writes and not external_services_contacted else "detected",
        "no_external_writes": no_external_writes,
        "external_services_contacted": external_services_contacted,
        "write_clients_initialized": False,
        "ledger_counts_available": ledger_counts is not None,
        "external_write_intent_count": counts.get("external_write_intents"),
        "external_write_attempt_count": counts.get("external_write_attempts"),
        "idempotency_record_count": counts.get("idempotency_records"),
    }


def _warnings_or_blockers(readiness: Mapping[str, Any]) -> list[str]:
    reasons = readiness.get("reasons")
    blockers = list(reasons) if isinstance(reasons, list) else []
    status = str(readiness.get("status", "unknown"))
    if status != "ready":
        return ["Personal OS is not ready for live operation.", *blockers]
    return blockers


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

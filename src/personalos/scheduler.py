"""No-send scheduler/runtime-loop simulation foundation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.config import DEFAULT_TIMEZONE
from personalos.path_safety import validate_output_file_path

SCHEDULER_JOB_TYPES = (
    "today_view",
    "briefing_preview",
    "status_summary",
    "synthesis_apply_summary",
    "side_effect_summary",
    "dashboard_render_preview",
    "other",
)
SIMULATED_JOB_TYPES = (
    "today_view",
    "briefing_preview",
    "status_summary",
    "synthesis_apply_summary",
    "side_effect_summary",
    "dashboard_render_preview",
)
SCHEDULER_CADENCE_TYPES = (
    "manual",
    "daily",
    "weekdays",
    "specific_times",
    "interval_minutes",
)
SCHEDULER_JOB_STATUSES = ("draft", "enabled_dev_test", "disabled", "blocked")
SCHEDULER_RUN_TYPES = ("manual_simulated", "due_check_simulated", "no_send_preview")
SCHEDULER_RUN_STATUSES = ("completed", "blocked", "failed", "skipped")
BRIEFING_WINDOWS = ("morning", "midday", "afternoon", "evening")
SAFE_NO_SEND_SEED_PROFILE = "safe_no_send"

SCHEDULER_SAFETY_FLAGS = {
    "no_send_mode": True,
    "no_external_writes": True,
    "fake_model_only": True,
    "live_write": False,
    "external_mutation": False,
    "scheduler_activation": False,
    "launch_agent_installed": False,
    "no_live_model_call": True,
    "no_todoist_writes": True,
    "no_calendar_writes": True,
    "no_gmail_send": True,
    "no_gmail_draft": True,
    "no_personalos_writes": True,
}

_FORBIDDEN_JOB_TYPE_MARKERS = (
    "gmail",
    "todoist_write",
    "calendar_write",
    "personalos_markdown",
    "launchagent",
    "launch_agent",
    "crontab",
    "daemon",
    "background",
    "production",
    "activate",
    "live_model",
    "openai",
    "openrouter",
    "anthropic",
    "send",
    "draft",
)


class SchedulerValidationError(ValueError):
    """Raised when scheduler job or run input is not Phase 13C safe."""


def build_scheduler_job_definition(
    *,
    scheduler_job_id: str | None = None,
    name: str,
    job_type: str,
    cadence_type: str,
    schedule_json: Mapping[str, Any] | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    enabled: bool = False,
    no_send_mode: bool = True,
    no_external_writes: bool = True,
    fake_model_only: bool = True,
    target_window: str | None = None,
    status: str = "draft",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    job_type = validate_scheduler_job_type(job_type)
    cadence_type = validate_cadence_type(cadence_type)
    schedule = validate_schedule_json(schedule_json or {}, cadence_type=cadence_type)
    timezone_name = validate_timezone(timezone)
    target_window = validate_target_window(target_window, job_type=job_type)
    status = validate_job_status(status)
    enabled = _validate_bool("enabled", enabled)
    _validate_true("no_send_mode", no_send_mode)
    _validate_true("no_external_writes", no_external_writes)
    _validate_true("fake_model_only", fake_model_only)
    if status == "enabled_dev_test" and not enabled:
        raise SchedulerValidationError("enabled_dev_test scheduler jobs must set enabled=true")
    if job_type == "other" and status == "enabled_dev_test":
        raise SchedulerValidationError("other scheduler jobs cannot be enabled for simulation")

    created = validate_iso_datetime("created_at", created_at or _utc_now())
    updated = validate_iso_datetime("updated_at", updated_at or created)
    job_id = (
        _validate_required_text("scheduler_job_id", scheduler_job_id)
        if scheduler_job_id is not None
        else stable_scheduler_id("scheduler-job", f"{job_type}|{name}|{timezone_name}")
    )
    return {
        "scheduler_job_id": job_id,
        "name": _validate_required_text("name", name),
        "job_type": job_type,
        "cadence_type": cadence_type,
        "schedule_json": schedule,
        "timezone": timezone_name,
        "enabled": enabled,
        "no_send_mode": True,
        "no_external_writes": True,
        "fake_model_only": True,
        "target_window": target_window,
        "status": status,
        "created_at": created,
        "updated_at": updated,
    }


def create_scheduler_job_record(
    connection: sqlite3.Connection,
    **job_input: Any,
) -> dict[str, Any]:
    job = build_scheduler_job_definition(**job_input)
    with connection:
        connection.execute(
            """
            INSERT INTO scheduler_jobs (
                scheduler_job_id,
                name,
                job_type,
                cadence_type,
                schedule_json,
                timezone,
                enabled,
                no_send_mode,
                no_external_writes,
                fake_model_only,
                target_window,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scheduler_job_id) DO UPDATE SET
                name = excluded.name,
                job_type = excluded.job_type,
                cadence_type = excluded.cadence_type,
                schedule_json = excluded.schedule_json,
                timezone = excluded.timezone,
                enabled = excluded.enabled,
                no_send_mode = excluded.no_send_mode,
                no_external_writes = excluded.no_external_writes,
                fake_model_only = excluded.fake_model_only,
                target_window = excluded.target_window,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                job["scheduler_job_id"],
                job["name"],
                job["job_type"],
                job["cadence_type"],
                _json_dumps(job["schedule_json"]),
                job["timezone"],
                int(job["enabled"]),
                1,
                1,
                1,
                job["target_window"],
                job["status"],
                job["created_at"],
                job["updated_at"],
            ),
        )
    persisted = get_scheduler_job(connection, job["scheduler_job_id"])
    if persisted is None:
        raise RuntimeError(f"Scheduler job was not persisted: {job['scheduler_job_id']}")
    return persisted


def seed_dev_scheduler_jobs(
    connection: sqlite3.Connection,
    *,
    profile: str = SAFE_NO_SEND_SEED_PROFILE,
    timezone: str = DEFAULT_TIMEZONE,
    created_at: str | None = None,
) -> dict[str, Any]:
    if profile != SAFE_NO_SEND_SEED_PROFILE:
        raise SchedulerValidationError(f"scheduler seed profile must be: {SAFE_NO_SEND_SEED_PROFILE}")
    timezone_name = validate_timezone(timezone)
    created = validate_iso_datetime("created_at", created_at or _utc_now())
    jobs = [
        create_scheduler_job_record(connection, **job)
        for job in _safe_seed_job_definitions(timezone_name=timezone_name, created_at=created)
    ]
    return {
        "status": "seeded",
        "profile": profile,
        "database_write": True,
        "scheduler_job_count": len(jobs),
        "scheduler_jobs": jobs,
        **SCHEDULER_SAFETY_FLAGS,
    }


def list_scheduler_jobs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT *
        FROM scheduler_jobs
        ORDER BY job_type, name, scheduler_job_id
        """
    ).fetchall()
    return [_job_row_to_dict(row) for row in rows]


def get_scheduler_job(
    connection: sqlite3.Connection,
    scheduler_job_id: str,
) -> dict[str, Any] | None:
    scheduler_job_id = _validate_required_text("scheduler_job_id", scheduler_job_id)
    row = connection.execute(
        """
        SELECT *
        FROM scheduler_jobs
        WHERE scheduler_job_id = ?
        """,
        (scheduler_job_id,),
    ).fetchone()
    return _job_row_to_dict(row) if row is not None else None


def list_scheduler_runs(
    connection: sqlite3.Connection,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None and (type(limit) is not int or limit < 0):
        raise SchedulerValidationError("limit must be a non-negative integer")
    sql = """
        SELECT *
        FROM scheduler_runs
        ORDER BY started_at DESC, scheduler_run_id
    """
    values: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        values = (limit,)
    rows = connection.execute(sql, values).fetchall()
    return [_run_row_to_dict(row) for row in rows]


def count_scheduler_jobs(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "scheduler_jobs")


def count_scheduler_runs(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "scheduler_runs")


def summarize_scheduler(connection: sqlite3.Connection) -> dict[str, Any]:
    jobs = list_scheduler_jobs(connection)
    runs = list_scheduler_runs(connection, limit=5)
    latest_run = runs[0] if runs else None
    blocked_or_failed_jobs = [
        job for job in jobs if job["status"] == "blocked"
    ]
    blocked_or_failed_runs = [
        run for run in runs if run["status"] in {"blocked", "failed"}
    ]
    warnings: list[str] = []
    if blocked_or_failed_jobs:
        warnings.append("One or more scheduler jobs are blocked.")
    if blocked_or_failed_runs:
        warnings.append("One or more recent simulated scheduler runs were blocked or failed.")
    return {
        "scheduler_job_count": len(jobs),
        "scheduler_run_count": count_scheduler_runs(connection),
        "enabled_dev_test_job_count": sum(
            1 for job in jobs if job["enabled"] and job["status"] == "enabled_dev_test"
        ),
        "counts_by_job_type": _count_by_key(jobs, "job_type"),
        "counts_by_job_status": _count_by_key(jobs, "status"),
        "counts_by_run_status": _grouped_counts(connection, "scheduler_runs", "status"),
        "latest_scheduler_run_id": (
            latest_run["scheduler_run_id"] if latest_run is not None else None
        ),
        "latest_job_type": latest_run["job_type"] if latest_run is not None else None,
        "latest_status": latest_run["status"] if latest_run is not None else None,
        "recent_runs": runs,
        "warnings": warnings,
        "read_only": True,
        **SCHEDULER_SAFETY_FLAGS,
    }


def preview_scheduler_jobs(
    connection: sqlite3.Connection,
    *,
    source_date: date | str,
    timezone: str = DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    source_date_iso = validate_iso_date("source_date", source_date)
    timezone_name = validate_timezone(timezone)
    parsed_date = date.fromisoformat(source_date_iso)
    jobs = list_scheduler_jobs(connection)
    previews = [
        _preview_job(job, source_date=parsed_date, timezone_name=timezone_name)
        for job in jobs
    ]
    return {
        "status": "completed",
        "database_write": False,
        "source_date": source_date_iso,
        "timezone": timezone_name,
        "scheduler_job_count": len(jobs),
        "due_simulated_job_count": sum(1 for preview in previews if preview["would_run"]),
        "job_previews": previews,
        **SCHEDULER_SAFETY_FLAGS,
    }


def run_scheduler_job_simulated(
    connection: sqlite3.Connection,
    *,
    job_type: str | None = None,
    scheduler_job_id: str | None = None,
    run_type: str = "manual_simulated",
    source_date: date | str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    briefing_window_name: str | None = None,
    output_file: str | Path | None = None,
    scheduled_for: str | None = None,
    run_at: str | None = None,
) -> dict[str, Any]:
    started = validate_iso_datetime("run_at", run_at or _utc_now())
    run_type = validate_run_type(run_type)
    timezone_name = validate_timezone(timezone)
    job = _resolve_run_job(connection, scheduler_job_id=scheduler_job_id, job_type=job_type)
    resolved_job_type = validate_simulated_job_type(str(job["job_type"]))
    source_date_iso = _source_date_for_run(
        source_date,
        job_type=resolved_job_type,
        timezone_name=timezone_name,
    )
    window_name = _briefing_window_for_run(
        briefing_window_name,
        job=job,
        job_type=resolved_job_type,
    )
    scheduled_for = _normalize_optional_datetime("scheduled_for", scheduled_for)

    status = "completed"
    reason = None
    try:
        _ensure_job_runnable(job)
        workflow_report = _run_simulated_workflow(
            connection,
            job_type=resolved_job_type,
            source_date=source_date_iso,
            timezone=timezone_name,
            briefing_window_name=window_name,
            output_file=output_file,
        )
        workflow_status = str(workflow_report.get("status", "completed"))
        if workflow_status in {"blocked", "rejected"}:
            status = "blocked"
        elif workflow_status in {"failed", "error"}:
            status = "failed"
    except (SchedulerValidationError, ValueError, PermissionError) as error:
        status = "blocked"
        reason = str(error)
        workflow_report = {
            "status": "blocked",
            "reason": reason,
            "database_write": False,
            **SCHEDULER_SAFETY_FLAGS,
        }
    completed = _utc_now()
    completion_report = build_scheduler_completion_report(
        status=status,
        job=job,
        run_type=run_type,
        source_date=source_date_iso,
        timezone=timezone_name,
        briefing_window_name=window_name,
        scheduled_for=scheduled_for,
        started_at=started,
        completed_at=completed,
        workflow_report=workflow_report,
        reason=reason,
    )
    scheduler_run_id = stable_scheduler_id(
        "scheduler-run",
        "|".join(
            (
                str(job.get("scheduler_job_id") or "adhoc"),
                resolved_job_type,
                run_type,
                scheduled_for or "unscheduled",
                started,
            )
        ),
    )
    run = _record_scheduler_run(
        connection,
        scheduler_run_id=scheduler_run_id,
        scheduler_job_id=job.get("scheduler_job_id"),
        job_type=resolved_job_type,
        run_type=run_type,
        scheduled_for=scheduled_for,
        started_at=started,
        completed_at=completed,
        status=status,
        completion_report=completion_report,
    )
    return {
        "status": status,
        "database_write": True,
        "scheduler_run": run,
        "completion_report": completion_report,
        "workflow_report": workflow_report,
        **SCHEDULER_SAFETY_FLAGS,
    }


def build_scheduler_completion_report(
    *,
    status: str,
    job: Mapping[str, Any],
    run_type: str,
    source_date: str | None,
    timezone: str,
    briefing_window_name: str | None,
    scheduled_for: str | None,
    started_at: str,
    completed_at: str,
    workflow_report: Mapping[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    status = validate_run_status(status)
    return {
        "status": status,
        "reason": reason,
        "scheduler_job_id": job.get("scheduler_job_id"),
        "job_type": job["job_type"],
        "run_type": run_type,
        "source_date": source_date,
        "timezone": timezone,
        "briefing_window_name": briefing_window_name,
        "scheduled_for": scheduled_for,
        "started_at": started_at,
        "completed_at": completed_at,
        "workflow_report": dict(workflow_report),
        "warnings": _completion_warnings(status=status, workflow_report=workflow_report),
        "foreground_synchronous": True,
        "daemonized": False,
        "background_process_started": False,
        **SCHEDULER_SAFETY_FLAGS,
    }


def validate_scheduler_job_type(job_type: str) -> str:
    normalized = _normalize_token("job_type", job_type)
    if normalized not in SCHEDULER_JOB_TYPES and any(
        marker in normalized for marker in _FORBIDDEN_JOB_TYPE_MARKERS
    ):
        raise SchedulerValidationError(f"prohibited scheduler job_type is blocked: {normalized}")
    if normalized not in SCHEDULER_JOB_TYPES:
        allowed = ", ".join(SCHEDULER_JOB_TYPES)
        raise SchedulerValidationError(f"job_type must be one of: {allowed}")
    return normalized


def validate_simulated_job_type(job_type: str) -> str:
    normalized = validate_scheduler_job_type(job_type)
    if normalized not in SIMULATED_JOB_TYPES:
        allowed = ", ".join(SIMULATED_JOB_TYPES)
        raise SchedulerValidationError(f"job_type is not allowed for simulated runs: {allowed}")
    return normalized


def validate_cadence_type(cadence_type: str) -> str:
    normalized = _normalize_token("cadence_type", cadence_type)
    if normalized not in SCHEDULER_CADENCE_TYPES:
        allowed = ", ".join(SCHEDULER_CADENCE_TYPES)
        raise SchedulerValidationError(f"cadence_type must be one of: {allowed}")
    return normalized


def validate_schedule_json(
    schedule_json: Mapping[str, Any],
    *,
    cadence_type: str,
) -> dict[str, Any]:
    if not isinstance(schedule_json, Mapping):
        raise SchedulerValidationError("schedule_json must be an object")
    schedule = dict(schedule_json)
    if cadence_type == "specific_times":
        times = schedule.get("times")
        if not isinstance(times, list) or not times:
            raise SchedulerValidationError("specific_times cadence requires a non-empty times list")
        for value in times:
            _validate_hhmm_time("schedule_json.times", value)
    if cadence_type == "interval_minutes":
        interval = schedule.get("interval_minutes")
        if type(interval) is not int or interval <= 0:
            raise SchedulerValidationError(
                "interval_minutes cadence requires a positive interval_minutes integer"
            )
    if "install_launch_agent" in schedule or "activate_scheduler" in schedule:
        raise SchedulerValidationError("scheduler activation settings are blocked in Phase 13C")
    return schedule


def validate_timezone(timezone: str) -> str:
    timezone_name = _validate_required_text("timezone", timezone)
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise SchedulerValidationError("timezone must be a valid IANA timezone name") from error
    return timezone_name


def validate_iso_date(field_name: str, value: date | str) -> str:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise SchedulerValidationError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise SchedulerValidationError(f"{field_name} must be an ISO date") from error


def validate_iso_datetime(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SchedulerValidationError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchedulerValidationError(f"{field_name} must include a timezone offset")
    return value


def validate_target_window(target_window: str | None, *, job_type: str) -> str | None:
    if target_window is None:
        return None
    target_window = _normalize_token("target_window", target_window)
    if target_window not in BRIEFING_WINDOWS:
        allowed = ", ".join(BRIEFING_WINDOWS)
        raise SchedulerValidationError(f"target_window must be one of: {allowed}")
    if job_type != "briefing_preview":
        raise SchedulerValidationError("target_window is only valid for briefing_preview jobs")
    return target_window


def validate_job_status(status: str) -> str:
    normalized = _normalize_token("status", status)
    if normalized not in SCHEDULER_JOB_STATUSES:
        allowed = ", ".join(SCHEDULER_JOB_STATUSES)
        raise SchedulerValidationError(f"status must be one of: {allowed}")
    return normalized


def validate_run_type(run_type: str) -> str:
    normalized = _normalize_token("run_type", run_type)
    if normalized not in SCHEDULER_RUN_TYPES:
        allowed = ", ".join(SCHEDULER_RUN_TYPES)
        raise SchedulerValidationError(f"run_type must be one of: {allowed}")
    return normalized


def validate_run_status(status: str) -> str:
    normalized = _normalize_token("status", status)
    if normalized not in SCHEDULER_RUN_STATUSES:
        allowed = ", ".join(SCHEDULER_RUN_STATUSES)
        raise SchedulerValidationError(f"status must be one of: {allowed}")
    return normalized


def stable_scheduler_id(prefix: str, material: str) -> str:
    prefix = _normalize_token("prefix", prefix)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _run_simulated_workflow(
    connection: sqlite3.Connection,
    *,
    job_type: str,
    source_date: str | None,
    timezone: str,
    briefing_window_name: str | None,
    output_file: str | Path | None,
) -> dict[str, Any]:
    if job_type == "status_summary":
        from personalos.status import create_status_summary

        return {
            "status": "completed",
            "workflow": job_type,
            "database_write": False,
            "summary": create_status_summary(connection),
            **SCHEDULER_SAFETY_FLAGS,
        }
    if job_type == "today_view":
        from personalos.today import create_today_view_summary

        return {
            "status": "completed",
            "workflow": job_type,
            "database_write": False,
            "summary": create_today_view_summary(
                connection,
                source_date=source_date,
                timezone=timezone,
            ),
            **SCHEDULER_SAFETY_FLAGS,
        }
    if job_type == "side_effect_summary":
        from personalos.side_effects import summarize_side_effect_ledgers

        return {
            "status": "completed",
            "workflow": job_type,
            "database_write": False,
            "summary": summarize_side_effect_ledgers(connection),
            **SCHEDULER_SAFETY_FLAGS,
        }
    if job_type == "synthesis_apply_summary":
        from personalos.synthesis_apply import summarize_synthesis_apply_runs

        return {
            "status": "completed",
            "workflow": job_type,
            "database_write": False,
            "summary": summarize_synthesis_apply_runs(connection),
            **SCHEDULER_SAFETY_FLAGS,
        }
    if job_type == "briefing_preview":
        from personalos.briefings import generate_no_send_briefing_preview

        if source_date is None or briefing_window_name is None:
            raise SchedulerValidationError(
                "briefing_preview simulated runs require source_date and briefing_window_name"
            )
        result = generate_no_send_briefing_preview(
            connection,
            source_date=source_date,
            timezone=timezone,
            briefing_window_name=briefing_window_name,
            delivery_mode="no_send",
        )
        return {
            "workflow": job_type,
            "database_write": result.get("status") == "generated",
            **result,
            **SCHEDULER_SAFETY_FLAGS,
        }
    if job_type == "dashboard_render_preview":
        from personalos.dashboard import render_today_view_html_from_connection

        if source_date is None:
            raise SchedulerValidationError("dashboard_render_preview requires source_date")
        if output_file is None:
            raise SchedulerValidationError(
                "dashboard_render_preview requires an explicit safe output_file"
            )
        output_path = validate_output_file_path(
            output_file,
            path_label="scheduler output_file",
        )
        html = render_today_view_html_from_connection(
            connection,
            source_date=source_date,
            timezone=timezone,
            include_synthesis_import_form=False,
        )
        output_path.write_text(html, encoding="utf-8")
        return {
            "status": "completed",
            "workflow": job_type,
            "database_write": False,
            "file_write": True,
            "output_file": str(output_path),
            "static_html_only": True,
            **SCHEDULER_SAFETY_FLAGS,
        }
    raise SchedulerValidationError(f"unsupported simulated scheduler job_type: {job_type}")


def _record_scheduler_run(
    connection: sqlite3.Connection,
    *,
    scheduler_run_id: str,
    scheduler_job_id: str | None,
    job_type: str,
    run_type: str,
    scheduled_for: str | None,
    started_at: str,
    completed_at: str,
    status: str,
    completion_report: Mapping[str, Any],
) -> dict[str, Any]:
    with connection:
        connection.execute(
            """
            INSERT INTO scheduler_runs (
                scheduler_run_id,
                scheduler_job_id,
                job_type,
                run_type,
                scheduled_for,
                started_at,
                completed_at,
                status,
                completion_report_json,
                no_send_mode,
                no_external_writes,
                live_write,
                external_mutation,
                scheduler_activation,
                launch_agent_installed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scheduler_run_id,
                scheduler_job_id,
                job_type,
                run_type,
                scheduled_for,
                started_at,
                completed_at,
                status,
                _json_dumps(completion_report),
                1,
                1,
                0,
                0,
                0,
                0,
            ),
        )
    row = connection.execute(
        """
        SELECT *
        FROM scheduler_runs
        WHERE scheduler_run_id = ?
        """,
        (scheduler_run_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Scheduler run was not persisted: {scheduler_run_id}")
    return _run_row_to_dict(row)


def _resolve_run_job(
    connection: sqlite3.Connection,
    *,
    scheduler_job_id: str | None,
    job_type: str | None,
) -> dict[str, Any]:
    if scheduler_job_id is not None:
        job = get_scheduler_job(connection, scheduler_job_id)
        if job is None:
            raise SchedulerValidationError(f"scheduler job not found: {scheduler_job_id}")
        if job_type is not None and validate_scheduler_job_type(job_type) != job["job_type"]:
            raise SchedulerValidationError("job_type does not match scheduler_job_id")
        return job
    if job_type is None:
        raise SchedulerValidationError("scheduler run requires job_type or scheduler_job_id")
    resolved_job_type = validate_simulated_job_type(job_type)
    return {
        "scheduler_job_id": None,
        "name": f"Ad-hoc {resolved_job_type}",
        "job_type": resolved_job_type,
        "cadence_type": "manual",
        "schedule_json": {},
        "timezone": DEFAULT_TIMEZONE,
        "enabled": True,
        "no_send_mode": True,
        "no_external_writes": True,
        "fake_model_only": True,
        "target_window": None,
        "status": "enabled_dev_test",
    }


def _ensure_job_runnable(job: Mapping[str, Any]) -> None:
    if job.get("no_send_mode") is not True:
        raise SchedulerValidationError("scheduler job must keep no_send_mode=true")
    if job.get("no_external_writes") is not True:
        raise SchedulerValidationError("scheduler job must keep no_external_writes=true")
    if job.get("fake_model_only") is not True:
        raise SchedulerValidationError("scheduler job must keep fake_model_only=true")
    if job.get("status") == "blocked":
        raise SchedulerValidationError("scheduler job is blocked")
    if job.get("status") == "disabled":
        raise SchedulerValidationError("scheduler job is disabled")
    if job.get("scheduler_job_id") is not None and (
        job.get("status") != "enabled_dev_test" or job.get("enabled") is not True
    ):
        raise SchedulerValidationError(
            "stored scheduler jobs must be enabled_dev_test before simulation"
        )


def _source_date_for_run(
    source_date: date | str | None,
    *,
    job_type: str,
    timezone_name: str,
) -> str | None:
    if job_type in {"today_view", "briefing_preview", "dashboard_render_preview"}:
        if source_date is None:
            raise SchedulerValidationError(f"{job_type} requires source_date")
        return validate_iso_date("source_date", source_date)
    if source_date is None:
        return None
    return validate_iso_date("source_date", source_date)


def _briefing_window_for_run(
    briefing_window_name: str | None,
    *,
    job: Mapping[str, Any],
    job_type: str,
) -> str | None:
    if job_type != "briefing_preview":
        if briefing_window_name is not None:
            raise SchedulerValidationError("window is only valid for briefing_preview runs")
        return None
    window = briefing_window_name or job.get("target_window")
    if window is None:
        raise SchedulerValidationError("briefing_preview requires a briefing window")
    return validate_target_window(str(window), job_type=job_type)


def _safe_seed_job_definitions(
    *,
    timezone_name: str,
    created_at: str,
) -> list[dict[str, Any]]:
    shared = {
        "timezone": timezone_name,
        "enabled": True,
        "status": "enabled_dev_test",
        "created_at": created_at,
        "updated_at": created_at,
    }
    return [
        {
            **shared,
            "scheduler_job_id": "scheduler-job-status-summary-dev",
            "name": "Status summary dev/test simulation",
            "job_type": "status_summary",
            "cadence_type": "manual",
            "schedule_json": {"profile": SAFE_NO_SEND_SEED_PROFILE},
        },
        {
            **shared,
            "scheduler_job_id": "scheduler-job-today-view-dev",
            "name": "Today View dev/test simulation",
            "job_type": "today_view",
            "cadence_type": "daily",
            "schedule_json": {"time": "06:00"},
        },
        {
            **shared,
            "scheduler_job_id": "scheduler-job-morning-briefing-preview-dev",
            "name": "Morning briefing no-send preview simulation",
            "job_type": "briefing_preview",
            "cadence_type": "daily",
            "schedule_json": {"time": "06:30"},
            "target_window": "morning",
        },
        {
            **shared,
            "scheduler_job_id": "scheduler-job-side-effect-summary-dev",
            "name": "Side-effect ledger summary dev/test simulation",
            "job_type": "side_effect_summary",
            "cadence_type": "manual",
            "schedule_json": {"profile": SAFE_NO_SEND_SEED_PROFILE},
        },
        {
            **shared,
            "scheduler_job_id": "scheduler-job-synthesis-apply-summary-dev",
            "name": "Synthesis apply summary dev/test simulation",
            "job_type": "synthesis_apply_summary",
            "cadence_type": "manual",
            "schedule_json": {"profile": SAFE_NO_SEND_SEED_PROFILE},
        },
    ]


def _preview_job(
    job: Mapping[str, Any],
    *,
    source_date: date,
    timezone_name: str,
) -> dict[str, Any]:
    if job["status"] != "enabled_dev_test" or job["enabled"] is not True:
        return _preview_result(job, would_run=False, reason="job is not enabled_dev_test")
    if job["timezone"] != timezone_name:
        return _preview_result(job, would_run=False, reason="timezone does not match")
    cadence = job["cadence_type"]
    if cadence == "manual":
        return _preview_result(job, would_run=False, reason="manual jobs do not run automatically")
    if cadence == "daily":
        return _preview_result(job, would_run=True, reason="daily dev/test simulation")
    if cadence == "weekdays":
        return _preview_result(
            job,
            would_run=source_date.weekday() < 5,
            reason="weekday dev/test simulation",
        )
    if cadence == "specific_times":
        times = job["schedule_json"].get("times", [])
        return _preview_result(
            job,
            would_run=bool(times),
            reason="specific_times dev/test simulation",
        )
    if cadence == "interval_minutes":
        return _preview_result(
            job,
            would_run=False,
            reason="interval preview never activates a scheduler in Phase 13C",
        )
    return _preview_result(job, would_run=False, reason="unsupported cadence")


def _preview_result(
    job: Mapping[str, Any],
    *,
    would_run: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "scheduler_job_id": job["scheduler_job_id"],
        "name": job["name"],
        "job_type": job["job_type"],
        "cadence_type": job["cadence_type"],
        "status": job["status"],
        "enabled": job["enabled"],
        "would_run": would_run,
        "reason": reason,
        **SCHEDULER_SAFETY_FLAGS,
    }


def _job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "scheduler_job_id": row["scheduler_job_id"],
        "name": row["name"],
        "job_type": row["job_type"],
        "cadence_type": row["cadence_type"],
        "schedule_json": _json_loads_object(row["schedule_json"]),
        "timezone": row["timezone"],
        "enabled": bool(row["enabled"]),
        "no_send_mode": bool(row["no_send_mode"]),
        "no_external_writes": bool(row["no_external_writes"]),
        "fake_model_only": bool(row["fake_model_only"]),
        "target_window": row["target_window"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "scheduler_run_id": row["scheduler_run_id"],
        "scheduler_job_id": row["scheduler_job_id"],
        "job_type": row["job_type"],
        "run_type": row["run_type"],
        "scheduled_for": row["scheduled_for"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "status": row["status"],
        "completion_report_json": _json_loads_object(row["completion_report_json"]),
        "no_send_mode": bool(row["no_send_mode"]),
        "no_external_writes": bool(row["no_external_writes"]),
        "live_write": bool(row["live_write"]),
        "external_mutation": bool(row["external_mutation"]),
        "scheduler_activation": bool(row["scheduler_activation"]),
        "launch_agent_installed": bool(row["launch_agent_installed"]),
    }


def _grouped_counts(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> dict[str, int]:
    if table_name != "scheduler_runs":
        raise SchedulerValidationError(f"unsupported scheduler summary table: {table_name}")
    if column_name != "status":
        raise SchedulerValidationError(f"unsupported scheduler summary column: {column_name}")
    rows = connection.execute(
        f"""
        SELECT {column_name} AS value, COUNT(*) AS value_count
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY {column_name}
        """
    ).fetchall()
    return {row["value"]: int(row["value_count"]) for row in rows}


def _count_by_key(items: list[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])


def _completion_warnings(
    *,
    status: str,
    workflow_report: Mapping[str, Any],
) -> list[str]:
    warnings = [
        "Phase 13C scheduler run is manual/foreground simulation only.",
        "No LaunchAgent, crontab, daemon, or production scheduler was activated.",
    ]
    workflow_warnings = workflow_report.get("warnings")
    if isinstance(workflow_warnings, list):
        warnings.extend(str(warning) for warning in workflow_warnings)
    if status != "completed":
        warnings.append("Scheduler simulation did not complete successfully.")
    return warnings


def _validate_hhmm_time(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as error:
        raise SchedulerValidationError(f"{field_name} values must use HH:MM") from error
    return parsed.strftime("%H:%M")


def _normalize_optional_datetime(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return validate_iso_datetime(field_name, value)


def _validate_required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchedulerValidationError(f"{field_name} must not be empty")
    return value.strip()


def _normalize_token(field_name: str, value: Any) -> str:
    return _validate_required_text(field_name, value).lower().replace("-", "_").replace(" ", "_")


def _validate_bool(field_name: str, value: bool) -> bool:
    if type(value) is not bool:
        raise SchedulerValidationError(f"{field_name} must be a boolean")
    return value


def _validate_true(field_name: str, value: bool) -> None:
    if _validate_bool(field_name, value) is not True:
        raise SchedulerValidationError(f"{field_name} must be true")


def _json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_loads_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("stored JSON must decode to an object")
    return parsed


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

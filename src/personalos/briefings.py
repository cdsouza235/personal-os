"""No-send daily briefing loop foundation for local/dev preview runtime DBs."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.composer import (
    ComposerAdapter,
    FAKE_COMPOSER_ADAPTER_NAME,
    FakeComposerAdapter,
    build_composer_packet_from_state,
    run_fake_composer_model,
    stable_composer_id,
)
from personalos.config import DEFAULT_TIMEZONE
from personalos.permissions import evaluate_auto_write_gate
from personalos.state import (
    count_briefing_outputs,
    count_daily_plans,
    create_briefing_output,
    create_daily_plan,
    get_briefing_output,
    get_daily_plan,
    list_briefing_outputs,
    list_daily_plans,
    summarize_priorities,
)
from personalos.today import create_today_view_summary

BRIEFING_LOOP_READ_PERMISSION = "briefing_loop_dev_test_read"
BRIEFING_LOOP_WRITE_PERMISSION = "briefing_loop_dev_test_write"
BRIEFING_LOOP_RUN_PERMISSION = "briefing_loop_dev_test_run"

BRIEFING_WINDOW_NAMES = ("morning", "midday", "afternoon", "evening")
BRIEFING_WINDOW_STATUSES_FOR_PREVIEW = ("draft", "active")
BRIEFING_DELIVERY_MODES = ("no_send", "manual_export")


class BriefingLoopPermissionDenied(PermissionError):
    """Raised when briefing loop permissions do not allow the requested action."""


class BriefingLoopValidationError(ValueError):
    """Raised when a no-send briefing preview cannot be generated safely."""


def build_no_send_daily_plan(
    connection: sqlite3.Connection,
    *,
    source_date: date | str,
    timezone: str = DEFAULT_TIMEZONE,
    generated_at: str | None = None,
) -> dict[str, Any]:
    source_date_iso = _validate_iso_date("source_date", source_date)
    timezone_name = _validate_timezone(timezone)
    generated = _validate_iso_datetime("generated_at", generated_at or _utc_now())
    today_summary = create_today_view_summary(
        connection,
        source_date=source_date_iso,
        timezone=timezone_name,
    )
    windows = _list_active_or_draft_briefing_windows(connection, timezone_name=timezone_name)

    return {
        "source_date": source_date_iso,
        "timezone": timezone_name,
        "generated_at": generated,
        "today_view_summary": today_summary,
        "active_or_draft_briefing_windows": windows,
        "routine_summary": today_summary["routine_summary"],
        "priority_summary": summarize_priorities(connection),
        "followup_summary": today_summary["followup_summary"],
        "todoist_candidate_summary": today_summary["todoist_candidate_summary"],
        "calendar_block_summary": today_summary["calendar_block_summary"],
        "warnings": [
            "No-send daily plan preview only.",
            "No external writes are performed by the briefing loop foundation.",
        ],
        "no_external_writes": True,
        "no_send_mode": True,
    }


def select_briefing_window(
    connection: sqlite3.Connection,
    *,
    source_date: date | str,
    timezone: str = DEFAULT_TIMEZONE,
    briefing_window_name: str,
) -> dict[str, Any]:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return _select_briefing_window_unchecked(
        connection,
        source_date=source_date,
        timezone=timezone,
        briefing_window_name=briefing_window_name,
    )


def generate_no_send_briefing_preview(
    connection: sqlite3.Connection,
    *,
    source_date: date | str,
    timezone: str = DEFAULT_TIMEZONE,
    briefing_window_name: str,
    delivery_mode: str = "no_send",
    adapter: ComposerAdapter | None = None,
    run_at: str | None = None,
) -> dict[str, Any]:
    source_date_iso = _validate_iso_date("source_date", source_date)
    timezone_name = _validate_timezone(timezone)
    briefing_window_name = _validate_briefing_window_name(briefing_window_name)
    delivery_mode = _validate_delivery_mode(delivery_mode)
    started_at = _validate_iso_datetime("run_at", run_at or _utc_now())
    selected_adapter = _require_fake_composer_adapter(adapter or FakeComposerAdapter())

    permissions = _evaluate_generation_permissions(connection)
    denied = next((permission for permission in permissions.values() if not permission["allowed"]), None)
    if denied is not None:
        return _blocked_result(
            reason=denied["reason"],
            source_date=source_date_iso,
            timezone=timezone_name,
            briefing_window_name=briefing_window_name,
            delivery_mode=delivery_mode,
            permissions=permissions,
        )

    window = _select_briefing_window_unchecked(
        connection,
        source_date=source_date_iso,
        timezone=timezone_name,
        briefing_window_name=briefing_window_name,
    )
    daily_plan = _ensure_daily_plan(
        connection,
        source_date=source_date_iso,
        timezone=timezone_name,
        generated_at=started_at,
    )
    packet_id = stable_composer_id(
        "briefing-packet",
        f"{daily_plan['id']}|{briefing_window_name}|{started_at}",
    )
    packet = build_composer_packet_from_state(
        connection,
        packet_id=packet_id,
        packet_type="window_brief",
        briefing_window=briefing_window_name,
        source_date=source_date_iso,
        timezone=timezone_name,
        generated_at=started_at,
        calendar_availability_summary={
            "source": "phase_10b_no_send_preview",
            "no_external_writes": True,
        },
        prior_briefing_summaries=_prior_briefing_summaries(
            connection,
            source_date=source_date_iso,
        ),
    )
    composer_result = run_fake_composer_model(
        connection,
        packet=packet,
        adapter=selected_adapter,
        run_at=started_at,
    )

    if composer_result["status"] != "completed":
        return _record_failed_briefing_output(
            connection,
            source_date=source_date_iso,
            timezone=timezone_name,
            briefing_window_name=briefing_window_name,
            delivery_mode=delivery_mode,
            daily_plan=daily_plan,
            window=window,
            packet_id=packet_id,
            composer_result=composer_result,
            permissions=permissions,
            created_at=started_at,
        )

    output = composer_result["output"]
    if output is None:
        return _record_failed_briefing_output(
            connection,
            source_date=source_date_iso,
            timezone=timezone_name,
            briefing_window_name=briefing_window_name,
            delivery_mode=delivery_mode,
            daily_plan=daily_plan,
            window=window,
            packet_id=packet_id,
            composer_result={
                **composer_result,
                "reason": "Fake Composer run completed without an output record.",
            },
            permissions=permissions,
            created_at=started_at,
        )

    readable_text = output["readable_text"]
    output_json = output["output_json"]
    briefing_output_id = stable_composer_id(
        "briefing-output",
        f"{daily_plan['id']}|{briefing_window_name}|{started_at}",
    )
    manual_export_markdown = build_manual_export_markdown(
        source_date=source_date_iso,
        timezone=timezone_name,
        briefing_window=window,
        readable_text=readable_text,
        output_json=output_json,
    )
    completion_report = _completion_report(
        status="generated",
        source_date=source_date_iso,
        timezone=timezone_name,
        briefing_window_name=briefing_window_name,
        daily_plan_id=daily_plan["id"],
        briefing_output_id=briefing_output_id,
        composer_packet_id=composer_result["packet"]["id"],
        composer_output_id=output["id"],
        delivery_mode=delivery_mode,
        warnings=_warning_messages(daily_plan, output_json),
        permissions=permissions,
        composer_result=composer_result,
        readable_text=readable_text,
        manual_export_markdown=manual_export_markdown,
    )
    briefing_output = create_briefing_output(
        connection,
        briefing_output_id=briefing_output_id,
        daily_plan_id=daily_plan["id"],
        briefing_window_id=window["id"],
        briefing_window_name=briefing_window_name,
        source_date=source_date_iso,
        timezone=timezone_name,
        composer_packet_id=composer_result["packet"]["id"],
        composer_output_id=output["id"],
        readable_text=readable_text,
        output_json=output_json,
        manual_export_markdown=manual_export_markdown,
        completion_report_json=completion_report,
        delivery_mode=delivery_mode,
        status="generated",
        created_at=started_at,
        updated_at=started_at,
    )
    completion_report["briefing_output"] = briefing_output
    return completion_report


def build_manual_export_markdown(
    *,
    source_date: str,
    timezone: str,
    briefing_window: Mapping[str, Any],
    readable_text: str,
    output_json: Mapping[str, Any],
) -> str:
    source_date = _validate_iso_date("source_date", source_date)
    timezone = _validate_timezone(timezone)
    window_name = _validate_briefing_window_name(str(briefing_window["name"]))
    readable_text = _validate_required_text("readable_text", readable_text)
    output = dict(output_json)

    lines = [
        f"# Personal OS {window_name.title()} Brief Preview",
        "",
        f"- Source date: {source_date}",
        f"- Timezone: {timezone}",
        f"- Briefing window: {window_name}",
        f"- Scheduled time: {briefing_window['scheduled_time']}",
        "",
        "## Readable Brief",
        "",
        readable_text,
        "",
        "## Candidate Summaries",
        "",
        _candidate_summary_line("Todoist candidates", output.get("todoist_tasks", []), "task_title"),
        _candidate_summary_line("Calendar candidates", output.get("calendar_blocks", []), "title"),
        _candidate_summary_line("Follow-ups", output.get("followups", []), "title"),
        _candidate_summary_line("Email brief previews", output.get("email_briefs", []), "subject"),
        "",
        "## Safety",
        "",
        "- No-send preview",
        "- No external writes performed",
    ]
    return "\n".join(lines)


def read_daily_plan(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str,
) -> dict[str, Any] | None:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return get_daily_plan(connection, daily_plan_id)


def read_daily_plans(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return list_daily_plans(connection, source_date=source_date, status=status)


def read_daily_plan_count(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    status: str | None = None,
) -> int:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return count_daily_plans(connection, source_date=source_date, status=status)


def read_briefing_output(
    connection: sqlite3.Connection,
    *,
    briefing_output_id: str,
) -> dict[str, Any] | None:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return get_briefing_output(connection, briefing_output_id)


def read_briefing_outputs(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str | None = None,
    source_date: str | None = None,
    briefing_window_name: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return list_briefing_outputs(
        connection,
        daily_plan_id=daily_plan_id,
        source_date=source_date,
        briefing_window_name=briefing_window_name,
        status=status,
    )


def read_briefing_output_count(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str | None = None,
    source_date: str | None = None,
    briefing_window_name: str | None = None,
    status: str | None = None,
) -> int:
    require_briefing_loop_permission(connection, category=BRIEFING_LOOP_READ_PERMISSION)
    return count_briefing_outputs(
        connection,
        daily_plan_id=daily_plan_id,
        source_date=source_date,
        briefing_window_name=briefing_window_name,
        status=status,
    )


def require_briefing_loop_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_briefing_loop_permission(connection, category=category)
    if not decision["allowed"]:
        raise BriefingLoopPermissionDenied(decision["reason"])
    return decision


def evaluate_briefing_loop_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = _validate_required_text("category", category)
    return evaluate_auto_write_gate(
        connection,
        category=category,
        missing_reason=lambda: f"Missing briefing loop permission setting: {category}",
        invalid_reason=lambda raw_mode: f"Invalid briefing loop permission mode: {raw_mode}",
        disabled_reason=lambda: f"Briefing loop permission is disabled: {category}",
        not_auto_write_reason=(
            lambda _mode_value: f"Briefing loop permission is not enabled for dev/test use: {category}"
        ),
        success_reason="Briefing loop permission is explicitly enabled for dev/test use.",
    )


def _ensure_daily_plan(
    connection: sqlite3.Connection,
    *,
    source_date: str,
    timezone: str,
    generated_at: str,
) -> dict[str, Any]:
    daily_plan_id = stable_composer_id("daily-plan", f"{source_date}|{timezone}")
    existing = get_daily_plan(connection, daily_plan_id)
    if existing is not None:
        return existing

    plan = build_no_send_daily_plan(
        connection,
        source_date=source_date,
        timezone=timezone,
        generated_at=generated_at,
    )
    return create_daily_plan(
        connection,
        daily_plan_id=daily_plan_id,
        source_date=source_date,
        timezone=timezone,
        plan_json=plan,
        status="generated",
        created_at=generated_at,
        updated_at=generated_at,
    )


def _require_fake_composer_adapter(adapter: ComposerAdapter) -> ComposerAdapter:
    if getattr(adapter, "dev_test_fake_adapter", False) is not True:
        raise BriefingLoopValidationError(
            "No-send briefing previews require a dev/test fake Composer adapter."
        )
    if getattr(adapter, "adapter_name", None) != FAKE_COMPOSER_ADAPTER_NAME:
        raise BriefingLoopValidationError(
            f"No-send briefing previews are limited to {FAKE_COMPOSER_ADAPTER_NAME}."
        )
    return adapter


def _record_failed_briefing_output(
    connection: sqlite3.Connection,
    *,
    source_date: str,
    timezone: str,
    briefing_window_name: str,
    delivery_mode: str,
    daily_plan: Mapping[str, Any],
    window: Mapping[str, Any],
    packet_id: str,
    composer_result: Mapping[str, Any],
    permissions: Mapping[str, Mapping[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    reason = str(composer_result.get("reason", "Fake Composer run failed."))
    readable_text = "Briefing preview failed before a validated Composer output was produced."
    output_json = {
        "error": reason,
        "composer_result_status": composer_result.get("status", "failed"),
        "no_external_writes": True,
        "no_send_mode": True,
    }
    briefing_output_id = stable_composer_id(
        "briefing-output",
        f"{daily_plan['id']}|{briefing_window_name}|{created_at}",
    )
    persisted_packet = composer_result.get("packet")
    persisted_packet_id = (
        persisted_packet.get("id")
        if isinstance(persisted_packet, Mapping)
        else None
    )
    manual_export_markdown = "\n".join(
        [
            f"# Personal OS {briefing_window_name.title()} Brief Preview",
            "",
            f"- Source date: {source_date}",
            f"- Timezone: {timezone}",
            f"- Briefing window: {briefing_window_name}",
            "",
            "## Readable Brief",
            "",
            readable_text,
            "",
            "## Safety",
            "",
            "- No-send preview",
            "- No external writes performed",
        ]
    )
    completion_report = _completion_report(
        status="failed",
        source_date=source_date,
        timezone=timezone,
        briefing_window_name=briefing_window_name,
        daily_plan_id=str(daily_plan["id"]),
        briefing_output_id=briefing_output_id,
        composer_packet_id=packet_id,
        composer_output_id=None,
        delivery_mode=delivery_mode,
        warnings=[reason],
        permissions=permissions,
        composer_result=composer_result,
        readable_text=readable_text,
        manual_export_markdown=manual_export_markdown,
    )
    briefing_output = create_briefing_output(
        connection,
        briefing_output_id=briefing_output_id,
        daily_plan_id=str(daily_plan["id"]),
        briefing_window_id=str(window["id"]),
        briefing_window_name=briefing_window_name,
        source_date=source_date,
        timezone=timezone,
        composer_packet_id=persisted_packet_id,
        composer_output_id=None,
        readable_text=readable_text,
        output_json=output_json,
        manual_export_markdown=manual_export_markdown,
        completion_report_json=completion_report,
        delivery_mode=delivery_mode,
        status="failed",
        created_at=created_at,
        updated_at=created_at,
    )
    completion_report["briefing_output"] = briefing_output
    return completion_report


def _select_briefing_window_unchecked(
    connection: sqlite3.Connection,
    *,
    source_date: date | str,
    timezone: str,
    briefing_window_name: str,
) -> dict[str, Any]:
    source_date_iso = _validate_iso_date("source_date", source_date)
    timezone_name = _validate_timezone(timezone)
    briefing_window_name = _validate_briefing_window_name(briefing_window_name)
    row = connection.execute(
        """
        SELECT id, name, scheduled_time, timezone, delivery_mode, status, created_at, updated_at
        FROM briefing_windows
        WHERE name = ? AND timezone = ?
        """,
        (briefing_window_name, timezone_name),
    ).fetchone()
    if row is None:
        raise BriefingLoopValidationError(
            "Briefing window does not exist for "
            f"{source_date_iso} {timezone_name}: {briefing_window_name}"
        )

    window = _briefing_window_row_to_dict(row)
    if window["status"] not in BRIEFING_WINDOW_STATUSES_FOR_PREVIEW:
        raise BriefingLoopValidationError(
            f"Briefing window is not available for preview: {briefing_window_name}"
        )
    if window["delivery_mode"] not in BRIEFING_DELIVERY_MODES:
        raise BriefingLoopValidationError(
            f"Briefing window delivery mode is not no-send safe: {briefing_window_name}"
        )
    window["source_date"] = source_date_iso
    return window


def _list_active_or_draft_briefing_windows(
    connection: sqlite3.Connection,
    *,
    timezone_name: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, scheduled_time, timezone, delivery_mode, status, created_at, updated_at
        FROM briefing_windows
        WHERE timezone = ? AND status IN ('draft', 'active')
        ORDER BY scheduled_time, name
        """,
        (timezone_name,),
    ).fetchall()
    return [_briefing_window_row_to_dict(row) for row in rows]


def _prior_briefing_summaries(
    connection: sqlite3.Connection,
    *,
    source_date: str,
) -> list[dict[str, Any]]:
    outputs = list_briefing_outputs(connection, source_date=source_date, status="generated")
    return [
        {
            "briefing_output_id": output["id"],
            "briefing_window_name": output["briefing_window_name"],
            "status": output["status"],
            "readable_text": output["readable_text"],
            "created_at": output["created_at"],
        }
        for output in outputs[:3]
    ]


def _completion_report(
    *,
    status: str,
    source_date: str,
    timezone: str,
    briefing_window_name: str,
    daily_plan_id: str,
    briefing_output_id: str,
    composer_packet_id: str,
    composer_output_id: str | None,
    delivery_mode: str,
    warnings: list[str],
    permissions: Mapping[str, Mapping[str, Any]],
    composer_result: Mapping[str, Any],
    readable_text: str,
    manual_export_markdown: str,
) -> dict[str, Any]:
    model_run = composer_result.get("model_run") or {}
    return {
        "status": status,
        "source_date": source_date,
        "timezone": timezone,
        "briefing_window_name": briefing_window_name,
        "daily_plan_id": daily_plan_id,
        "briefing_output_id": briefing_output_id,
        "composer_packet_id": composer_packet_id,
        "composer_output_id": composer_output_id,
        "model_run_id": model_run.get("id"),
        "delivery_mode": delivery_mode,
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_model_call": True,
        "no_todoist_writes": True,
        "no_calendar_writes": True,
        "no_gmail_send": True,
        "no_gmail_draft": True,
        "manual_export_available": True,
        "external_mutation": False,
        "network_called": bool(composer_result.get("network_called", False)),
        "fake_composer_adapter": model_run.get("adapter_name") == "fake_composer_adapter",
        "permissions": {key: dict(value) for key, value in permissions.items()},
        "warnings": warnings,
        "readable_text": readable_text,
        "manual_export_markdown": manual_export_markdown,
    }


def _blocked_result(
    *,
    reason: str,
    source_date: str,
    timezone: str,
    briefing_window_name: str,
    delivery_mode: str,
    permissions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "source_date": source_date,
        "timezone": timezone,
        "briefing_window_name": briefing_window_name,
        "daily_plan_id": None,
        "composer_packet_id": None,
        "composer_output_id": None,
        "delivery_mode": delivery_mode,
        "no_external_writes": True,
        "no_send_mode": True,
        "no_live_model_call": True,
        "no_todoist_writes": True,
        "no_calendar_writes": True,
        "no_gmail_send": True,
        "no_gmail_draft": True,
        "database_write": False,
        "external_mutation": False,
        "permissions": {key: dict(value) for key, value in permissions.items()},
        "warnings": [reason],
    }


def _evaluate_generation_permissions(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    return {
        "write": evaluate_briefing_loop_permission(
            connection,
            category=BRIEFING_LOOP_WRITE_PERMISSION,
        ),
        "run": evaluate_briefing_loop_permission(
            connection,
            category=BRIEFING_LOOP_RUN_PERMISSION,
        ),
    }


def _briefing_window_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "scheduled_time": row["scheduled_time"],
        "timezone": row["timezone"],
        "delivery_mode": row["delivery_mode"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _warning_messages(
    daily_plan: Mapping[str, Any],
    output_json: Mapping[str, Any],
) -> list[str]:
    plan_warnings = daily_plan.get("plan_json", {}).get("warnings", [])
    output_warnings = output_json.get("warnings", [])
    warnings: list[str] = []
    if isinstance(plan_warnings, list):
        warnings.extend(str(warning) for warning in plan_warnings)
    if isinstance(output_warnings, list):
        for warning in output_warnings:
            if isinstance(warning, Mapping):
                warnings.append(str(warning.get("message", warning)))
            else:
                warnings.append(str(warning))
    return warnings


def _candidate_summary_line(
    label: str,
    candidates: Any,
    title_key: str,
) -> str:
    if not isinstance(candidates, list) or not candidates:
        return f"- {label}: 0"

    titles = []
    for candidate in candidates[:3]:
        if isinstance(candidate, Mapping):
            title = candidate.get(title_key)
            if isinstance(title, str) and title.strip():
                titles.append(title.strip())
    suffix = ""
    if titles:
        suffix = " - " + "; ".join(titles)
    if len(candidates) > 3:
        suffix = f"{suffix}; +{len(candidates) - 3} more"
    return f"- {label}: {len(candidates)}{suffix}"


def _validate_briefing_window_name(value: str) -> str:
    if not isinstance(value, str) or value not in BRIEFING_WINDOW_NAMES:
        allowed = ", ".join(BRIEFING_WINDOW_NAMES)
        raise BriefingLoopValidationError(f"briefing_window_name must be one of: {allowed}")
    return value


def _validate_delivery_mode(value: str) -> str:
    if not isinstance(value, str) or value not in BRIEFING_DELIVERY_MODES:
        allowed = ", ".join(BRIEFING_DELIVERY_MODES)
        raise BriefingLoopValidationError(f"delivery_mode must be one of: {allowed}")
    return value


def _validate_timezone(value: str) -> str:
    value = _validate_required_text("timezone", value)
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as error:
        raise BriefingLoopValidationError("timezone must be an IANA timezone name") from error
    return value


def _validate_iso_date(field_name: str, value: date | str) -> str:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise BriefingLoopValidationError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise BriefingLoopValidationError(f"{field_name} must be an ISO date") from error


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise BriefingLoopValidationError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BriefingLoopValidationError(f"{field_name} must include a timezone offset")
    return value


def _validate_required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BriefingLoopValidationError(f"{field_name} must not be empty")
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

"""Read-only Today View summaries for the local dashboard shell."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from personalos.config import DEFAULT_TIMEZONE
from personalos.state import (
    count_briefing_outputs,
    count_calendar_blocks,
    count_followups,
    count_routine_completions,
    count_routines,
    count_todoist_tasks,
    list_calendar_blocks,
    list_followups,
    list_permission_settings,
    list_routines,
    summarize_priorities,
)
from personalos.status import create_status_summary

SAFETY_WARNINGS = (
    "Read-only Today View preview; no dashboard mutation routes are available.",
    "No scheduler, production runtime activation, or daily briefing loop is active.",
    "No live Todoist, Calendar, Gmail, model, or external API calls are made.",
)


def create_today_view_summary(
    connection: sqlite3.Connection,
    *,
    source_date: date | str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    recent_event_limit: int = 5,
) -> dict[str, Any]:
    """Build a read-only Today View summary from an existing SQLite connection."""
    timezone_name = _validate_timezone(timezone)
    source_date_iso = _normalize_source_date(source_date, timezone_name=timezone_name)
    day_window = _source_date_window(source_date_iso, timezone_name=timezone_name)

    system_status_summary = create_status_summary(
        connection,
        recent_event_limit=recent_event_limit,
    )

    return {
        "source_date": source_date_iso,
        "timezone": timezone_name,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "routine_summary": _routine_summary(connection, source_date=source_date_iso),
        "priority_summary": summarize_priorities(connection),
        "followup_summary": _followup_summary(connection),
        "todoist_candidate_summary": _todoist_candidate_summary(connection),
        "calendar_block_summary": _calendar_block_summary(connection, day_window=day_window),
        "briefing_window_summary": _briefing_window_summary(connection),
        "briefing_loop_summary": _briefing_loop_summary(
            connection,
            source_date=source_date_iso,
        ),
        "permission_summary": _permission_summary(connection),
        "system_status_summary": _system_status_summary(connection, system_status_summary),
        "warnings": list(SAFETY_WARNINGS),
        "no_external_writes": True,
    }


def _routine_summary(
    connection: sqlite3.Connection,
    *,
    source_date: str,
) -> dict[str, Any]:
    routines = list_routines(connection)
    completions_for_date = _routine_completion_counts_for_date(connection, source_date)
    return {
        "total_count": count_routines(connection),
        "enabled_count": sum(1 for routine in routines if routine["enabled"]),
        "disabled_count": sum(1 for routine in routines if not routine["enabled"]),
        "counts_by_status": _count_by_key(routines, "status"),
        "completion_count": count_routine_completions(connection),
        "completed_for_source_date_count": sum(completions_for_date.values()),
        "routines": [
            {
                "routine_id": routine["routine_id"],
                "name": routine["name"],
                "status": routine["status"],
                "enabled": routine["enabled"],
                "completed_for_source_date_count": completions_for_date.get(
                    routine["routine_id"],
                    0,
                ),
            }
            for routine in routines
        ],
    }


def _routine_completion_counts_for_date(
    connection: sqlite3.Connection,
    source_date: str,
) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT routine_id, COUNT(*) AS completion_count
        FROM routine_completions
        WHERE completed_for_date = ?
        GROUP BY routine_id
        ORDER BY routine_id
        """,
        (source_date,),
    ).fetchall()
    return {row["routine_id"]: int(row["completion_count"]) for row in rows}


def _followup_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    followups = list_followups(connection)
    return {
        "total_count": count_followups(connection),
        "counts_by_status": _count_by_key(followups, "status"),
        "open_count": sum(1 for followup in followups if followup["status"] == "open"),
        "followups": [
            {
                "followup_id": followup["followup_id"],
                "title": followup["title"],
                "status": followup["status"],
                "source": followup["source"],
            }
            for followup in followups
        ],
    }


def _todoist_candidate_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "total_count": count_todoist_tasks(connection),
        "counts_by_status": _grouped_counts(connection, "todoist_tasks", "status"),
        "counts_by_risk_level": _grouped_counts(connection, "todoist_tasks", "risk_level"),
        "counts_by_approval_mode": _grouped_counts(
            connection,
            "todoist_tasks",
            "approval_mode",
        ),
    }


def _calendar_block_summary(
    connection: sqlite3.Connection,
    *,
    day_window: Mapping[str, str],
) -> dict[str, Any]:
    source_date_blocks = list_calendar_blocks(
        connection,
        time_min=day_window["start"],
        time_max=day_window["end"],
    )
    return {
        "total_count": count_calendar_blocks(connection),
        "source_date_count": len(source_date_blocks),
        "source_date_window": dict(day_window),
        "counts_by_status": _grouped_counts(connection, "calendar_blocks", "status"),
        "counts_by_risk_level": _grouped_counts(connection, "calendar_blocks", "risk_level"),
        "counts_by_approval_mode": _grouped_counts(
            connection,
            "calendar_blocks",
            "approval_mode",
        ),
        "blocks_for_source_date": [
            {
                "calendar_block_id": block["calendar_block_id"],
                "title": block["title"],
                "status": block["status"],
                "start_time": block["start_time"],
                "end_time": block["end_time"],
                "timezone": block["timezone"],
            }
            for block in source_date_blocks
        ],
    }


def _briefing_window_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    windows = _list_briefing_windows(connection)
    return {
        "total_count": len(windows),
        "counts_by_status": _count_by_key(windows, "status"),
        "counts_by_delivery_mode": _count_by_key(windows, "delivery_mode"),
        "windows": windows,
    }


def _list_briefing_windows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, scheduled_time, timezone, delivery_mode, status, created_at, updated_at
        FROM briefing_windows
        ORDER BY scheduled_time, name
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "scheduled_time": row["scheduled_time"],
            "timezone": row["timezone"],
            "delivery_mode": row["delivery_mode"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def _briefing_loop_summary(
    connection: sqlite3.Connection,
    *,
    source_date: str,
) -> dict[str, Any]:
    windows = _list_briefing_windows(connection)
    return {
        "latest_briefing_output_count": count_briefing_outputs(connection),
        "source_date_briefing_output_count": count_briefing_outputs(
            connection,
            source_date=source_date,
        ),
        "briefing_windows_status": _count_by_key(windows, "status"),
        "no_send_mode": True,
    }


def _permission_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    settings = list_permission_settings(connection)
    live_like_categories = [
        setting["category"]
        for setting in settings
        if _is_live_like_permission_category(setting["category"])
    ]
    return {
        "total_count": len(settings),
        "counts_by_mode": _count_by_key(settings, "mode"),
        "live_like_permission_categories": live_like_categories,
        "live_like_permission_count": len(live_like_categories),
        "settings": settings,
        "no_live_external_permission_keys": len(live_like_categories) == 0,
    }


def _system_status_summary(
    connection: sqlite3.Connection,
    status_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at_utc": status_summary["generated_at_utc"],
        "counts": dict(status_summary["counts"]),
        "permission_settings_count": status_summary["permission_settings_count"],
        "recent_system_events": list(status_summary["recent_system_events"]),
        "runtime_bootstrap_run_count": _count_table_if_present(
            connection,
            "runtime_bootstrap_runs",
        ),
        "no_external_writes": True,
    }


def _grouped_counts(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> dict[str, int]:
    if table_name not in {"todoist_tasks", "calendar_blocks"}:
        raise ValueError(f"Unsupported summary table: {table_name}")
    if column_name not in {"status", "risk_level", "approval_mode"}:
        raise ValueError(f"Unsupported summary column: {column_name}")

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


def _count_table_if_present(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    if row is None:
        return 0
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])


def _source_date_window(source_date: str, *, timezone_name: str) -> dict[str, str]:
    zone = ZoneInfo(timezone_name)
    parsed_date = date.fromisoformat(source_date)
    start = datetime.combine(parsed_date, time.min, tzinfo=zone)
    end = datetime.combine(parsed_date + timedelta(days=1), time.min, tzinfo=zone)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _normalize_source_date(source_date: date | str | None, *, timezone_name: str) -> str:
    if source_date is None:
        return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    if isinstance(source_date, date) and not isinstance(source_date, datetime):
        return source_date.isoformat()
    if isinstance(source_date, str):
        try:
            return date.fromisoformat(source_date).isoformat()
        except ValueError as error:
            raise ValueError("source_date must be an ISO date string") from error
    raise ValueError("source_date must be a date, ISO date string, or None")


def _validate_timezone(timezone: str) -> str:
    if not isinstance(timezone, str) or not timezone.strip():
        raise ValueError("timezone must be a non-empty IANA timezone name")
    timezone_name = timezone.strip()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError("timezone must be a valid IANA timezone name") from error
    return timezone_name


def _is_live_like_permission_category(category: str) -> bool:
    live_markers = (
        "live",
        "gmail",
        "model_api",
        "openai",
        "openrouter",
        "anthropic",
        "todoist_live",
        "calendar_live",
    )
    return any(marker in category for marker in live_markers)

"""Daily-plan and briefing-output state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.state._shared import (
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_iso_date,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_required_text,
)

BRIEFING_LOOP_STATE_TABLES = ("daily_plans", "briefing_outputs")


DAILY_PLAN_STATUSES = ("draft", "generated", "completed", "failed")


BRIEFING_OUTPUT_WINDOWS = ("morning", "midday", "afternoon", "evening")


BRIEFING_OUTPUT_DELIVERY_MODES = ("no_send", "manual_export")


BRIEFING_OUTPUT_STATUSES = ("preview", "generated", "failed")


def validate_daily_plan_status(status: str) -> str:
    if not isinstance(status, str) or status not in DAILY_PLAN_STATUSES:
        allowed = ", ".join(DAILY_PLAN_STATUSES)
        raise ValueError(f"daily plan status must be one of: {allowed}")
    return status


def validate_briefing_output_window(briefing_window_name: str) -> str:
    if (
        not isinstance(briefing_window_name, str)
        or briefing_window_name not in BRIEFING_OUTPUT_WINDOWS
    ):
        allowed = ", ".join(BRIEFING_OUTPUT_WINDOWS)
        raise ValueError(f"briefing output window must be one of: {allowed}")
    return briefing_window_name


def validate_briefing_output_delivery_mode(delivery_mode: str) -> str:
    if not isinstance(delivery_mode, str) or delivery_mode not in BRIEFING_OUTPUT_DELIVERY_MODES:
        allowed = ", ".join(BRIEFING_OUTPUT_DELIVERY_MODES)
        raise ValueError(f"briefing output delivery_mode must be one of: {allowed}")
    return delivery_mode


def validate_briefing_output_status(status: str) -> str:
    if not isinstance(status, str) or status not in BRIEFING_OUTPUT_STATUSES:
        allowed = ", ".join(BRIEFING_OUTPUT_STATUSES)
        raise ValueError(f"briefing output status must be one of: {allowed}")
    return status


def create_daily_plan(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str,
    source_date: str,
    timezone: str,
    plan_json: Mapping[str, Any],
    status: str = "generated",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    daily_plan_id = _validate_required_text("daily_plan_id", daily_plan_id)
    source_date = _validate_iso_date("source_date", source_date)
    timezone = _validate_required_text("timezone", timezone)
    plan_json_text = _serialize_metadata(_validate_metadata("plan_json", plan_json))
    status = validate_daily_plan_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO daily_plans (
                id,
                source_date,
                timezone,
                plan_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                daily_plan_id,
                source_date,
                timezone,
                plan_json_text,
                status,
                created,
                updated,
            ),
        )

    daily_plan = get_daily_plan(connection, daily_plan_id)
    if daily_plan is None:
        raise RuntimeError(f"Daily plan was not persisted: {daily_plan_id}")
    return daily_plan


def get_daily_plan(
    connection: sqlite3.Connection,
    daily_plan_id: str,
) -> dict[str, Any] | None:
    daily_plan_id = _validate_required_text("daily_plan_id", daily_plan_id)
    row = connection.execute(
        """
        SELECT id, source_date, timezone, plan_json, status, created_at, updated_at
        FROM daily_plans
        WHERE id = ?
        """,
        (daily_plan_id,),
    ).fetchone()
    return _daily_plan_row_to_dict(row) if row is not None else None


def update_daily_plan_status(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str,
    status: str,
    updated_at: str | None = None,
) -> dict[str, Any]:
    daily_plan_id = _validate_required_text("daily_plan_id", daily_plan_id)
    status = validate_daily_plan_status(status)
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())
    current = get_daily_plan(connection, daily_plan_id)
    if current is None:
        raise ValueError(f"Daily plan does not exist: {daily_plan_id}")

    with connection:
        connection.execute(
            """
            UPDATE daily_plans
            SET status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, updated, daily_plan_id),
        )

    daily_plan = get_daily_plan(connection, daily_plan_id)
    if daily_plan is None:
        raise RuntimeError(f"Daily plan was not found after update: {daily_plan_id}")
    return daily_plan


def list_daily_plans(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _daily_plan_filter_clause(source_date=source_date, status=status)
    rows = connection.execute(
        f"""
        SELECT id, source_date, timezone, plan_json, status, created_at, updated_at
        FROM daily_plans
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_daily_plan_row_to_dict(row) for row in rows]


def count_daily_plans(
    connection: sqlite3.Connection,
    *,
    source_date: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _daily_plan_filter_clause(source_date=source_date, status=status)
    row = connection.execute(
        f"SELECT COUNT(*) FROM daily_plans {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_briefing_output(
    connection: sqlite3.Connection,
    *,
    briefing_output_id: str,
    daily_plan_id: str | None,
    briefing_window_id: str | None,
    briefing_window_name: str,
    source_date: str,
    timezone: str,
    composer_packet_id: str | None,
    composer_output_id: str | None,
    readable_text: str,
    output_json: Mapping[str, Any],
    manual_export_markdown: str,
    completion_report_json: Mapping[str, Any],
    delivery_mode: str = "no_send",
    status: str = "generated",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    briefing_output_id = _validate_required_text("briefing_output_id", briefing_output_id)
    if daily_plan_id is not None:
        daily_plan_id = _validate_required_text("daily_plan_id", daily_plan_id)
    if briefing_window_id is not None:
        briefing_window_id = _validate_required_text("briefing_window_id", briefing_window_id)
    briefing_window_name = validate_briefing_output_window(briefing_window_name)
    source_date = _validate_iso_date("source_date", source_date)
    timezone = _validate_required_text("timezone", timezone)
    if composer_packet_id is not None:
        composer_packet_id = _validate_required_text("composer_packet_id", composer_packet_id)
    if composer_output_id is not None:
        composer_output_id = _validate_required_text("composer_output_id", composer_output_id)
    readable_text = _validate_required_text("readable_text", readable_text)
    output_json_text = _serialize_metadata(_validate_metadata("output_json", output_json))
    manual_export_markdown = _validate_required_text(
        "manual_export_markdown",
        manual_export_markdown,
    )
    completion_report_text = _serialize_metadata(
        _validate_metadata("completion_report_json", completion_report_json)
    )
    delivery_mode = validate_briefing_output_delivery_mode(delivery_mode)
    status = validate_briefing_output_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO briefing_outputs (
                id,
                daily_plan_id,
                briefing_window_id,
                briefing_window_name,
                source_date,
                timezone,
                composer_packet_id,
                composer_output_id,
                readable_text,
                output_json,
                manual_export_markdown,
                completion_report_json,
                delivery_mode,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                briefing_output_id,
                daily_plan_id,
                briefing_window_id,
                briefing_window_name,
                source_date,
                timezone,
                composer_packet_id,
                composer_output_id,
                readable_text,
                output_json_text,
                manual_export_markdown,
                completion_report_text,
                delivery_mode,
                status,
                created,
                updated,
            ),
        )

    briefing_output = get_briefing_output(connection, briefing_output_id)
    if briefing_output is None:
        raise RuntimeError(f"Briefing output was not persisted: {briefing_output_id}")
    return briefing_output


def get_briefing_output(
    connection: sqlite3.Connection,
    briefing_output_id: str,
) -> dict[str, Any] | None:
    briefing_output_id = _validate_required_text("briefing_output_id", briefing_output_id)
    row = connection.execute(
        """
        SELECT
            id,
            daily_plan_id,
            briefing_window_id,
            briefing_window_name,
            source_date,
            timezone,
            composer_packet_id,
            composer_output_id,
            readable_text,
            output_json,
            manual_export_markdown,
            completion_report_json,
            delivery_mode,
            status,
            created_at,
            updated_at
        FROM briefing_outputs
        WHERE id = ?
        """,
        (briefing_output_id,),
    ).fetchone()
    return _briefing_output_row_to_dict(row) if row is not None else None


def list_briefing_outputs(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str | None = None,
    source_date: str | None = None,
    briefing_window_name: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _briefing_output_filter_clause(
        daily_plan_id=daily_plan_id,
        source_date=source_date,
        briefing_window_name=briefing_window_name,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            daily_plan_id,
            briefing_window_id,
            briefing_window_name,
            source_date,
            timezone,
            composer_packet_id,
            composer_output_id,
            readable_text,
            output_json,
            manual_export_markdown,
            completion_report_json,
            delivery_mode,
            status,
            created_at,
            updated_at
        FROM briefing_outputs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_briefing_output_row_to_dict(row) for row in rows]


def count_briefing_outputs(
    connection: sqlite3.Connection,
    *,
    daily_plan_id: str | None = None,
    source_date: str | None = None,
    briefing_window_name: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _briefing_output_filter_clause(
        daily_plan_id=daily_plan_id,
        source_date=source_date,
        briefing_window_name=briefing_window_name,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM briefing_outputs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def _daily_plan_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_date": row["source_date"],
        "timezone": row["timezone"],
        "plan_json": _deserialize_metadata(row["plan_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _briefing_output_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "daily_plan_id": row["daily_plan_id"],
        "briefing_window_id": row["briefing_window_id"],
        "briefing_window_name": row["briefing_window_name"],
        "source_date": row["source_date"],
        "timezone": row["timezone"],
        "composer_packet_id": row["composer_packet_id"],
        "composer_output_id": row["composer_output_id"],
        "readable_text": row["readable_text"],
        "output_json": _deserialize_metadata(row["output_json"]),
        "manual_export_markdown": row["manual_export_markdown"],
        "completion_report_json": _deserialize_metadata(row["completion_report_json"]),
        "delivery_mode": row["delivery_mode"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _daily_plan_filter_clause(
    *,
    source_date: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if source_date is not None:
        clauses.append("source_date = ?")
        values.append(_validate_iso_date("source_date", source_date))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_daily_plan_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _briefing_output_filter_clause(
    *,
    daily_plan_id: str | None,
    source_date: str | None,
    briefing_window_name: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if daily_plan_id is not None:
        clauses.append("daily_plan_id = ?")
        values.append(_validate_required_text("daily_plan_id", daily_plan_id))
    if source_date is not None:
        clauses.append("source_date = ?")
        values.append(_validate_iso_date("source_date", source_date))
    if briefing_window_name is not None:
        clauses.append("briefing_window_name = ?")
        values.append(validate_briefing_output_window(briefing_window_name))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_briefing_output_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


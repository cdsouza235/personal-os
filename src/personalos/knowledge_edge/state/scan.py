"""Knowledge Edge scan/health state: scan_run, scan_cursor, source_health,
coverage_report (amendment §11.1 cursor behavior, §10.5 coverage reporting, §17.3
health surface).

Cursor-advance invariant (migration 00020 comment): a source's cursor is only ever
advanced through ``advance_scan_cursor`` after that source's discovered batch has
already been committed by the caller -- this module does not enforce ordering against
any other table, it only records the value the caller passes.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from personalos.knowledge_edge.state._shared import (
    _count_rows,
    _deserialize_json_object,
    _serialize_json,
    _utc_now,
    _validate_enum,
    _validate_optional_iso_datetime,
    _validate_optional_text,
    _validate_required_text,
)

SCAN_RUN_TYPES = ("full_scan", "morning_refresh", "manual_scan_now", "targeted_link_check")
SCAN_RUN_STATUSES = ("running", "completed", "partially_completed", "failed")
SOURCE_HEALTH_STATUSES = ("healthy", "degraded", "failed", "stale", "unknown")


def validate_scan_run_type(value: str) -> str:
    return _validate_enum("run_type", value, SCAN_RUN_TYPES)


def validate_scan_run_status(value: str) -> str:
    return _validate_enum("status", value, SCAN_RUN_STATUSES)


def validate_source_health_status(value: str) -> str:
    return _validate_enum("status", value, SOURCE_HEALTH_STATUSES)


# --------------------------------------------------------------------------- scan runs


def create_scan_run(
    connection: sqlite3.Connection,
    *,
    scan_run_id: str,
    run_type: str,
    status: str = "running",
    triggered_by: str = "scheduler",
    started_at: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scan_run_id = _validate_required_text("scan_run_id", scan_run_id)
    run_type = validate_scan_run_type(run_type)
    status = validate_scan_run_status(status)
    triggered_by = _validate_required_text("triggered_by", triggered_by)
    started_at = _validate_optional_iso_datetime("started_at", started_at or _utc_now())
    summary_json = _serialize_json(dict(summary or {}))
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_scan_runs (
                scan_run_id, run_type, status, triggered_by, started_at, completed_at,
                summary_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (scan_run_id, run_type, status, triggered_by, started_at, summary_json, now),
        )

    run = get_scan_run(connection, scan_run_id)
    if run is None:
        raise RuntimeError(f"Scan run was not persisted for scan_run_id: {scan_run_id}")
    return run


def get_scan_run(connection: sqlite3.Connection, scan_run_id: str) -> dict[str, Any] | None:
    scan_run_id = _validate_required_text("scan_run_id", scan_run_id)
    row = connection.execute(
        "SELECT * FROM ke_scan_runs WHERE scan_run_id = ?", (scan_run_id,)
    ).fetchone()
    return _scan_run_row_to_dict(row) if row is not None else None


def list_scan_runs(
    connection: sqlite3.Connection, *, run_type: str | None = None
) -> list[dict[str, Any]]:
    if run_type is None:
        rows = connection.execute(
            "SELECT * FROM ke_scan_runs ORDER BY started_at DESC, scan_run_id"
        ).fetchall()
    else:
        run_type = validate_scan_run_type(run_type)
        rows = connection.execute(
            "SELECT * FROM ke_scan_runs WHERE run_type = ? ORDER BY started_at DESC, scan_run_id",
            (run_type,),
        ).fetchall()
    return [_scan_run_row_to_dict(row) for row in rows]


def count_scan_runs(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_scan_runs")


def complete_scan_run(
    connection: sqlite3.Connection,
    *,
    scan_run_id: str,
    status: str,
    completed_at: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run = get_scan_run(connection, scan_run_id)
    if run is None:
        raise ValueError(f"Scan run does not exist: {scan_run_id}")
    status = validate_scan_run_status(status)
    if status == "running":
        raise ValueError("complete_scan_run cannot set status back to 'running'")
    completed_at = _validate_optional_iso_datetime("completed_at", completed_at or _utc_now())
    if completed_at is not None and completed_at < run["started_at"]:
        raise ValueError("completed_at must not be before started_at")
    summary_json = (
        run["summary_json"] if summary is None else _serialize_json(dict(summary))
    )

    with connection:
        connection.execute(
            """
            UPDATE ke_scan_runs
            SET status = ?, completed_at = ?, summary_json = ?
            WHERE scan_run_id = ?
            """,
            (status, completed_at, summary_json, scan_run_id),
        )

    updated = get_scan_run(connection, scan_run_id)
    if updated is None:
        raise RuntimeError(f"Scan run was not found after update: {scan_run_id}")
    return updated


def _scan_run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["summary"] = _deserialize_json_object(item.pop("summary_json"))
    return item


# ------------------------------------------------------------------------ scan cursors


def advance_scan_cursor(
    connection: sqlite3.Connection,
    *,
    cursor_id: str,
    source_id: str,
    last_successful_cursor_value: str | None,
    last_successful_at: str | None = None,
    overlap_window_seconds: int = 3600,
) -> dict[str, Any]:
    """Create or advance the one cursor row for ``source_id``.

    Callers must persist the source's discovered batch before calling this -- that
    ordering invariant is a caller responsibility, not something this function can
    check.
    """
    cursor_id = _validate_required_text("cursor_id", cursor_id)
    source_id = _validate_required_text("source_id", source_id)
    last_successful_cursor_value = _validate_optional_text(
        "last_successful_cursor_value", last_successful_cursor_value
    )
    last_successful_at = _validate_optional_iso_datetime(
        "last_successful_at", last_successful_at or _utc_now()
    )
    if type(overlap_window_seconds) is not int or overlap_window_seconds < 0:
        raise ValueError("overlap_window_seconds must be a non-negative integer")
    now = _utc_now()

    existing = get_scan_cursor(connection, source_id=source_id)

    with connection:
        if existing is None:
            connection.execute(
                """
                INSERT INTO ke_scan_cursors (
                    cursor_id, source_id, last_successful_cursor_value, last_successful_at,
                    overlap_window_seconds, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cursor_id, source_id, last_successful_cursor_value, last_successful_at,
                    overlap_window_seconds, now, now,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE ke_scan_cursors
                SET last_successful_cursor_value = ?, last_successful_at = ?,
                    overlap_window_seconds = ?, updated_at = ?
                WHERE source_id = ?
                """,
                (
                    last_successful_cursor_value, last_successful_at, overlap_window_seconds,
                    now, source_id,
                ),
            )

    cursor = get_scan_cursor(connection, source_id=source_id)
    if cursor is None:
        raise RuntimeError(f"Scan cursor was not persisted for source_id: {source_id}")
    return cursor


def get_scan_cursor(connection: sqlite3.Connection, *, source_id: str) -> dict[str, Any] | None:
    source_id = _validate_required_text("source_id", source_id)
    row = connection.execute(
        "SELECT * FROM ke_scan_cursors WHERE source_id = ?", (source_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def count_scan_cursors(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_scan_cursors")


# ---------------------------------------------------------------------- source health


def upsert_source_health(
    connection: sqlite3.Connection,
    *,
    health_id: str,
    source_id: str,
    status: str,
    scan_run_id: str | None = None,
    last_success_at: str | None = None,
    last_failure_at: str | None = None,
    consecutive_failure_count: int = 0,
    last_error_summary: str | None = None,
) -> dict[str, Any]:
    health_id = _validate_required_text("health_id", health_id)
    source_id = _validate_required_text("source_id", source_id)
    status = validate_source_health_status(status)
    last_success_at = _validate_optional_iso_datetime("last_success_at", last_success_at)
    last_failure_at = _validate_optional_iso_datetime("last_failure_at", last_failure_at)
    if type(consecutive_failure_count) is not int or consecutive_failure_count < 0:
        raise ValueError("consecutive_failure_count must be a non-negative integer")
    last_error_summary = _validate_optional_text("last_error_summary", last_error_summary)
    now = _utc_now()

    existing = get_source_health(connection, source_id=source_id)

    with connection:
        if existing is None:
            connection.execute(
                """
                INSERT INTO ke_source_health (
                    health_id, source_id, scan_run_id, status, last_success_at,
                    last_failure_at, consecutive_failure_count, last_error_summary,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    health_id, source_id, scan_run_id, status, last_success_at,
                    last_failure_at, consecutive_failure_count, last_error_summary, now, now,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE ke_source_health
                SET scan_run_id = ?, status = ?, last_success_at = ?, last_failure_at = ?,
                    consecutive_failure_count = ?, last_error_summary = ?, updated_at = ?
                WHERE source_id = ?
                """,
                (
                    scan_run_id, status, last_success_at, last_failure_at,
                    consecutive_failure_count, last_error_summary, now, source_id,
                ),
            )

    health = get_source_health(connection, source_id=source_id)
    if health is None:
        raise RuntimeError(f"Source health was not persisted for source_id: {source_id}")
    return health


def get_source_health(connection: sqlite3.Connection, *, source_id: str) -> dict[str, Any] | None:
    source_id = _validate_required_text("source_id", source_id)
    row = connection.execute(
        "SELECT * FROM ke_source_health WHERE source_id = ?", (source_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def list_source_health(
    connection: sqlite3.Connection, *, status: str | None = None
) -> list[dict[str, Any]]:
    if status is None:
        rows = connection.execute(
            "SELECT * FROM ke_source_health ORDER BY source_id"
        ).fetchall()
    else:
        status = validate_source_health_status(status)
        rows = connection.execute(
            "SELECT * FROM ke_source_health WHERE status = ? ORDER BY source_id", (status,)
        ).fetchall()
    return [dict(row) for row in rows]


def count_source_health(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_source_health")


# ------------------------------------------------------------------- coverage reports


def create_coverage_report(
    connection: sqlite3.Connection,
    *,
    coverage_report_id: str,
    scan_run_id: str,
    report_date: str,
    report: dict[str, Any],
    overall_summary: str,
) -> dict[str, Any]:
    coverage_report_id = _validate_required_text("coverage_report_id", coverage_report_id)
    scan_run_id = _validate_required_text("scan_run_id", scan_run_id)
    report_date = _validate_required_text("report_date", report_date)
    report_json = _serialize_json(dict(report))
    overall_summary = _validate_required_text("overall_summary", overall_summary)
    now = _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO ke_coverage_reports (
                coverage_report_id, scan_run_id, report_date, report_json,
                overall_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (coverage_report_id, scan_run_id, report_date, report_json, overall_summary, now),
        )

    row = connection.execute(
        "SELECT * FROM ke_coverage_reports WHERE coverage_report_id = ?", (coverage_report_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Coverage report was not persisted for coverage_report_id: {coverage_report_id}"
        )
    return _coverage_report_row_to_dict(row)


def list_coverage_reports(
    connection: sqlite3.Connection, *, report_date: str | None = None
) -> list[dict[str, Any]]:
    if report_date is None:
        rows = connection.execute(
            "SELECT * FROM ke_coverage_reports ORDER BY report_date DESC, coverage_report_id"
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT * FROM ke_coverage_reports WHERE report_date = ?
            ORDER BY coverage_report_id
            """,
            (report_date,),
        ).fetchall()
    return [_coverage_report_row_to_dict(row) for row in rows]


def count_coverage_reports(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "ke_coverage_reports")


def _coverage_report_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["report"] = _deserialize_json_object(item.pop("report_json"))
    return item

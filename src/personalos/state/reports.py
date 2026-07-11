"""Report job/run and chart-pack-review state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.state._shared import (
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_bool,
    _validate_iso_date,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_required_text,
    _validate_text,
)

REPORT_STATE_TABLES = ("report_jobs", "report_runs", "chart_pack_reviews")


REPORT_JOB_TYPES = (
    "weekly_chart_pack_index",
    "tradingview_alert_digest",
    "macro_calendar",
    "earnings_calendar",
    "priority_status_report",
    "routine_adherence_report",
    "todoist_completion_report",
    "calendar_utilization_report",
)


REPORT_JOB_CADENCES = ("manual", "daily", "weekly", "monthly")


REPORT_JOB_STATUSES = ("draft", "active", "paused", "disabled")


REPORT_RUN_TYPES = ("preview", "dry_run", "simulated")


REPORT_RUN_STATUSES = ("started", "completed", "failed")


CHART_PACK_REVIEW_SOURCE_TYPES = (
    "chatgpt_synthesis",
    "manual_entry",
    "imported_markdown",
    "fake_fixture",
)


CHART_PACK_REVIEW_STATUSES = ("draft", "validated", "stored", "rejected")


def validate_report_job_type(job_type: str) -> str:
    if not isinstance(job_type, str) or job_type not in REPORT_JOB_TYPES:
        allowed = ", ".join(REPORT_JOB_TYPES)
        raise ValueError(f"report job_type must be one of: {allowed}")
    return job_type


def validate_report_job_cadence(cadence: str) -> str:
    if not isinstance(cadence, str) or cadence not in REPORT_JOB_CADENCES:
        allowed = ", ".join(REPORT_JOB_CADENCES)
        raise ValueError(f"report job cadence must be one of: {allowed}")
    return cadence


def validate_report_job_status(status: str) -> str:
    if not isinstance(status, str) or status not in REPORT_JOB_STATUSES:
        allowed = ", ".join(REPORT_JOB_STATUSES)
        raise ValueError(f"report job status must be one of: {allowed}")
    return status


def validate_report_run_type(run_type: str) -> str:
    if not isinstance(run_type, str) or run_type not in REPORT_RUN_TYPES:
        allowed = ", ".join(REPORT_RUN_TYPES)
        raise ValueError(f"report run_type must be one of: {allowed}")
    return run_type


def validate_report_run_status(status: str) -> str:
    if not isinstance(status, str) or status not in REPORT_RUN_STATUSES:
        allowed = ", ".join(REPORT_RUN_STATUSES)
        raise ValueError(f"report run status must be one of: {allowed}")
    return status


def validate_chart_pack_review_source_type(source_type: str) -> str:
    if not isinstance(source_type, str) or source_type not in CHART_PACK_REVIEW_SOURCE_TYPES:
        allowed = ", ".join(CHART_PACK_REVIEW_SOURCE_TYPES)
        raise ValueError(f"chart pack review source_type must be one of: {allowed}")
    return source_type


def validate_chart_pack_review_status(status: str) -> str:
    if not isinstance(status, str) or status not in CHART_PACK_REVIEW_STATUSES:
        allowed = ", ".join(CHART_PACK_REVIEW_STATUSES)
        raise ValueError(f"chart pack review status must be one of: {allowed}")
    return status


def create_report_job(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    job_type: str,
    name: str,
    cadence: str,
    config_json: Mapping[str, Any],
    status: str = "draft",
    description: str | None = None,
    last_run_at: str | None = None,
    next_due_at: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    job_id = _validate_required_text("job_id", job_id)
    job_type = validate_report_job_type(job_type)
    name = _validate_required_text("name", name)
    cadence = validate_report_job_cadence(cadence)
    config_json_text = _serialize_metadata(_validate_metadata("config_json", config_json))
    status = validate_report_job_status(status)
    if description is not None:
        description = _validate_text("description", description)
    if last_run_at is not None:
        last_run_at = _validate_iso_datetime("last_run_at", last_run_at)
    if next_due_at is not None:
        next_due_at = _validate_iso_datetime("next_due_at", next_due_at)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO report_jobs (
                id,
                job_type,
                name,
                description,
                cadence,
                config_json,
                status,
                last_run_at,
                next_due_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job_type,
                name,
                description,
                cadence,
                config_json_text,
                status,
                last_run_at,
                next_due_at,
                created,
                updated,
            ),
        )

    job = get_report_job(connection, job_id)
    if job is None:
        raise RuntimeError(f"Report job was not persisted: {job_id}")
    return job


def update_report_job(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    status: str | None = None,
    last_run_at: str | None = None,
    next_due_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    job_id = _validate_required_text("job_id", job_id)
    current = get_report_job(connection, job_id)
    if current is None:
        raise ValueError(f"Report job does not exist: {job_id}")

    next_status = current["status"] if status is None else validate_report_job_status(status)
    next_last_run_at = current["last_run_at"]
    if last_run_at is not None:
        next_last_run_at = _validate_iso_datetime("last_run_at", last_run_at)
    next_next_due_at = current["next_due_at"]
    if next_due_at is not None:
        next_next_due_at = _validate_iso_datetime("next_due_at", next_due_at)
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())

    with connection:
        connection.execute(
            """
            UPDATE report_jobs
            SET status = ?,
                last_run_at = ?,
                next_due_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (next_status, next_last_run_at, next_next_due_at, updated, job_id),
        )

    job = get_report_job(connection, job_id)
    if job is None:
        raise RuntimeError(f"Report job was not found after update: {job_id}")
    return job


def get_report_job(
    connection: sqlite3.Connection,
    job_id: str,
) -> dict[str, Any] | None:
    job_id = _validate_required_text("job_id", job_id)
    row = connection.execute(
        """
        SELECT
            id,
            job_type,
            name,
            description,
            cadence,
            config_json,
            status,
            last_run_at,
            next_due_at,
            created_at,
            updated_at
        FROM report_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()
    return _report_job_row_to_dict(row) if row is not None else None


def list_report_jobs(
    connection: sqlite3.Connection,
    *,
    job_type: str | None = None,
    cadence: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _report_job_filter_clause(
        job_type=job_type,
        cadence=cadence,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            job_type,
            name,
            description,
            cadence,
            config_json,
            status,
            last_run_at,
            next_due_at,
            created_at,
            updated_at
        FROM report_jobs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_report_job_row_to_dict(row) for row in rows]


def count_report_jobs(
    connection: sqlite3.Connection,
    *,
    job_type: str | None = None,
    cadence: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _report_job_filter_clause(
        job_type=job_type,
        cadence=cadence,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM report_jobs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_report_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    job_id: str,
    run_type: str,
    dry_run: bool,
    status: str,
    input_json: Mapping[str, Any],
    output_json: Mapping[str, Any],
    error_message: str | None = None,
    created_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    run_id = _validate_required_text("run_id", run_id)
    job_id = _validate_required_text("job_id", job_id)
    run_type = validate_report_run_type(run_type)
    dry_run = _validate_bool("dry_run", dry_run)
    status = validate_report_run_status(status)
    input_json_text = _serialize_metadata(_validate_metadata("input_json", input_json))
    output_json_text = _serialize_metadata(_validate_metadata("output_json", output_json))
    if error_message is not None:
        error_message = _validate_text("error_message", error_message)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    completed = (
        None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at)
    )

    with connection:
        connection.execute(
            """
            INSERT INTO report_runs (
                id,
                job_id,
                run_type,
                dry_run,
                status,
                input_json,
                output_json,
                error_message,
                created_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                job_id,
                run_type,
                int(dry_run),
                status,
                input_json_text,
                output_json_text,
                error_message,
                created,
                completed,
            ),
        )

    run = get_report_run(connection, run_id)
    if run is None:
        raise RuntimeError(f"Report run was not persisted: {run_id}")
    return run


def update_report_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    output_json: Mapping[str, Any] | None = None,
    error_message: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    run_id = _validate_required_text("run_id", run_id)
    current = get_report_run(connection, run_id)
    if current is None:
        raise ValueError(f"Report run does not exist: {run_id}")

    status = validate_report_run_status(status)
    next_output_json = current["output_json"] if output_json is None else output_json
    output_json_text = _serialize_metadata(_validate_metadata("output_json", next_output_json))
    if error_message is not None:
        error_message = _validate_text("error_message", error_message)
    completed = (
        None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at)
    )

    with connection:
        connection.execute(
            """
            UPDATE report_runs
            SET status = ?,
                output_json = ?,
                error_message = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (status, output_json_text, error_message, completed, run_id),
        )

    run = get_report_run(connection, run_id)
    if run is None:
        raise RuntimeError(f"Report run was not found after update: {run_id}")
    return run


def get_report_run(
    connection: sqlite3.Connection,
    run_id: str,
) -> dict[str, Any] | None:
    run_id = _validate_required_text("run_id", run_id)
    row = connection.execute(
        """
        SELECT
            id,
            job_id,
            run_type,
            dry_run,
            status,
            input_json,
            output_json,
            error_message,
            created_at,
            completed_at
        FROM report_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    return _report_run_row_to_dict(row) if row is not None else None


def list_report_runs(
    connection: sqlite3.Connection,
    *,
    job_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _report_run_filter_clause(
        job_id=job_id,
        run_type=run_type,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            job_id,
            run_type,
            dry_run,
            status,
            input_json,
            output_json,
            error_message,
            created_at,
            completed_at
        FROM report_runs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_report_run_row_to_dict(row) for row in rows]


def count_report_runs(
    connection: sqlite3.Connection,
    *,
    job_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _report_run_filter_clause(
        job_id=job_id,
        run_type=run_type,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM report_runs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_chart_pack_review(
    connection: sqlite3.Connection,
    *,
    review_id: str,
    review_date: str,
    week_start: str,
    week_end: str,
    source_type: str,
    title: str,
    chart_pack_json: Mapping[str, Any],
    tradingview_alerts_json: Mapping[str, Any],
    synthesis_markdown: str,
    structured_summary_json: Mapping[str, Any],
    status: str = "draft",
    source_id: str | None = None,
    thesis_context: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    review_id = _validate_required_text("review_id", review_id)
    review_date = _validate_iso_date("review_date", review_date)
    week_start = _validate_iso_date("week_start", week_start)
    week_end = _validate_iso_date("week_end", week_end)
    source_type = validate_chart_pack_review_source_type(source_type)
    if source_id is not None:
        source_id = _validate_required_text("source_id", source_id)
    title = _validate_required_text("title", title)
    if thesis_context is not None:
        thesis_context = _validate_text("thesis_context", thesis_context)
    chart_pack_json_text = _serialize_metadata(
        _validate_metadata("chart_pack_json", chart_pack_json)
    )
    tradingview_alerts_json_text = _serialize_metadata(
        _validate_metadata("tradingview_alerts_json", tradingview_alerts_json)
    )
    synthesis_markdown = _validate_required_text("synthesis_markdown", synthesis_markdown)
    structured_summary_json_text = _serialize_metadata(
        _validate_metadata("structured_summary_json", structured_summary_json)
    )
    status = validate_chart_pack_review_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO chart_pack_reviews (
                id,
                review_date,
                week_start,
                week_end,
                source_type,
                source_id,
                title,
                thesis_context,
                chart_pack_json,
                tradingview_alerts_json,
                synthesis_markdown,
                structured_summary_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                review_date,
                week_start,
                week_end,
                source_type,
                source_id,
                title,
                thesis_context,
                chart_pack_json_text,
                tradingview_alerts_json_text,
                synthesis_markdown,
                structured_summary_json_text,
                status,
                created,
                updated,
            ),
        )

    review = get_chart_pack_review(connection, review_id)
    if review is None:
        raise RuntimeError(f"Chart pack review was not persisted: {review_id}")
    return review


def update_chart_pack_review(
    connection: sqlite3.Connection,
    *,
    review_id: str,
    status: str | None = None,
    structured_summary_json: Mapping[str, Any] | None = None,
    synthesis_markdown: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    review_id = _validate_required_text("review_id", review_id)
    current = get_chart_pack_review(connection, review_id)
    if current is None:
        raise ValueError(f"Chart pack review does not exist: {review_id}")

    next_status = (
        current["status"] if status is None else validate_chart_pack_review_status(status)
    )
    next_summary = current["structured_summary_json"]
    if structured_summary_json is not None:
        next_summary = _validate_metadata("structured_summary_json", structured_summary_json)
    next_synthesis = current["synthesis_markdown"]
    if synthesis_markdown is not None:
        next_synthesis = _validate_required_text("synthesis_markdown", synthesis_markdown)
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())

    with connection:
        connection.execute(
            """
            UPDATE chart_pack_reviews
            SET status = ?,
                synthesis_markdown = ?,
                structured_summary_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                next_status,
                next_synthesis,
                _serialize_metadata(next_summary),
                updated,
                review_id,
            ),
        )

    review = get_chart_pack_review(connection, review_id)
    if review is None:
        raise RuntimeError(f"Chart pack review was not found after update: {review_id}")
    return review


def get_chart_pack_review(
    connection: sqlite3.Connection,
    review_id: str,
) -> dict[str, Any] | None:
    review_id = _validate_required_text("review_id", review_id)
    row = connection.execute(
        """
        SELECT
            id,
            review_date,
            week_start,
            week_end,
            source_type,
            source_id,
            title,
            thesis_context,
            chart_pack_json,
            tradingview_alerts_json,
            synthesis_markdown,
            structured_summary_json,
            status,
            created_at,
            updated_at
        FROM chart_pack_reviews
        WHERE id = ?
        """,
        (review_id,),
    ).fetchone()
    return _chart_pack_review_row_to_dict(row) if row is not None else None


def list_chart_pack_reviews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    status: str | None = None,
    week_start: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _chart_pack_review_filter_clause(
        source_type=source_type,
        status=status,
        week_start=week_start,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            review_date,
            week_start,
            week_end,
            source_type,
            source_id,
            title,
            thesis_context,
            chart_pack_json,
            tradingview_alerts_json,
            synthesis_markdown,
            structured_summary_json,
            status,
            created_at,
            updated_at
        FROM chart_pack_reviews
        {where_clause}
        ORDER BY week_start DESC, id
        """,
        values,
    ).fetchall()
    return [_chart_pack_review_row_to_dict(row) for row in rows]


def count_chart_pack_reviews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    status: str | None = None,
    week_start: str | None = None,
) -> int:
    where_clause, values = _chart_pack_review_filter_clause(
        source_type=source_type,
        status=status,
        week_start=week_start,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM chart_pack_reviews {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def _report_job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "job_type": row["job_type"],
        "name": row["name"],
        "description": row["description"],
        "cadence": row["cadence"],
        "config_json": _deserialize_metadata(row["config_json"]),
        "status": row["status"],
        "last_run_at": row["last_run_at"],
        "next_due_at": row["next_due_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _report_run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "run_type": row["run_type"],
        "dry_run": bool(row["dry_run"]),
        "status": row["status"],
        "input_json": _deserialize_metadata(row["input_json"]),
        "output_json": _deserialize_metadata(row["output_json"]),
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _chart_pack_review_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "review_date": row["review_date"],
        "week_start": row["week_start"],
        "week_end": row["week_end"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "title": row["title"],
        "thesis_context": row["thesis_context"],
        "chart_pack_json": _deserialize_metadata(row["chart_pack_json"]),
        "tradingview_alerts_json": _deserialize_metadata(row["tradingview_alerts_json"]),
        "synthesis_markdown": row["synthesis_markdown"],
        "structured_summary_json": _deserialize_metadata(row["structured_summary_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _report_job_filter_clause(
    *,
    job_type: str | None,
    cadence: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if job_type is not None:
        clauses.append("job_type = ?")
        values.append(validate_report_job_type(job_type))
    if cadence is not None:
        clauses.append("cadence = ?")
        values.append(validate_report_job_cadence(cadence))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_report_job_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _report_run_filter_clause(
    *,
    job_id: str | None,
    run_type: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if job_id is not None:
        clauses.append("job_id = ?")
        values.append(_validate_required_text("job_id", job_id))
    if run_type is not None:
        clauses.append("run_type = ?")
        values.append(validate_report_run_type(run_type))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_report_run_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _chart_pack_review_filter_clause(
    *,
    source_type: str | None,
    status: str | None,
    week_start: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if source_type is not None:
        clauses.append("source_type = ?")
        values.append(validate_chart_pack_review_source_type(source_type))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_chart_pack_review_status(status))
    if week_start is not None:
        clauses.append("week_start = ?")
        values.append(_validate_iso_date("week_start", week_start))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


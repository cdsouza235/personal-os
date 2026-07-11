"""Dev/test state helpers for todoist_tasks and calendar_blocks tables."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from personalos import execution_rails as rails

from personalos.state._shared import (
    _utc_now,
    _validate_iso_datetime,
    _validate_required_text,
    _validate_text,
)

EXECUTION_RAIL_STATE_TABLES = ("todoist_tasks", "calendar_blocks")


def build_todoist_task_record(
    *,
    task_title: str,
    source_type: str,
    source_id: str,
    project: str,
    todoist_task_id: str | None = None,
    description: str = "",
    labels: list[str] | None = None,
    due_date_or_due_string: str = "",
    priority: int = 1,
    risk_level: str = "low",
    approval_mode: str | None = None,
    dedupe_key: str | None = None,
    status: str | None = None,
    external_task_id: str | None = None,
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    task_title = _validate_required_text("task_title", task_title)
    source_type = _validate_required_text("source_type", source_type)
    source_id = _validate_required_text("source_id", source_id)
    project = _validate_required_text("project", project)
    description = _validate_text("description", description)
    labels_list = rails.validate_labels([] if labels is None else labels)
    due_date_or_due_string = _validate_text("due_date_or_due_string", due_date_or_due_string)
    priority = rails.validate_todoist_priority(priority)
    risk_level = rails.validate_risk_level(risk_level)
    approval_mode = rails.validate_approval_mode(approval_mode, risk_level=risk_level)
    status = rails.validate_execution_status(
        status or rails.default_status_for_approval(approval_mode)
    )
    dedupe_key = (
        rails.normalize_dedupe_key(dedupe_key)
        if dedupe_key is not None
        else rails.generate_dedupe_key(
            module_name="todoist",
            object_type="task",
            source_type=source_type,
            source_id=source_id,
            title=task_title,
            scheduled_marker=due_date_or_due_string or "no-due",
        )
    )
    todoist_task_id = (
        _validate_required_text("todoist_task_id", todoist_task_id)
        if todoist_task_id is not None
        else rails.stable_local_id("todoist-task", dedupe_key)
    )
    if external_task_id is not None:
        external_task_id = _validate_required_text("external_task_id", external_task_id)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)
    return {
        "todoist_task_id": todoist_task_id,
        "task_title": task_title,
        "description": description,
        "source_type": source_type,
        "source_id": source_id,
        "project": project,
        "labels": labels_list,
        "due_date_or_due_string": due_date_or_due_string,
        "priority": priority,
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "dedupe_key": dedupe_key,
        "status": status,
        "external_task_id": external_task_id,
        "created_at_utc": created_at,
        "updated_at_utc": updated_at,
    }


def create_todoist_task(
    connection: sqlite3.Connection,
    **task_input: Any,
) -> dict[str, Any]:
    task = build_todoist_task_record(**task_input)
    existing = get_todoist_task_by_dedupe_key(connection, task["dedupe_key"])
    if existing is not None:
        raise rails.DedupeConflictError(
            f"Todoist task dedupe_key already exists: {task['dedupe_key']}"
        )

    with connection:
        connection.execute(
            """
            INSERT INTO todoist_tasks (
                todoist_task_id,
                task_title,
                description,
                source_type,
                source_id,
                project,
                labels_json,
                due_date_or_due_string,
                priority,
                risk_level,
                approval_mode,
                dedupe_key,
                status,
                external_task_id,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["todoist_task_id"],
                task["task_title"],
                task["description"],
                task["source_type"],
                task["source_id"],
                task["project"],
                _serialize_labels(task["labels"]),
                task["due_date_or_due_string"],
                task["priority"],
                task["risk_level"],
                task["approval_mode"],
                task["dedupe_key"],
                task["status"],
                task["external_task_id"],
                task["created_at_utc"],
                task["updated_at_utc"],
            ),
        )

    persisted = get_todoist_task(connection, task["todoist_task_id"])
    if persisted is None:
        raise RuntimeError(f"Todoist task was not persisted: {task['todoist_task_id']}")
    return persisted


def get_todoist_task(
    connection: sqlite3.Connection,
    todoist_task_id: str,
) -> dict[str, Any] | None:
    todoist_task_id = _validate_required_text("todoist_task_id", todoist_task_id)
    row = connection.execute(
        """
        SELECT
            todoist_task_id,
            task_title,
            description,
            source_type,
            source_id,
            project,
            labels_json,
            due_date_or_due_string,
            priority,
            risk_level,
            approval_mode,
            dedupe_key,
            status,
            external_task_id,
            created_at_utc,
            updated_at_utc
        FROM todoist_tasks
        WHERE todoist_task_id = ?
        """,
        (todoist_task_id,),
    ).fetchone()
    return _todoist_task_row_to_dict(row) if row is not None else None


def get_todoist_task_by_dedupe_key(
    connection: sqlite3.Connection,
    dedupe_key: str,
) -> dict[str, Any] | None:
    dedupe_key = rails.normalize_dedupe_key(dedupe_key)
    row = connection.execute(
        """
        SELECT
            todoist_task_id,
            task_title,
            description,
            source_type,
            source_id,
            project,
            labels_json,
            due_date_or_due_string,
            priority,
            risk_level,
            approval_mode,
            dedupe_key,
            status,
            external_task_id,
            created_at_utc,
            updated_at_utc
        FROM todoist_tasks
        WHERE dedupe_key = ?
        """,
        (dedupe_key,),
    ).fetchone()
    return _todoist_task_row_to_dict(row) if row is not None else None


def list_todoist_tasks(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    project: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _todoist_task_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        project=project,
    )
    rows = connection.execute(
        f"""
        SELECT
            todoist_task_id,
            task_title,
            description,
            source_type,
            source_id,
            project,
            labels_json,
            due_date_or_due_string,
            priority,
            risk_level,
            approval_mode,
            dedupe_key,
            status,
            external_task_id,
            created_at_utc,
            updated_at_utc
        FROM todoist_tasks
        {where_clause}
        ORDER BY created_at_utc DESC, todoist_task_id
        """,
        values,
    ).fetchall()
    return [_todoist_task_row_to_dict(row) for row in rows]


def count_todoist_tasks(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    project: str | None = None,
) -> int:
    where_clause, values = _todoist_task_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        project=project,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM todoist_tasks {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def update_todoist_task_status(
    connection: sqlite3.Connection,
    *,
    todoist_task_id: str,
    status: str,
    external_task_id: str | None = None,
    update_external_task_id: bool = False,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    todoist_task_id = _validate_required_text("todoist_task_id", todoist_task_id)
    status = rails.validate_execution_status(status)
    if external_task_id is not None:
        external_task_id = _validate_required_text("external_task_id", external_task_id)
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or _utc_now())
    current = get_todoist_task(connection, todoist_task_id)
    if current is None:
        raise ValueError(f"Todoist task does not exist: {todoist_task_id}")

    if update_external_task_id:
        with connection:
            connection.execute(
                """
                UPDATE todoist_tasks
                SET status = ?,
                    external_task_id = ?,
                    updated_at_utc = ?
                WHERE todoist_task_id = ?
                """,
                (status, external_task_id, updated_at, todoist_task_id),
            )
    else:
        with connection:
            connection.execute(
                """
                UPDATE todoist_tasks
                SET status = ?,
                    updated_at_utc = ?
                WHERE todoist_task_id = ?
                """,
                (status, updated_at, todoist_task_id),
            )

    updated = get_todoist_task(connection, todoist_task_id)
    if updated is None:
        raise RuntimeError(f"Todoist task was not found after update: {todoist_task_id}")
    return updated


def build_calendar_block_record(
    *,
    title: str,
    source_type: str,
    source_id: str,
    start_time: str,
    end_time: str,
    duration_minutes: int,
    calendar_id: str,
    timezone: str,
    calendar_block_id: str | None = None,
    description: str = "",
    risk_level: str = "low",
    approval_mode: str | None = None,
    dedupe_key: str | None = None,
    status: str | None = None,
    external_event_id: str | None = None,
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    title = _validate_required_text("title", title)
    source_type = _validate_required_text("source_type", source_type)
    source_id = _validate_required_text("source_id", source_id)
    description = _validate_text("description", description)
    start_time = _validate_required_text("start_time", start_time)
    end_time = _validate_required_text("end_time", end_time)
    duration_minutes = rails.validate_duration_matches_window(
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
    )
    calendar_id = _validate_required_text("calendar_id", calendar_id)
    timezone = _validate_required_text("timezone", timezone)
    risk_level = rails.validate_risk_level(risk_level)
    approval_mode = rails.validate_approval_mode(approval_mode, risk_level=risk_level)
    status = rails.validate_execution_status(
        status or rails.default_status_for_approval(approval_mode)
    )
    dedupe_key = (
        rails.normalize_dedupe_key(dedupe_key)
        if dedupe_key is not None
        else rails.generate_dedupe_key(
            module_name="calendar",
            object_type="block",
            source_type=source_type,
            source_id=source_id,
            title=title,
            scheduled_marker=start_time,
        )
    )
    calendar_block_id = (
        _validate_required_text("calendar_block_id", calendar_block_id)
        if calendar_block_id is not None
        else rails.stable_local_id("calendar-block", dedupe_key)
    )
    if external_event_id is not None:
        external_event_id = _validate_required_text("external_event_id", external_event_id)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)
    return {
        "calendar_block_id": calendar_block_id,
        "title": title,
        "description": description,
        "source_type": source_type,
        "source_id": source_id,
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "calendar_id": calendar_id,
        "timezone": timezone,
        "approval_mode": approval_mode,
        "risk_level": risk_level,
        "dedupe_key": dedupe_key,
        "status": status,
        "external_event_id": external_event_id,
        "created_at_utc": created_at,
        "updated_at_utc": updated_at,
    }


def create_calendar_block(
    connection: sqlite3.Connection,
    **block_input: Any,
) -> dict[str, Any]:
    block = build_calendar_block_record(**block_input)
    existing = get_calendar_block_by_dedupe_key(connection, block["dedupe_key"])
    if existing is not None:
        raise rails.DedupeConflictError(
            f"Calendar block dedupe_key already exists: {block['dedupe_key']}"
        )

    with connection:
        connection.execute(
            """
            INSERT INTO calendar_blocks (
                calendar_block_id,
                title,
                description,
                source_type,
                source_id,
                start_time,
                end_time,
                duration_minutes,
                calendar_id,
                timezone,
                approval_mode,
                risk_level,
                dedupe_key,
                status,
                external_event_id,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block["calendar_block_id"],
                block["title"],
                block["description"],
                block["source_type"],
                block["source_id"],
                block["start_time"],
                block["end_time"],
                block["duration_minutes"],
                block["calendar_id"],
                block["timezone"],
                block["approval_mode"],
                block["risk_level"],
                block["dedupe_key"],
                block["status"],
                block["external_event_id"],
                block["created_at_utc"],
                block["updated_at_utc"],
            ),
        )

    persisted = get_calendar_block(connection, block["calendar_block_id"])
    if persisted is None:
        raise RuntimeError(f"Calendar block was not persisted: {block['calendar_block_id']}")
    return persisted


def get_calendar_block(
    connection: sqlite3.Connection,
    calendar_block_id: str,
) -> dict[str, Any] | None:
    calendar_block_id = _validate_required_text("calendar_block_id", calendar_block_id)
    row = connection.execute(
        """
        SELECT
            calendar_block_id,
            title,
            description,
            source_type,
            source_id,
            start_time,
            end_time,
            duration_minutes,
            calendar_id,
            timezone,
            approval_mode,
            risk_level,
            dedupe_key,
            status,
            external_event_id,
            created_at_utc,
            updated_at_utc
        FROM calendar_blocks
        WHERE calendar_block_id = ?
        """,
        (calendar_block_id,),
    ).fetchone()
    return _calendar_block_row_to_dict(row) if row is not None else None


def get_calendar_block_by_dedupe_key(
    connection: sqlite3.Connection,
    dedupe_key: str,
) -> dict[str, Any] | None:
    dedupe_key = rails.normalize_dedupe_key(dedupe_key)
    row = connection.execute(
        """
        SELECT
            calendar_block_id,
            title,
            description,
            source_type,
            source_id,
            start_time,
            end_time,
            duration_minutes,
            calendar_id,
            timezone,
            approval_mode,
            risk_level,
            dedupe_key,
            status,
            external_event_id,
            created_at_utc,
            updated_at_utc
        FROM calendar_blocks
        WHERE dedupe_key = ?
        """,
        (dedupe_key,),
    ).fetchone()
    return _calendar_block_row_to_dict(row) if row is not None else None


def list_calendar_blocks(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    calendar_id: str | None = None,
    time_min: str | None = None,
    time_max: str | None = None,
) -> list[dict[str, Any]]:
    time_min_filter = _validate_calendar_filter_datetime("time_min", time_min)
    time_max_filter = _validate_calendar_filter_datetime("time_max", time_max)
    where_clause, values = _calendar_block_non_time_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
    )
    rows = connection.execute(
        f"""
        SELECT
            calendar_block_id,
            title,
            description,
            source_type,
            source_id,
            start_time,
            end_time,
            duration_minutes,
            calendar_id,
            timezone,
            approval_mode,
            risk_level,
            dedupe_key,
            status,
            external_event_id,
            created_at_utc,
            updated_at_utc
        FROM calendar_blocks
        {where_clause}
        ORDER BY start_time, calendar_block_id
        """,
        values,
    ).fetchall()
    blocks = [_calendar_block_row_to_dict(row) for row in rows]
    filtered_blocks = [
        block
        for block in blocks
        if _calendar_block_overlaps_window(
            block,
            time_min=time_min_filter,
            time_max=time_max_filter,
        )
    ]
    return sorted(filtered_blocks, key=_calendar_block_sort_key)


def count_calendar_blocks(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    calendar_id: str | None = None,
    time_min: str | None = None,
    time_max: str | None = None,
) -> int:
    if time_min is not None or time_max is not None:
        return len(
            list_calendar_blocks(
                connection,
                status=status,
                risk_level=risk_level,
                approval_mode=approval_mode,
                source_type=source_type,
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
            )
        )

    where_clause, values = _calendar_block_non_time_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM calendar_blocks {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def update_calendar_block_status(
    connection: sqlite3.Connection,
    *,
    calendar_block_id: str,
    status: str,
    external_event_id: str | None = None,
    update_external_event_id: bool = False,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    calendar_block_id = _validate_required_text("calendar_block_id", calendar_block_id)
    status = rails.validate_execution_status(status)
    if external_event_id is not None:
        external_event_id = _validate_required_text("external_event_id", external_event_id)
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or _utc_now())
    current = get_calendar_block(connection, calendar_block_id)
    if current is None:
        raise ValueError(f"Calendar block does not exist: {calendar_block_id}")

    if update_external_event_id:
        with connection:
            connection.execute(
                """
                UPDATE calendar_blocks
                SET status = ?,
                    external_event_id = ?,
                    updated_at_utc = ?
                WHERE calendar_block_id = ?
                """,
                (status, external_event_id, updated_at, calendar_block_id),
            )
    else:
        with connection:
            connection.execute(
                """
                UPDATE calendar_blocks
                SET status = ?,
                    updated_at_utc = ?
                WHERE calendar_block_id = ?
                """,
                (status, updated_at, calendar_block_id),
            )

    updated = get_calendar_block(connection, calendar_block_id)
    if updated is None:
        raise RuntimeError(f"Calendar block was not found after update: {calendar_block_id}")
    return updated


def _todoist_task_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "todoist_task_id": row["todoist_task_id"],
        "task_title": row["task_title"],
        "description": row["description"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "project": row["project"],
        "labels": _deserialize_labels(row["labels_json"]),
        "due_date_or_due_string": row["due_date_or_due_string"],
        "priority": row["priority"],
        "risk_level": row["risk_level"],
        "approval_mode": row["approval_mode"],
        "dedupe_key": row["dedupe_key"],
        "status": row["status"],
        "external_task_id": row["external_task_id"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }


def _calendar_block_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "calendar_block_id": row["calendar_block_id"],
        "title": row["title"],
        "description": row["description"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "duration_minutes": row["duration_minutes"],
        "calendar_id": row["calendar_id"],
        "timezone": row["timezone"],
        "approval_mode": row["approval_mode"],
        "risk_level": row["risk_level"],
        "dedupe_key": row["dedupe_key"],
        "status": row["status"],
        "external_event_id": row["external_event_id"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }


def _todoist_task_filter_clause(
    *,
    status: str | None,
    risk_level: str | None,
    approval_mode: str | None,
    source_type: str | None,
    project: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if status is not None:
        clauses.append("status = ?")
        values.append(rails.validate_execution_status(status))
    if risk_level is not None:
        clauses.append("risk_level = ?")
        values.append(rails.validate_risk_level(risk_level))
    if approval_mode is not None:
        clauses.append("approval_mode = ?")
        values.append(rails.validate_approval_mode(approval_mode, risk_level=risk_level or "low"))
    if source_type is not None:
        clauses.append("source_type = ?")
        values.append(_validate_required_text("source_type", source_type))
    if project is not None:
        clauses.append("project = ?")
        values.append(_validate_required_text("project", project))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _calendar_block_non_time_filter_clause(
    *,
    status: str | None,
    risk_level: str | None,
    approval_mode: str | None,
    source_type: str | None,
    calendar_id: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if status is not None:
        clauses.append("status = ?")
        values.append(rails.validate_execution_status(status))
    if risk_level is not None:
        clauses.append("risk_level = ?")
        values.append(rails.validate_risk_level(risk_level))
    if approval_mode is not None:
        clauses.append("approval_mode = ?")
        values.append(rails.validate_approval_mode(approval_mode, risk_level=risk_level or "low"))
    if source_type is not None:
        clauses.append("source_type = ?")
        values.append(_validate_required_text("source_type", source_type))
    if calendar_id is not None:
        clauses.append("calendar_id = ?")
        values.append(_validate_required_text("calendar_id", calendar_id))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _validate_calendar_filter_datetime(field_name: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    return rails.validate_timezone_aware_datetime(field_name, value)


def _calendar_block_overlaps_window(
    block: Mapping[str, Any],
    *,
    time_min: datetime | None,
    time_max: datetime | None,
) -> bool:
    start_time = rails.validate_timezone_aware_datetime("start_time", block["start_time"])
    end_time = rails.validate_timezone_aware_datetime("end_time", block["end_time"])
    if time_min is not None and end_time < time_min:
        return False
    if time_max is not None and start_time > time_max:
        return False
    return True


def _calendar_block_sort_key(block: Mapping[str, Any]) -> tuple[datetime, str]:
    start_time = rails.validate_timezone_aware_datetime("start_time", block["start_time"])
    return start_time, str(block["calendar_block_id"])


def _serialize_labels(labels: list[str]) -> str:
    return json.dumps(
        rails.validate_labels(labels),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deserialize_labels(labels_json: str) -> list[str]:
    labels = json.loads(labels_json)
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        raise ValueError("labels_json must decode to a list of strings")
    return labels


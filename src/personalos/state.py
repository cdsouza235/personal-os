"""Dev/test SQLite state-store helpers for core foundation tables."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from personalos import execution_rails as rails

CORE_STATE_TABLES = ("routines", "priorities", "projects", "followups")
ROUTINE_COMPLETION_TABLE = "routine_completions"
EXECUTION_RAIL_STATE_TABLES = ("todoist_tasks", "calendar_blocks")
COUNTABLE_STATE_TABLES = CORE_STATE_TABLES + (ROUTINE_COMPLETION_TABLE,) + EXECUTION_RAIL_STATE_TABLES
ROUTINE_STATUSES = ("active", "paused", "archived")
PRIORITY_STATUSES = ("active", "paused", "completed", "archived")


def get_permission_setting(connection: sqlite3.Connection, category: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT category, mode, metadata_json, updated_at_utc, updated_by
        FROM permission_settings
        WHERE category = ?
        """,
        (category,),
    ).fetchone()
    return _permission_row_to_dict(row) if row is not None else None


def list_permission_settings(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT category, mode, metadata_json, updated_at_utc, updated_by
        FROM permission_settings
        ORDER BY category
        """
    ).fetchall()
    return [_permission_row_to_dict(row) for row in rows]


def upsert_permission_setting(
    connection: sqlite3.Connection,
    *,
    category: str,
    mode: str,
    metadata: Mapping[str, Any] | None = None,
    updated_by: str = "personalos.state",
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    metadata_json = _serialize_metadata(
        _validate_metadata("metadata", {} if metadata is None else metadata)
    )
    updated_at = updated_at_utc or _utc_now()

    with connection:
        connection.execute(
            """
            INSERT INTO permission_settings (
                category,
                mode,
                metadata_json,
                updated_at_utc,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                mode = excluded.mode,
                metadata_json = excluded.metadata_json,
                updated_at_utc = excluded.updated_at_utc,
                updated_by = excluded.updated_by
            """,
            (category, mode, metadata_json, updated_at, updated_by),
        )

    setting = get_permission_setting(connection, category)
    if setting is None:
        raise RuntimeError(f"Permission setting was not persisted for category: {category}")
    return setting


def list_routines(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            routine_id,
            name,
            status,
            enabled,
            settings_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM routines
        ORDER BY name, routine_id
        """
    ).fetchall()
    return [_routine_row_to_dict(row) for row in rows]


def get_routine(connection: sqlite3.Connection, routine_id: str) -> dict[str, Any] | None:
    routine_id = _validate_required_text("routine_id", routine_id)
    row = connection.execute(
        """
        SELECT
            routine_id,
            name,
            status,
            enabled,
            settings_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM routines
        WHERE routine_id = ?
        """,
        (routine_id,),
    ).fetchone()
    return _routine_row_to_dict(row) if row is not None else None


def count_routines(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "routines")


def create_routine(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    name: str,
    status: str = "active",
    enabled: bool = True,
    settings: Mapping[str, Any] | None = None,
    notes: str = "",
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    name = _validate_required_text("name", name)
    status = validate_routine_status(status)
    enabled = validate_routine_enabled(enabled)
    notes = _validate_text("notes", notes)
    settings_json = _serialize_metadata(settings or {})
    created_at = created_at_utc or _utc_now()
    updated_at = updated_at_utc or created_at

    with connection:
        connection.execute(
            """
            INSERT INTO routines (
                routine_id,
                name,
                status,
                enabled,
                settings_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routine_id,
                name,
                status,
                int(enabled),
                settings_json,
                notes,
                created_at,
                updated_at,
            ),
        )

    routine = get_routine(connection, routine_id)
    if routine is None:
        raise RuntimeError(f"Routine was not persisted for routine_id: {routine_id}")
    return routine


def update_routine_status_enabled(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    status: str | None = None,
    enabled: bool | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    if status is None and enabled is None:
        raise ValueError("status or enabled must be provided")

    current = get_routine(connection, routine_id)
    if current is None:
        raise ValueError(f"Routine does not exist: {routine_id}")

    next_status = current["status"] if status is None else validate_routine_status(status)
    next_enabled = current["enabled"] if enabled is None else validate_routine_enabled(enabled)
    updated_at = updated_at_utc or _utc_now()

    with connection:
        connection.execute(
            """
            UPDATE routines
            SET status = ?,
                enabled = ?,
                updated_at_utc = ?
            WHERE routine_id = ?
            """,
            (next_status, int(next_enabled), updated_at, routine_id),
        )

    routine = get_routine(connection, routine_id)
    if routine is None:
        raise RuntimeError(f"Routine was not found after update: {routine_id}")
    return routine


def get_routine_completion(
    connection: sqlite3.Connection,
    completion_id: str,
) -> dict[str, Any] | None:
    completion_id = _validate_required_text("completion_id", completion_id)
    row = connection.execute(
        """
        SELECT
            completion_id,
            routine_id,
            completed_for_date,
            completed_at_utc,
            source,
            metadata_json,
            created_at_utc
        FROM routine_completions
        WHERE completion_id = ?
        """,
        (completion_id,),
    ).fetchone()
    return _routine_completion_row_to_dict(row) if row is not None else None


def list_routine_completions(
    connection: sqlite3.Connection,
    *,
    routine_id: str | None = None,
) -> list[dict[str, Any]]:
    if routine_id is None:
        rows = connection.execute(
            """
            SELECT
                completion_id,
                routine_id,
                completed_for_date,
                completed_at_utc,
                source,
                metadata_json,
                created_at_utc
            FROM routine_completions
            ORDER BY completed_at_utc DESC, completion_id
            """
        ).fetchall()
    else:
        routine_id = _validate_required_text("routine_id", routine_id)
        rows = connection.execute(
            """
            SELECT
                completion_id,
                routine_id,
                completed_for_date,
                completed_at_utc,
                source,
                metadata_json,
                created_at_utc
            FROM routine_completions
            WHERE routine_id = ?
            ORDER BY completed_at_utc DESC, completion_id
            """,
            (routine_id,),
        ).fetchall()
    return [_routine_completion_row_to_dict(row) for row in rows]


def count_routine_completions(
    connection: sqlite3.Connection,
    *,
    routine_id: str | None = None,
) -> int:
    if routine_id is None:
        return _count_rows(connection, ROUTINE_COMPLETION_TABLE)

    routine_id = _validate_required_text("routine_id", routine_id)
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM routine_completions WHERE routine_id = ?",
            (routine_id,),
        ).fetchone()[0]
    )


def record_routine_completion(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    completed_for_date: str,
    completion_id: str | None = None,
    completed_at_utc: str | None = None,
    source: str = "personalos.state",
    metadata: Mapping[str, Any] | None = None,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    completed_for_date = _validate_iso_date("completed_for_date", completed_for_date)
    completion_id = completion_id or str(uuid4())
    completion_id = _validate_required_text("completion_id", completion_id)
    source = _validate_required_text("source", source)
    metadata_json = _serialize_metadata(
        _validate_metadata("metadata", {} if metadata is None else metadata)
    )
    routine = get_routine(connection, routine_id)
    if routine is None:
        raise ValueError(f"Routine does not exist: {routine_id}")
    _validate_routine_can_be_completed(routine)

    completed_at = completed_at_utc or _utc_now()
    created_at = created_at_utc or completed_at

    with connection:
        connection.execute(
            """
            INSERT INTO routine_completions (
                completion_id,
                routine_id,
                completed_for_date,
                completed_at_utc,
                source,
                metadata_json,
                created_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                completion_id,
                routine_id,
                completed_for_date,
                completed_at,
                source,
                metadata_json,
                created_at,
            ),
        )

    completion = get_routine_completion(connection, completion_id)
    if completion is None:
        raise RuntimeError(f"Routine completion was not persisted: {completion_id}")
    return completion


def validate_routine_status(status: str) -> str:
    if not isinstance(status, str) or status not in ROUTINE_STATUSES:
        allowed = ", ".join(ROUTINE_STATUSES)
        raise ValueError(f"routine status must be one of: {allowed}")
    return status


def validate_routine_enabled(enabled: bool) -> bool:
    if type(enabled) is not bool:
        raise ValueError("routine enabled must be a boolean")
    return enabled


def list_priorities(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    if status is None:
        return _list_metadata_rows(
            connection,
            table_name="priorities",
            id_column="priority_id",
            order_columns=("title", "priority_id"),
        )

    status = validate_priority_status(status)
    rows = connection.execute(
        """
        SELECT
            priority_id,
            title,
            status,
            metadata_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM priorities
        WHERE status = ?
        ORDER BY title, priority_id
        """,
        (status,),
    ).fetchall()
    return [_metadata_row_to_dict(row, id_column="priority_id") for row in rows]


def get_priority(connection: sqlite3.Connection, priority_id: str) -> dict[str, Any] | None:
    priority_id = _validate_required_text("priority_id", priority_id)
    row = connection.execute(
        """
        SELECT
            priority_id,
            title,
            status,
            metadata_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM priorities
        WHERE priority_id = ?
        """,
        (priority_id,),
    ).fetchone()
    return _metadata_row_to_dict(row, id_column="priority_id") if row is not None else None


def count_priorities(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
) -> int:
    if status is None:
        return _count_rows(connection, "priorities")

    status = validate_priority_status(status)
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM priorities WHERE status = ?",
            (status,),
        ).fetchone()[0]
    )


def create_priority(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    title: str,
    status: str = "active",
    metadata: Mapping[str, Any] | None = None,
    notes: str = "",
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    priority_id = _validate_required_text("priority_id", priority_id)
    title = _validate_required_text("title", title)
    status = validate_priority_status(status)
    metadata_json = _serialize_metadata(
        _validate_metadata("metadata", {} if metadata is None else metadata)
    )
    notes = _validate_text("notes", notes)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)

    with connection:
        connection.execute(
            """
            INSERT INTO priorities (
                priority_id,
                title,
                status,
                metadata_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                priority_id,
                title,
                status,
                metadata_json,
                notes,
                created_at,
                updated_at,
            ),
        )

    priority = get_priority(connection, priority_id)
    if priority is None:
        raise RuntimeError(f"Priority was not persisted for priority_id: {priority_id}")
    return priority


def update_priority(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    title: str | None = None,
    status: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    notes: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    priority_id = _validate_required_text("priority_id", priority_id)
    if title is None and status is None and metadata is None and notes is None:
        raise ValueError("title, status, metadata, or notes must be provided")

    current = get_priority(connection, priority_id)
    if current is None:
        raise ValueError(f"Priority does not exist: {priority_id}")

    next_title = current["title"] if title is None else _validate_required_text("title", title)
    next_status = current["status"] if status is None else validate_priority_status(status)
    next_metadata = (
        current["metadata"] if metadata is None else _validate_metadata("metadata", metadata)
    )
    metadata_json = _serialize_metadata(next_metadata)
    next_notes = current["notes"] if notes is None else _validate_text("notes", notes)
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or _utc_now())

    with connection:
        connection.execute(
            """
            UPDATE priorities
            SET title = ?,
                status = ?,
                metadata_json = ?,
                notes = ?,
                updated_at_utc = ?
            WHERE priority_id = ?
            """,
            (
                next_title,
                next_status,
                metadata_json,
                next_notes,
                updated_at,
                priority_id,
            ),
        )

    priority = get_priority(connection, priority_id)
    if priority is None:
        raise RuntimeError(f"Priority was not found after update: {priority_id}")
    return priority


def update_priority_status(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    status: str,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    return update_priority(
        connection,
        priority_id=priority_id,
        status=status,
        updated_at_utc=updated_at_utc,
    )


def validate_priority_status(status: str) -> str:
    if not isinstance(status, str) or status not in PRIORITY_STATUSES:
        allowed = ", ".join(PRIORITY_STATUSES)
        raise ValueError(f"priority status must be one of: {allowed}")
    return status


def list_active_priorities(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return list_priorities(connection, status="active")


def count_priorities_by_status(connection: sqlite3.Connection) -> dict[str, int]:
    counts = dict.fromkeys(PRIORITY_STATUSES, 0)
    rows = connection.execute(
        """
        SELECT status, COUNT(*) AS status_count
        FROM priorities
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()
    for row in rows:
        status = validate_priority_status(row["status"])
        counts[status] = int(row["status_count"])
    return counts


def summarize_priorities(connection: sqlite3.Connection) -> dict[str, Any]:
    counts_by_status = count_priorities_by_status(connection)
    active_priorities = list_active_priorities(connection)
    return {
        "total_count": count_priorities(connection),
        "counts_by_status": counts_by_status,
        "active_count": counts_by_status["active"],
        "active_priorities": active_priorities,
    }


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
    where_clause, values = _calendar_block_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
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
    return [_calendar_block_row_to_dict(row) for row in rows]


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
    where_clause, values = _calendar_block_filter_clause(
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
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


def list_projects(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_metadata_rows(
        connection,
        table_name="projects",
        id_column="project_id",
        order_columns=("title", "project_id"),
    )


def count_projects(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "projects")


def list_followups(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            followup_id,
            title,
            status,
            source,
            metadata_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM followups
        ORDER BY title, followup_id
        """
    ).fetchall()
    return [_metadata_row_to_dict(row, id_column="followup_id") for row in rows]


def count_followups(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "followups")


def _list_metadata_rows(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    id_column: str,
    order_columns: tuple[str, str],
) -> list[dict[str, Any]]:
    if table_name not in CORE_STATE_TABLES:
        raise ValueError(f"Unsupported state table: {table_name}")

    first_order_column, second_order_column = order_columns
    rows = connection.execute(
        f"""
        SELECT
            {id_column},
            title,
            status,
            metadata_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM {table_name}
        ORDER BY {first_order_column}, {second_order_column}
        """
    ).fetchall()
    return [_metadata_row_to_dict(row, id_column=id_column) for row in rows]


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    if table_name not in COUNTABLE_STATE_TABLES:
        raise ValueError(f"Unsupported state table: {table_name}")

    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _permission_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "category": row["category"],
        "mode": row["mode"],
        "metadata": _deserialize_metadata(row["metadata_json"]),
        "updated_at_utc": row["updated_at_utc"],
        "updated_by": row["updated_by"],
    }


def _routine_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "routine_id": row["routine_id"],
        "name": row["name"],
        "status": row["status"],
        "enabled": bool(row["enabled"]),
        "settings": _deserialize_metadata(row["settings_json"]),
        "notes": row["notes"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }


def _routine_completion_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "completion_id": row["completion_id"],
        "routine_id": row["routine_id"],
        "completed_for_date": row["completed_for_date"],
        "completed_at_utc": row["completed_at_utc"],
        "source": row["source"],
        "metadata": _deserialize_metadata(row["metadata_json"]),
        "created_at_utc": row["created_at_utc"],
    }


def _metadata_row_to_dict(row: sqlite3.Row, *, id_column: str) -> dict[str, Any]:
    item = {
        id_column: row[id_column],
        "title": row["title"],
        "status": row["status"],
        "metadata": _deserialize_metadata(row["metadata_json"]),
        "notes": row["notes"],
        "created_at_utc": row["created_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
    }
    if "source" in row.keys():
        item["source"] = row["source"]
    return item


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


def _calendar_block_filter_clause(
    *,
    status: str | None,
    risk_level: str | None,
    approval_mode: str | None,
    source_type: str | None,
    calendar_id: str | None,
    time_min: str | None,
    time_max: str | None,
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
    if time_min is not None:
        rails.validate_timezone_aware_datetime("time_min", time_min)
        clauses.append("end_time >= ?")
        values.append(time_min)
    if time_max is not None:
        rails.validate_timezone_aware_datetime("time_max", time_max)
        clauses.append("start_time <= ?")
        values.append(time_max)

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


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


def _serialize_metadata(metadata: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(metadata),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deserialize_metadata(metadata_json: str) -> dict[str, Any]:
    metadata = json.loads(metadata_json)
    if not isinstance(metadata, dict):
        raise ValueError("metadata_json must decode to an object")
    return metadata


def _validate_metadata(field_name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON-safe object")
    return dict(value)


def _validate_required_text(field_name: str, value: str) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _validate_iso_date(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO date") from error
    return value


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


def _validate_routine_can_be_completed(routine: Mapping[str, Any]) -> None:
    if routine["status"] != "active":
        raise ValueError(f"Routine is not active: {routine['status']}")
    if not routine["enabled"]:
        raise ValueError("Routine is disabled")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

"""Priority, project, and followup state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.state._shared import (
    _count_rows,
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_required_text,
    _validate_text,
)

PRIORITY_STATUSES = ("active", "paused", "completed", "archived")


PROJECT_STATUSES = ("active", "paused", "completed", "archived")


FOLLOWUP_STATUSES = ("open", "proposed", "completed", "archived", "blocked")


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
    commit: bool = True,
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

    if commit:
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
    else:
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


def get_project(connection: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    project_id = _validate_required_text("project_id", project_id)
    row = connection.execute(
        """
        SELECT
            project_id,
            title,
            status,
            metadata_json,
            notes,
            created_at_utc,
            updated_at_utc
        FROM projects
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    return _metadata_row_to_dict(row, id_column="project_id") if row is not None else None


def create_project(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    title: str,
    status: str,
    metadata: Mapping[str, Any] | None = None,
    notes: str = "",
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    project_id = _validate_required_text("project_id", project_id)
    title = _validate_required_text("title", title)
    status = validate_project_status(status)
    metadata_json = _serialize_metadata(
        _validate_metadata("metadata", {} if metadata is None else metadata)
    )
    notes = _validate_text("notes", notes)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)

    if commit:
        with connection:
            connection.execute(
                """
                INSERT INTO projects (
                    project_id,
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
                    project_id,
                    title,
                    status,
                    metadata_json,
                    notes,
                    created_at,
                    updated_at,
                ),
            )
    else:
        connection.execute(
            """
            INSERT INTO projects (
                project_id,
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
                project_id,
                title,
                status,
                metadata_json,
                notes,
                created_at,
                updated_at,
            ),
        )

    project = get_project(connection, project_id)
    if project is None:
        raise RuntimeError(f"Project was not persisted for project_id: {project_id}")
    return project


def get_followup(connection: sqlite3.Connection, followup_id: str) -> dict[str, Any] | None:
    followup_id = _validate_required_text("followup_id", followup_id)
    row = connection.execute(
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
        WHERE followup_id = ?
        """,
        (followup_id,),
    ).fetchone()
    return _metadata_row_to_dict(row, id_column="followup_id") if row is not None else None


def create_followup(
    connection: sqlite3.Connection,
    *,
    followup_id: str,
    title: str,
    status: str,
    source: str,
    metadata: Mapping[str, Any] | None = None,
    notes: str = "",
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    followup_id = _validate_required_text("followup_id", followup_id)
    title = _validate_required_text("title", title)
    status = validate_followup_status(status)
    source = _validate_required_text("source", source)
    metadata_json = _serialize_metadata(
        _validate_metadata("metadata", {} if metadata is None else metadata)
    )
    notes = _validate_text("notes", notes)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)

    if commit:
        with connection:
            connection.execute(
                """
                INSERT INTO followups (
                    followup_id,
                    title,
                    status,
                    source,
                    metadata_json,
                    notes,
                    created_at_utc,
                    updated_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    followup_id,
                    title,
                    status,
                    source,
                    metadata_json,
                    notes,
                    created_at,
                    updated_at,
                ),
            )
    else:
        connection.execute(
            """
            INSERT INTO followups (
                followup_id,
                title,
                status,
                source,
                metadata_json,
                notes,
                created_at_utc,
                updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                followup_id,
                title,
                status,
                source,
                metadata_json,
                notes,
                created_at,
                updated_at,
            ),
        )

    followup = get_followup(connection, followup_id)
    if followup is None:
        raise RuntimeError(f"Follow-up was not persisted for followup_id: {followup_id}")
    return followup


def validate_priority_status(status: str) -> str:
    if not isinstance(status, str) or status not in PRIORITY_STATUSES:
        allowed = ", ".join(PRIORITY_STATUSES)
        raise ValueError(f"priority status must be one of: {allowed}")
    return status


def validate_project_status(status: str) -> str:
    if not isinstance(status, str) or status not in PROJECT_STATUSES:
        allowed = ", ".join(PROJECT_STATUSES)
        raise ValueError(f"project status must be one of: {allowed}")
    return status


def validate_followup_status(status: str) -> str:
    if not isinstance(status, str) or status not in FOLLOWUP_STATUSES:
        allowed = ", ".join(FOLLOWUP_STATUSES)
        raise ValueError(f"followup status must be one of: {allowed}")
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
    from personalos.state import CORE_STATE_TABLES

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


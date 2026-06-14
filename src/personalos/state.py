"""Dev/test SQLite state-store helpers for core foundation tables."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

CORE_STATE_TABLES = ("routines", "priorities", "projects", "followups")
ROUTINE_COMPLETION_TABLE = "routine_completions"
COUNTABLE_STATE_TABLES = CORE_STATE_TABLES + (ROUTINE_COMPLETION_TABLE,)
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

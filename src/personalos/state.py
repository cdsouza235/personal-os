"""Dev/test SQLite state-store helpers for Phase 2 foundation tables."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

CORE_STATE_TABLES = ("routines", "priorities", "projects", "followups")


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
    metadata_json = _serialize_metadata(metadata or {})
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


def count_routines(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "routines")


def list_priorities(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _list_metadata_rows(
        connection,
        table_name="priorities",
        id_column="priority_id",
        order_columns=("title", "priority_id"),
    )


def count_priorities(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "priorities")


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
    if table_name not in CORE_STATE_TABLES:
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

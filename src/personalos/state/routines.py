"""Routine and routine-completion state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from personalos.state._shared import (
    _count_rows,
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_iso_date,
    _validate_metadata,
    _validate_optional_nonnegative_int,
    _validate_required_text,
    _validate_text,
)

ROUTINE_COMPLETION_TABLE = "routine_completions"


ROUTINE_STATUSES = ("active", "paused", "archived")


ROUTINE_CADENCE_TYPES = (
    "daily",
    "weekdays",
    "x_times_per_week",
    "weekly",
    "every_n_days",
    "specific_days",
    "rotating_sequence",
    "manual_only",
    "weekly_target_count",
    "weekly_target_reps",
    "rotating_weekday_pool",
)


ROUTINE_MISSED_BEHAVIOR_TYPES = (
    "combine_with_next",
    "bump_schedule_by_one_day",
    "carry_forward_within_week",
    "skip_and_continue",
    "escalate_to_review",
)


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
            updated_at_utc,
            cadence_type,
            cadence_config_json,
            missed_behavior_default,
            rotation_group,
            weekly_target
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
            updated_at_utc,
            cadence_type,
            cadence_config_json,
            missed_behavior_default,
            rotation_group,
            weekly_target
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
    cadence_type: str | None = None,
    cadence_config: Mapping[str, Any] | None = None,
    missed_behavior_default: str | None = None,
    rotation_group: str | None = None,
    weekly_target: int | None = None,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    name = _validate_required_text("name", name)
    status = validate_routine_status(status)
    enabled = validate_routine_enabled(enabled)
    notes = _validate_text("notes", notes)
    settings_json = _serialize_metadata(settings or {})
    cadence_type = validate_routine_cadence_type(cadence_type)
    cadence_config_json = (
        _serialize_metadata(_validate_metadata("cadence_config", cadence_config))
        if cadence_config
        else None
    )
    missed_behavior_default = validate_routine_missed_behavior(missed_behavior_default)
    if rotation_group is not None:
        rotation_group = _validate_required_text("rotation_group", rotation_group)
    weekly_target = _validate_optional_nonnegative_int("weekly_target", weekly_target)
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
                updated_at_utc,
                cadence_type,
                cadence_config_json,
                missed_behavior_default,
                rotation_group,
                weekly_target
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                cadence_type,
                cadence_config_json,
                missed_behavior_default,
                rotation_group,
                weekly_target,
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


def update_routine(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    name: str | None = None,
    status: str | None = None,
    enabled: bool | None = None,
    settings: Mapping[str, Any] | None = None,
    notes: str | None = None,
    updated_at_utc: str | None = None,
    cadence_type: str | None = None,
    cadence_config: Mapping[str, Any] | None = None,
    missed_behavior_default: str | None = None,
    rotation_group: str | None = None,
    weekly_target: int | None = None,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    if (
        name is None
        and status is None
        and enabled is None
        and settings is None
        and notes is None
        and cadence_type is None
        and cadence_config is None
        and missed_behavior_default is None
        and rotation_group is None
        and weekly_target is None
    ):
        raise ValueError(
            "name, status, enabled, settings, notes, cadence_type, cadence_config, "
            "missed_behavior_default, rotation_group, or weekly_target must be provided"
        )

    current = get_routine(connection, routine_id)
    if current is None:
        raise ValueError(f"Routine does not exist: {routine_id}")

    next_name = current["name"] if name is None else _validate_required_text("name", name)
    next_status = current["status"] if status is None else validate_routine_status(status)
    next_enabled = current["enabled"] if enabled is None else validate_routine_enabled(enabled)
    next_settings = (
        current["settings"] if settings is None else _validate_metadata("settings", settings)
    )
    settings_json = _serialize_metadata(next_settings)
    next_notes = current["notes"] if notes is None else _validate_text("notes", notes)
    next_cadence_type = (
        current["cadence_type"]
        if cadence_type is None
        else validate_routine_cadence_type(cadence_type)
    )
    next_cadence_config = (
        current["cadence_config"]
        if cadence_config is None
        else _validate_metadata("cadence_config", cadence_config)
    )
    cadence_config_json = (
        _serialize_metadata(next_cadence_config) if next_cadence_config else None
    )
    next_missed_behavior_default = (
        current["missed_behavior_default"]
        if missed_behavior_default is None
        else validate_routine_missed_behavior(missed_behavior_default)
    )
    next_rotation_group = (
        current["rotation_group"]
        if rotation_group is None
        else _validate_required_text("rotation_group", rotation_group)
    )
    next_weekly_target = (
        current["weekly_target"]
        if weekly_target is None
        else _validate_optional_nonnegative_int("weekly_target", weekly_target)
    )
    updated_at = updated_at_utc or _utc_now()

    with connection:
        connection.execute(
            """
            UPDATE routines
            SET name = ?,
                status = ?,
                enabled = ?,
                settings_json = ?,
                notes = ?,
                updated_at_utc = ?,
                cadence_type = ?,
                cadence_config_json = ?,
                missed_behavior_default = ?,
                rotation_group = ?,
                weekly_target = ?
            WHERE routine_id = ?
            """,
            (
                next_name,
                next_status,
                int(next_enabled),
                settings_json,
                next_notes,
                updated_at,
                next_cadence_type,
                cadence_config_json,
                next_missed_behavior_default,
                next_rotation_group,
                next_weekly_target,
                routine_id,
            ),
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


def validate_routine_cadence_type(cadence_type: str | None) -> str | None:
    if cadence_type is None:
        return None
    if not isinstance(cadence_type, str) or cadence_type not in ROUTINE_CADENCE_TYPES:
        allowed = ", ".join(ROUTINE_CADENCE_TYPES)
        raise ValueError(f"routine cadence_type must be one of: {allowed}")
    return cadence_type


def validate_routine_missed_behavior(missed_behavior: str | None) -> str | None:
    if missed_behavior is None:
        return None
    if not isinstance(missed_behavior, str) or missed_behavior not in ROUTINE_MISSED_BEHAVIOR_TYPES:
        allowed = ", ".join(ROUTINE_MISSED_BEHAVIOR_TYPES)
        raise ValueError(f"routine missed_behavior_default must be one of: {allowed}")
    return missed_behavior


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
        "cadence_type": row["cadence_type"],
        "cadence_config": (
            {}
            if row["cadence_config_json"] is None
            else _deserialize_metadata(row["cadence_config_json"])
        ),
        "missed_behavior_default": row["missed_behavior_default"],
        "rotation_group": row["rotation_group"],
        "weekly_target": row["weekly_target"],
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


def _validate_routine_can_be_completed(routine: Mapping[str, Any]) -> None:
    if routine["status"] != "active":
        raise ValueError(f"Routine is not active: {routine['status']}")
    if not routine["enabled"]:
        raise ValueError("Routine is disabled")


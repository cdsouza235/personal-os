"""Dev/test-only routine engine foundation."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

from personalos.permissions import PermissionMode
from personalos.state import (
    create_routine,
    get_routine,
    list_routines,
    record_routine_completion,
    update_routine,
    update_routine_status_enabled,
)

ROUTINE_ENGINE_READ_PERMISSION = "routine_engine_dev_test_read"
ROUTINE_ENGINE_WRITE_PERMISSION = "routine_engine_dev_test_write"
ROUTINE_COMPLETION_SOURCE = "personalos.routines"


class RoutineEnginePermissionDenied(PermissionError):
    """Raised when the routine engine permission setting does not allow the action."""


def read_routine(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
) -> dict[str, Any] | None:
    require_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_READ_PERMISSION,
    )
    return get_routine(connection, routine_id)


def read_routines(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    require_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_READ_PERMISSION,
    )
    return list_routines(connection)


def create_routine_record(
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
    require_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_WRITE_PERMISSION,
    )
    return create_routine(
        connection,
        routine_id=routine_id,
        name=name,
        status=status,
        enabled=enabled,
        settings=settings,
        notes=notes,
        created_at_utc=created_at_utc,
        updated_at_utc=updated_at_utc,
    )


def update_routine_record_status_enabled(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    status: str | None = None,
    enabled: bool | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_WRITE_PERMISSION,
    )
    return update_routine_status_enabled(
        connection,
        routine_id=routine_id,
        status=status,
        enabled=enabled,
        updated_at_utc=updated_at_utc,
    )


def update_routine_record(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    name: str | None = None,
    status: str | None = None,
    enabled: bool | None = None,
    settings: Mapping[str, Any] | None = None,
    notes: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_WRITE_PERMISSION,
    )
    return update_routine(
        connection,
        routine_id=routine_id,
        name=name,
        status=status,
        enabled=enabled,
        settings=settings,
        notes=notes,
        updated_at_utc=updated_at_utc,
    )


def complete_routine(
    connection: sqlite3.Connection,
    *,
    routine_id: str,
    completed_for_date: str,
    dry_run: bool = True,
    metadata: Mapping[str, Any] | None = None,
    completed_at_utc: str | None = None,
    source: str = ROUTINE_COMPLETION_SOURCE,
) -> dict[str, Any]:
    routine_id = _validate_required_text("routine_id", routine_id)
    completed_for_date = _validate_iso_date("completed_for_date", completed_for_date)
    source = _validate_required_text("source", source)
    metadata = _validate_metadata(metadata or {})
    completed_at = completed_at_utc or _utc_now()

    permission = evaluate_routine_engine_permission(
        connection,
        category=ROUTINE_ENGINE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            dry_run=dry_run,
            permission=permission,
            routine=None,
        )

    routine = get_routine(connection, routine_id)
    block_reason = routine_completion_block_reason(routine)
    if block_reason is not None:
        return _blocked_result(
            reason=block_reason,
            dry_run=dry_run,
            permission=permission,
            routine=routine,
        )

    intended_completion = {
        "routine_id": routine_id,
        "completed_for_date": completed_for_date,
        "completed_at_utc": completed_at,
        "source": source,
        "metadata": metadata,
    }

    if dry_run:
        return {
            "status": "would_complete",
            "reason": "Dry run validated routine completion; no row was written.",
            "dry_run": True,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "permission": permission,
            "routine": routine,
            "would_write": intended_completion,
            "completion": None,
        }

    completion = record_routine_completion(
        connection,
        routine_id=routine_id,
        completed_for_date=completed_for_date,
        completed_at_utc=completed_at,
        source=source,
        metadata=metadata,
    )
    return {
        "status": "completed",
        "reason": "Routine completion was recorded in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "permission": permission,
        "routine": routine,
        "would_write": intended_completion,
        "completion": completion,
    }


def require_routine_engine_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_routine_engine_permission(connection, category=category)
    if not decision["allowed"]:
        raise RoutineEnginePermissionDenied(decision["reason"])
    return decision


def evaluate_routine_engine_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    from personalos.state import get_permission_setting

    category = _validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=None,
            reason=f"Missing routine engine permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid routine engine permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Routine engine permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Routine engine permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Routine engine permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def routine_completion_block_reason(routine: Mapping[str, Any] | None) -> str | None:
    if routine is None:
        return "Routine does not exist."
    if routine["status"] != "active":
        return f"Routine is not active: {routine['status']}"
    if not routine["enabled"]:
        return "Routine is disabled."
    return None


def _permission_decision(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": category,
        "mode": mode,
        "reason": reason,
        "setting": setting,
    }


def _blocked_result(
    *,
    reason: str,
    dry_run: bool,
    permission: dict[str, Any],
    routine: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": dry_run,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "sent": False,
        "permission": permission,
        "routine": routine,
        "would_write": None,
        "completion": None,
    }


def _validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    metadata_dict = dict(metadata)
    json.dumps(
        metadata_dict,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return metadata_dict


def _validate_required_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_iso_date(field_name: str, value: str) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO date") from error
    return value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

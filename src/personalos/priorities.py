"""Dev/test-only priority engine foundation."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from personalos.permissions import PermissionMode
from personalos.state import (
    count_priorities,
    count_priorities_by_status,
    create_priority,
    get_priority,
    list_active_priorities,
    list_priorities,
    summarize_priorities,
    update_priority,
    update_priority_status,
    validate_priority_status,
)

PRIORITY_ENGINE_READ_PERMISSION = "priority_engine_dev_test_read"
PRIORITY_ENGINE_WRITE_PERMISSION = "priority_engine_dev_test_write"


class PriorityEnginePermissionDenied(PermissionError):
    """Raised when the priority engine permission setting does not allow the action."""


def read_priority(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
) -> dict[str, Any] | None:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    return get_priority(connection, priority_id)


def read_priorities(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    return list_priorities(connection, status=status)


def read_priority_count(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
) -> int:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    return count_priorities(connection, status=status)


def read_priority_counts_by_status(connection: sqlite3.Connection) -> dict[str, int]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    return count_priorities_by_status(connection)


def read_active_priority_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    active_priorities = list_active_priorities(connection)
    return {
        "active_count": len(active_priorities),
        "active_priorities": active_priorities,
    }


def read_priority_dashboard_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_READ_PERMISSION,
    )
    return summarize_priorities(connection)


def create_priority_record(
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
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    return create_priority(
        connection,
        priority_id=priority_id,
        title=title,
        status=status,
        metadata=metadata,
        notes=notes,
        created_at_utc=created_at_utc,
        updated_at_utc=updated_at_utc,
    )


def update_priority_record(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    title: str | None = None,
    status: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    notes: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    return update_priority(
        connection,
        priority_id=priority_id,
        title=title,
        status=status,
        metadata=metadata,
        notes=notes,
        updated_at_utc=updated_at_utc,
    )


def transition_priority_status_record(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    status: str,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    return update_priority_status(
        connection,
        priority_id=priority_id,
        status=status,
        updated_at_utc=updated_at_utc,
    )


def create_priority_flow(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    title: str,
    status: str = "active",
    metadata: Mapping[str, Any] | None = None,
    notes: str = "",
    dry_run: bool = True,
    created_at_utc: str | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    intended_priority = _validate_priority_creation(
        priority_id=priority_id,
        title=title,
        status=status,
        metadata=metadata,
        notes=notes,
        created_at_utc=created_at_utc,
        updated_at_utc=updated_at_utc,
    )

    permission = evaluate_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            dry_run=dry_run,
            permission=permission,
            priority=None,
        )

    if dry_run:
        return {
            "status": "would_create",
            "reason": "Dry run validated priority creation; no row was written.",
            "dry_run": True,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "permission": permission,
            "priority": None,
            "would_write": intended_priority,
        }

    priority = create_priority(connection, **intended_priority)
    return {
        "status": "created",
        "reason": "Priority was created in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "permission": permission,
        "priority": priority,
        "would_write": intended_priority,
    }


def update_priority_flow(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    title: str | None = None,
    status: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    notes: str | None = None,
    dry_run: bool = True,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    update_input = _validate_priority_update_input(
        priority_id=priority_id,
        title=title,
        status=status,
        metadata=metadata,
        notes=notes,
        updated_at_utc=updated_at_utc,
    )

    permission = evaluate_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            dry_run=dry_run,
            permission=permission,
            priority=None,
        )

    priority_before = get_priority(connection, update_input["priority_id"])
    if priority_before is None:
        return _blocked_result(
            reason=f"Priority does not exist: {update_input['priority_id']}",
            dry_run=dry_run,
            permission=permission,
            priority=None,
        )

    would_write = _merge_priority_update(priority_before, update_input)
    if dry_run:
        return {
            "status": "would_update",
            "reason": "Dry run validated priority update; no row was written.",
            "dry_run": True,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "permission": permission,
            "priority_before": priority_before,
            "priority_after": None,
            "would_write": would_write,
        }

    priority_after = update_priority(connection, **update_input)
    return {
        "status": "updated",
        "reason": "Priority was updated in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "permission": permission,
        "priority_before": priority_before,
        "priority_after": priority_after,
        "would_write": would_write,
    }


def transition_priority_status_flow(
    connection: sqlite3.Connection,
    *,
    priority_id: str,
    status: str,
    dry_run: bool = True,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    transition_input = _validate_priority_status_transition_input(
        priority_id=priority_id,
        status=status,
        updated_at_utc=updated_at_utc,
    )

    permission = evaluate_priority_engine_permission(
        connection,
        category=PRIORITY_ENGINE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            dry_run=dry_run,
            permission=permission,
            priority=None,
        )

    priority_before = get_priority(connection, transition_input["priority_id"])
    if priority_before is None:
        return _blocked_result(
            reason=f"Priority does not exist: {transition_input['priority_id']}",
            dry_run=dry_run,
            permission=permission,
            priority=None,
        )

    would_write = {
        **priority_before,
        "status": transition_input["status"],
        "updated_at_utc": transition_input["updated_at_utc"],
    }
    if dry_run:
        return {
            "status": "would_transition",
            "reason": "Dry run validated priority status transition; no row was written.",
            "dry_run": True,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "permission": permission,
            "priority_before": priority_before,
            "priority_after": None,
            "would_write": would_write,
        }

    priority_after = update_priority_status(connection, **transition_input)
    return {
        "status": "transitioned",
        "reason": "Priority status was updated in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "permission": permission,
        "priority_before": priority_before,
        "priority_after": priority_after,
        "would_write": would_write,
    }


def require_priority_engine_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_priority_engine_permission(connection, category=category)
    if not decision["allowed"]:
        raise PriorityEnginePermissionDenied(decision["reason"])
    return decision


def evaluate_priority_engine_permission(
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
            reason=f"Missing priority engine permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid priority engine permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Priority engine permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Priority engine permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Priority engine permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def _validate_priority_creation(
    *,
    priority_id: str,
    title: str,
    status: str,
    metadata: Mapping[str, Any] | None,
    notes: str,
    created_at_utc: str | None,
    updated_at_utc: str | None,
) -> dict[str, Any]:
    priority_id = _validate_required_text("priority_id", priority_id)
    title = _validate_required_text("title", title)
    status = validate_priority_status(status)
    metadata_dict = _validate_metadata({} if metadata is None else metadata)
    notes = _validate_text("notes", notes)
    created_at = _validate_iso_datetime("created_at_utc", created_at_utc or _utc_now())
    updated_at = _validate_iso_datetime("updated_at_utc", updated_at_utc or created_at)
    return {
        "priority_id": priority_id,
        "title": title,
        "status": status,
        "metadata": metadata_dict,
        "notes": notes,
        "created_at_utc": created_at,
        "updated_at_utc": updated_at,
    }


def _validate_priority_update_input(
    *,
    priority_id: str,
    title: str | None,
    status: str | None,
    metadata: Mapping[str, Any] | None,
    notes: str | None,
    updated_at_utc: str | None,
) -> dict[str, Any]:
    priority_id = _validate_required_text("priority_id", priority_id)
    if title is None and status is None and metadata is None and notes is None:
        raise ValueError("title, status, metadata, or notes must be provided")

    update_input: dict[str, Any] = {
        "priority_id": priority_id,
        "updated_at_utc": _validate_iso_datetime("updated_at_utc", updated_at_utc or _utc_now()),
    }
    if title is not None:
        update_input["title"] = _validate_required_text("title", title)
    if status is not None:
        update_input["status"] = validate_priority_status(status)
    if metadata is not None:
        update_input["metadata"] = _validate_metadata(metadata)
    if notes is not None:
        update_input["notes"] = _validate_text("notes", notes)
    return update_input


def _validate_priority_status_transition_input(
    *,
    priority_id: str,
    status: str,
    updated_at_utc: str | None,
) -> dict[str, Any]:
    return {
        "priority_id": _validate_required_text("priority_id", priority_id),
        "status": validate_priority_status(status),
        "updated_at_utc": _validate_iso_datetime("updated_at_utc", updated_at_utc or _utc_now()),
    }


def _merge_priority_update(
    priority_before: Mapping[str, Any],
    update_input: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "priority_id": priority_before["priority_id"],
        "title": update_input.get("title", priority_before["title"]),
        "status": update_input.get("status", priority_before["status"]),
        "metadata": update_input.get("metadata", priority_before["metadata"]),
        "notes": update_input.get("notes", priority_before["notes"]),
        "created_at_utc": priority_before["created_at_utc"],
        "updated_at_utc": update_input["updated_at_utc"],
    }


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
    priority: Mapping[str, Any] | None,
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
        "priority": priority,
        "would_write": None,
    }


def _validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a JSON-safe object")
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


def _validate_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

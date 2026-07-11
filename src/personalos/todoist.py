"""Dev/test-only Todoist module foundation."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any, Protocol

from personalos import execution_rails as rails
from personalos.permissions import evaluate_auto_write_gate
from personalos.state import (
    build_todoist_task_record,
    count_todoist_tasks,
    create_todoist_task,
    get_todoist_task,
    get_todoist_task_by_dedupe_key,
    list_todoist_tasks,
    update_todoist_task_status,
)

TODOIST_MODULE_READ_PERMISSION = "todoist_module_dev_test_read"
TODOIST_MODULE_WRITE_PERMISSION = "todoist_module_dev_test_write"
TODOIST_MODULE_SIMULATED_WRITE_PERMISSION = "todoist_module_dev_test_simulated_write"


class TodoistModulePermissionDenied(PermissionError):
    """Raised when Todoist module permission settings do not allow the action."""


class TodoistClient(Protocol):
    dev_test_fake_client: bool

    def create_task(self, task: Mapping[str, Any]) -> dict[str, Any]:
        """Create a Todoist task from a normalized task object."""


class FakeTodoistClient:
    """Recording Todoist client for tests and simulated writes only."""

    dev_test_fake_client = True

    def __init__(self) -> None:
        self.created_tasks: list[dict[str, Any]] = []

    def create_task(self, task: Mapping[str, Any]) -> dict[str, Any]:
        fake_external_id = rails.stable_fake_external_id("todoist-task", task["dedupe_key"])
        result = {
            "status": rails.ExecutionRailStatus.SIMULATED_CREATED.value,
            "external_task_id": fake_external_id,
            "dedupe_key": task["dedupe_key"],
            "warnings": [],
            "errors": [],
            "network_called": False,
            "credentials_read": False,
            "external_mutation": False,
        }
        self.created_tasks.append({"task": dict(task), "result": result})
        return result


def preview_todoist_task(**task_input: Any) -> dict[str, Any]:
    task = build_todoist_task_record(**task_input)
    return {
        "status": "would_create",
        "reason": "Preview validated Todoist task; no database row or external task was created.",
        "dry_run": True,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "sent": False,
        "adapter_called": False,
        "approval": rails.build_approval_result(task["risk_level"], task["approval_mode"]),
        "would_write": task,
        "task": None,
    }


def create_todoist_task_record(
    connection: sqlite3.Connection,
    **task_input: Any,
) -> dict[str, Any]:
    task = build_todoist_task_record(**task_input)
    permission = evaluate_todoist_module_permission(
        connection,
        category=TODOIST_MODULE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            task=None,
            would_write=task,
        )

    existing = get_todoist_task_by_dedupe_key(connection, task["dedupe_key"])
    if existing is not None:
        return {
            "status": "already_exists",
            "reason": "Todoist task dedupe_key already exists; no duplicate row was created.",
            "dry_run": False,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "duplicate": True,
            "permission": permission,
            "approval": rails.build_approval_result(
                existing["risk_level"],
                existing["approval_mode"],
            ),
            "would_write": task,
            "task": existing,
        }

    created = create_todoist_task(connection, **task)
    return {
        "status": "created",
        "reason": "Todoist task was created in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "duplicate": False,
        "permission": permission,
        "approval": rails.build_approval_result(created["risk_level"], created["approval_mode"]),
        "would_write": task,
        "task": created,
    }


def simulate_todoist_task_write(
    connection: sqlite3.Connection,
    *,
    todoist_task_id: str | None = None,
    dedupe_key: str | None = None,
    client: TodoistClient | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_todoist_module_permission(
        connection,
        category=TODOIST_MODULE_SIMULATED_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            task=None,
            would_write=None,
        )
    task = _find_task(connection, todoist_task_id=todoist_task_id, dedupe_key=dedupe_key)
    if task is None:
        return _blocked_result(
            reason="Todoist task does not exist.",
            permission=permission,
            task=None,
            would_write=None,
        )
    if task["status"] == rails.ExecutionRailStatus.SIMULATED_CREATED.value:
        return {
            "status": "already_simulated",
            "reason": "Todoist task was already marked simulated_created; no adapter was called.",
            "dry_run": False,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "adapter_called": False,
            "permission": permission,
            "task": task,
            "client_result": None,
        }

    block_reason = _simulation_block_reason(task)
    if block_reason is not None:
        return _blocked_result(
            reason=block_reason,
            permission=permission,
            task=task,
            would_write=None,
        )

    selected_client = client or FakeTodoistClient()
    _require_fake_client(selected_client)
    client_result = selected_client.create_task(task)
    updated_task = update_todoist_task_status(
        connection,
        todoist_task_id=task["todoist_task_id"],
        status=rails.ExecutionRailStatus.SIMULATED_CREATED.value,
        external_task_id=client_result["external_task_id"],
        update_external_task_id=True,
        updated_at_utc=updated_at_utc,
    )
    return {
        "status": rails.ExecutionRailStatus.SIMULATED_CREATED.value,
        "reason": "Fake Todoist client recorded a simulated task creation only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "adapter_called": True,
        "permission": permission,
        "task_before": task,
        "task_after": updated_task,
        "client_result": client_result,
    }


def read_todoist_task(
    connection: sqlite3.Connection,
    *,
    todoist_task_id: str,
) -> dict[str, Any] | None:
    require_todoist_module_permission(connection, category=TODOIST_MODULE_READ_PERMISSION)
    return get_todoist_task(connection, todoist_task_id)


def read_todoist_tasks(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    project: str | None = None,
) -> list[dict[str, Any]]:
    require_todoist_module_permission(connection, category=TODOIST_MODULE_READ_PERMISSION)
    return list_todoist_tasks(
        connection,
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        project=project,
    )


def read_todoist_task_count(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    risk_level: str | None = None,
    approval_mode: str | None = None,
    source_type: str | None = None,
    project: str | None = None,
) -> int:
    require_todoist_module_permission(connection, category=TODOIST_MODULE_READ_PERMISSION)
    return count_todoist_tasks(
        connection,
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        project=project,
    )


def update_todoist_task_status_record(
    connection: sqlite3.Connection,
    *,
    todoist_task_id: str,
    status: str,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_todoist_module_permission(connection, category=TODOIST_MODULE_WRITE_PERMISSION)
    return update_todoist_task_status(
        connection,
        todoist_task_id=todoist_task_id,
        status=status,
        updated_at_utc=updated_at_utc,
    )


def require_todoist_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_todoist_module_permission(connection, category=category)
    if not decision["allowed"]:
        raise TodoistModulePermissionDenied(decision["reason"])
    return decision


def evaluate_todoist_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = rails.validate_required_text("category", category)
    return evaluate_auto_write_gate(
        connection,
        category=category,
        missing_reason=lambda: f"Missing Todoist module permission setting: {category}",
        invalid_reason=lambda raw_mode: f"Invalid Todoist module permission mode: {raw_mode}",
        disabled_reason=lambda: f"Todoist module permission is disabled: {category}",
        not_auto_write_reason=(
            lambda _mode_value: f"Todoist module permission is not enabled for dev/test use: {category}"
        ),
        success_reason="Todoist module permission is explicitly enabled for dev/test use.",
    )


def _find_task(
    connection: sqlite3.Connection,
    *,
    todoist_task_id: str | None,
    dedupe_key: str | None,
) -> dict[str, Any] | None:
    if todoist_task_id is None and dedupe_key is None:
        raise ValueError("todoist_task_id or dedupe_key must be provided")
    if todoist_task_id is not None and dedupe_key is not None:
        raise ValueError("provide only one of todoist_task_id or dedupe_key")
    if todoist_task_id is not None:
        return get_todoist_task(connection, todoist_task_id)
    if dedupe_key is None:
        raise ValueError("dedupe_key must be provided")
    return get_todoist_task_by_dedupe_key(connection, dedupe_key)


def _simulation_block_reason(task: Mapping[str, Any]) -> str | None:
    if task["approval_mode"] == rails.ApprovalMode.MANUAL_ONLY.value:
        return "Todoist task is manual_only and must not be routed to a write client."
    if task["status"] in (
        rails.ExecutionRailStatus.CANCELLED.value,
        rails.ExecutionRailStatus.FAILED.value,
    ):
        return f"Todoist task status is not routable for simulation: {task['status']}"
    if (
        task["approval_mode"] == rails.ApprovalMode.APPROVAL_REQUIRED.value
        and task["status"] != rails.ExecutionRailStatus.APPROVED_FOR_DEV_TEST.value
    ):
        return "Todoist task requires approval before simulated write routing."
    return None


def _require_fake_client(client: TodoistClient) -> None:
    if getattr(client, "dev_test_fake_client", False) is not True:
        raise ValueError("simulated Todoist writes require a fake/recording client")


def _blocked_result(
    *,
    reason: str,
    permission: dict[str, Any],
    task: Mapping[str, Any] | None,
    would_write: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": False,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "sent": False,
        "adapter_called": False,
        "permission": permission,
        "task": dict(task) if task is not None else None,
        "would_write": dict(would_write) if would_write is not None else None,
    }

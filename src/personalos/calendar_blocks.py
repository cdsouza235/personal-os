"""Dev/test-only Calendar block module foundation."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any, Protocol

from personalos import execution_rails as rails
from personalos.permissions import evaluate_auto_write_gate
from personalos.state import (
    build_calendar_block_record,
    count_calendar_blocks,
    create_calendar_block,
    get_calendar_block,
    get_calendar_block_by_dedupe_key,
    list_calendar_blocks,
    update_calendar_block_status,
)

CALENDAR_MODULE_READ_PERMISSION = "calendar_module_dev_test_read"
CALENDAR_MODULE_WRITE_PERMISSION = "calendar_module_dev_test_write"
CALENDAR_MODULE_SIMULATED_WRITE_PERMISSION = "calendar_module_dev_test_simulated_write"


class CalendarModulePermissionDenied(PermissionError):
    """Raised when Calendar module permission settings do not allow the action."""


class CalendarClient(Protocol):
    dev_test_fake_client: bool

    def create_calendar_block(self, block: Mapping[str, Any]) -> dict[str, Any]:
        """Create a Calendar block from a normalized block object."""


class FakeCalendarClient:
    """Recording Calendar client for tests and simulated writes only."""

    dev_test_fake_client = True

    def __init__(self) -> None:
        self.created_blocks: list[dict[str, Any]] = []

    def create_calendar_block(self, block: Mapping[str, Any]) -> dict[str, Any]:
        fake_external_id = rails.stable_fake_external_id("calendar-event", block["dedupe_key"])
        result = {
            "status": rails.ExecutionRailStatus.SIMULATED_CREATED.value,
            "external_event_id": fake_external_id,
            "dedupe_key": block["dedupe_key"],
            "warnings": [],
            "errors": [],
            "network_called": False,
            "credentials_read": False,
            "external_mutation": False,
        }
        self.created_blocks.append({"block": dict(block), "result": result})
        return result


def preview_calendar_block(**block_input: Any) -> dict[str, Any]:
    block = build_calendar_block_record(**block_input)
    return {
        "status": "would_create",
        "reason": "Preview validated Calendar block; no database row or external event was created.",
        "dry_run": True,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "sent": False,
        "adapter_called": False,
        "approval": rails.build_approval_result(block["risk_level"], block["approval_mode"]),
        "would_write": block,
        "block": None,
    }


def create_calendar_block_record(
    connection: sqlite3.Connection,
    **block_input: Any,
) -> dict[str, Any]:
    block = build_calendar_block_record(**block_input)
    permission = evaluate_calendar_module_permission(
        connection,
        category=CALENDAR_MODULE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            block=None,
            would_write=block,
        )

    existing = get_calendar_block_by_dedupe_key(connection, block["dedupe_key"])
    if existing is not None:
        return {
            "status": "already_exists",
            "reason": "Calendar block dedupe_key already exists; no duplicate row was created.",
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
            "would_write": block,
            "block": existing,
        }

    created = create_calendar_block(connection, **block)
    return {
        "status": "created",
        "reason": "Calendar block was created in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "duplicate": False,
        "permission": permission,
        "approval": rails.build_approval_result(created["risk_level"], created["approval_mode"]),
        "would_write": block,
        "block": created,
    }


def simulate_calendar_block_write(
    connection: sqlite3.Connection,
    *,
    calendar_block_id: str | None = None,
    dedupe_key: str | None = None,
    client: CalendarClient | None = None,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_calendar_module_permission(
        connection,
        category=CALENDAR_MODULE_SIMULATED_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            block=None,
            would_write=None,
        )
    block = _find_block(connection, calendar_block_id=calendar_block_id, dedupe_key=dedupe_key)
    if block is None:
        return _blocked_result(
            reason="Calendar block does not exist.",
            permission=permission,
            block=None,
            would_write=None,
        )
    if block["status"] == rails.ExecutionRailStatus.SIMULATED_CREATED.value:
        return {
            "status": "already_simulated",
            "reason": "Calendar block was already marked simulated_created; no adapter was called.",
            "dry_run": False,
            "no_send": True,
            "database_write": False,
            "external_mutation": False,
            "sent": False,
            "adapter_called": False,
            "permission": permission,
            "block": block,
            "client_result": None,
        }

    block_reason = _simulation_block_reason(block)
    if block_reason is not None:
        return _blocked_result(
            reason=block_reason,
            permission=permission,
            block=block,
            would_write=None,
        )

    selected_client = client or FakeCalendarClient()
    _require_fake_client(selected_client)
    client_result = selected_client.create_calendar_block(block)
    updated_block = update_calendar_block_status(
        connection,
        calendar_block_id=block["calendar_block_id"],
        status=rails.ExecutionRailStatus.SIMULATED_CREATED.value,
        external_event_id=client_result["external_event_id"],
        update_external_event_id=True,
        updated_at_utc=updated_at_utc,
    )
    return {
        "status": rails.ExecutionRailStatus.SIMULATED_CREATED.value,
        "reason": "Fake Calendar client recorded a simulated event creation only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "sent": False,
        "adapter_called": True,
        "permission": permission,
        "block_before": block,
        "block_after": updated_block,
        "client_result": client_result,
    }


def read_calendar_block(
    connection: sqlite3.Connection,
    *,
    calendar_block_id: str,
) -> dict[str, Any] | None:
    require_calendar_module_permission(connection, category=CALENDAR_MODULE_READ_PERMISSION)
    return get_calendar_block(connection, calendar_block_id)


def read_calendar_blocks(
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
    require_calendar_module_permission(connection, category=CALENDAR_MODULE_READ_PERMISSION)
    return list_calendar_blocks(
        connection,
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
    )


def read_calendar_block_count(
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
    require_calendar_module_permission(connection, category=CALENDAR_MODULE_READ_PERMISSION)
    return count_calendar_blocks(
        connection,
        status=status,
        risk_level=risk_level,
        approval_mode=approval_mode,
        source_type=source_type,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
    )


def update_calendar_block_status_record(
    connection: sqlite3.Connection,
    *,
    calendar_block_id: str,
    status: str,
    updated_at_utc: str | None = None,
) -> dict[str, Any]:
    require_calendar_module_permission(connection, category=CALENDAR_MODULE_WRITE_PERMISSION)
    return update_calendar_block_status(
        connection,
        calendar_block_id=calendar_block_id,
        status=status,
        updated_at_utc=updated_at_utc,
    )


def require_calendar_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_calendar_module_permission(connection, category=category)
    if not decision["allowed"]:
        raise CalendarModulePermissionDenied(decision["reason"])
    return decision


def evaluate_calendar_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = rails.validate_required_text("category", category)
    return evaluate_auto_write_gate(
        connection,
        category=category,
        missing_reason=lambda: f"Missing Calendar module permission setting: {category}",
        invalid_reason=lambda raw_mode: f"Invalid Calendar module permission mode: {raw_mode}",
        disabled_reason=lambda: f"Calendar module permission is disabled: {category}",
        not_auto_write_reason=(
            lambda _mode_value: f"Calendar module permission is not enabled for dev/test use: {category}"
        ),
        success_reason="Calendar module permission is explicitly enabled for dev/test use.",
    )


def _find_block(
    connection: sqlite3.Connection,
    *,
    calendar_block_id: str | None,
    dedupe_key: str | None,
) -> dict[str, Any] | None:
    if calendar_block_id is None and dedupe_key is None:
        raise ValueError("calendar_block_id or dedupe_key must be provided")
    if calendar_block_id is not None and dedupe_key is not None:
        raise ValueError("provide only one of calendar_block_id or dedupe_key")
    if calendar_block_id is not None:
        return get_calendar_block(connection, calendar_block_id)
    if dedupe_key is None:
        raise ValueError("dedupe_key must be provided")
    return get_calendar_block_by_dedupe_key(connection, dedupe_key)


def _simulation_block_reason(block: Mapping[str, Any]) -> str | None:
    if block["approval_mode"] == rails.ApprovalMode.MANUAL_ONLY.value:
        return "Calendar block is manual_only and must not be routed to a write client."
    if block["status"] in (
        rails.ExecutionRailStatus.CANCELLED.value,
        rails.ExecutionRailStatus.FAILED.value,
    ):
        return f"Calendar block status is not routable for simulation: {block['status']}"
    if (
        block["approval_mode"] == rails.ApprovalMode.APPROVAL_REQUIRED.value
        and block["status"] != rails.ExecutionRailStatus.APPROVED_FOR_DEV_TEST.value
    ):
        return "Calendar block requires approval before simulated write routing."
    return None


def _require_fake_client(client: CalendarClient) -> None:
    if getattr(client, "dev_test_fake_client", False) is not True:
        raise ValueError("simulated Calendar writes require a fake/recording client")


def _blocked_result(
    *,
    reason: str,
    permission: dict[str, Any],
    block: Mapping[str, Any] | None,
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
        "block": dict(block) if block is not None else None,
        "would_write": dict(would_write) if would_write is not None else None,
    }

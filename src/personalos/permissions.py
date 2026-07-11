"""Default permission model for future Personal OS execution modules."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PermissionMode(StrEnum):
    AUTO_WRITE = "auto_write"
    APPROVAL_REQUIRED = "approval_required"
    DISABLED = "disabled"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionCategory(StrEnum):
    ROUTINE_TODOIST_TASKS = "routine_todoist_tasks"
    SELF_CALENDAR_BLOCKS = "self_calendar_blocks"
    HIGH_VALUE_REVIEW_TASKS = "high_value_review_tasks"
    HIGH_VALUE_EXECUTION_ACTIONS = "high_value_execution_actions"
    MESSAGES_TO_OTHER_PEOPLE = "messages_to_other_people"
    EXTERNAL_CALENDAR_EVENTS = "external_calendar_events"


class PermissionDecision(StrEnum):
    ALLOW_AUTOMATIC = "allow_automatic"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


DEFAULT_PERMISSIONS: dict[ActionCategory, PermissionMode] = {
    ActionCategory.ROUTINE_TODOIST_TASKS: PermissionMode.AUTO_WRITE,
    ActionCategory.SELF_CALENDAR_BLOCKS: PermissionMode.AUTO_WRITE,
    ActionCategory.HIGH_VALUE_REVIEW_TASKS: PermissionMode.AUTO_WRITE,
    ActionCategory.HIGH_VALUE_EXECUTION_ACTIONS: PermissionMode.APPROVAL_REQUIRED,
    ActionCategory.MESSAGES_TO_OTHER_PEOPLE: PermissionMode.APPROVAL_REQUIRED,
    ActionCategory.EXTERNAL_CALENDAR_EVENTS: PermissionMode.APPROVAL_REQUIRED,
}


@dataclass(frozen=True)
class ProposedAction:
    category: ActionCategory | str
    risk_level: RiskLevel | str


def evaluate_permission(
    action: ProposedAction,
    permissions: dict[ActionCategory, PermissionMode] | None = None,
) -> PermissionDecision:
    selected_permissions = DEFAULT_PERMISSIONS if permissions is None else permissions
    risk_level = _normalize_risk_level(action.risk_level)
    category = _normalize_action_category(action.category)

    if risk_level is None:
        return PermissionDecision.REQUIRES_APPROVAL
    if category is None:
        return PermissionDecision.REQUIRES_APPROVAL

    mode = selected_permissions.get(category, PermissionMode.APPROVAL_REQUIRED)
    if mode is PermissionMode.DISABLED:
        return PermissionDecision.BLOCKED
    if mode is PermissionMode.APPROVAL_REQUIRED:
        return PermissionDecision.REQUIRES_APPROVAL
    if risk_level is not RiskLevel.LOW:
        return PermissionDecision.REQUIRES_APPROVAL
    if mode is PermissionMode.AUTO_WRITE:
        return PermissionDecision.ALLOW_AUTOMATIC

    return PermissionDecision.REQUIRES_APPROVAL


def _normalize_action_category(category: ActionCategory | str) -> ActionCategory | None:
    if isinstance(category, ActionCategory):
        return category
    try:
        return ActionCategory(category)
    except ValueError:
        return None


def _normalize_risk_level(risk_level: RiskLevel | str) -> RiskLevel | None:
    if isinstance(risk_level, RiskLevel):
        return risk_level
    try:
        return RiskLevel(risk_level)
    except ValueError:
        return None


def evaluate_auto_write_gate(
    connection: sqlite3.Connection,
    *,
    category: str,
    missing_reason: Callable[[], str],
    invalid_reason: Callable[[str], str],
    not_auto_write_reason: Callable[[str], str],
    success_reason: str,
    disabled_reason: Callable[[], str] | None = None,
    include_category: bool = True,
    include_mode: bool = True,
    include_setting: bool = True,
) -> dict[str, Any]:
    """Shared control flow for the mode-only "auto_write hard gate" pattern.

    This is the branching logic that was copy-pasted (as a private
    `_permission_decision` helper plus surrounding if/else) across every
    `evaluate_*_permission` site in the codebase. It reads the stored
    permission setting via `state.get_permission_setting` (the already-shared
    DB read -- untouched here) and decides `allowed` based on the parsed
    `PermissionMode`. The exact reason text for each branch, and whether a
    separate `disabled` branch exists and which result keys are included, are
    left to the caller so every site's exact current wording and dict shape
    is reproducible through this one function.

    This is a distinct decision path from `evaluate_permission`/
    `ProposedAction`/`PermissionDecision` above, which is a risk-level-aware
    preview/dry-run evaluator used only by `validation.py`. This function
    backs the simpler mode-only hard gates used by module dev/test
    permission checks and live-write rail gates.
    """
    from personalos.state import get_permission_setting

    setting = get_permission_setting(connection, category)
    if setting is None:
        return _auto_write_gate_result(
            allowed=False,
            category=category,
            mode=None,
            reason=missing_reason(),
            setting=None,
            include_category=include_category,
            include_mode=include_mode,
            include_setting=include_setting,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _auto_write_gate_result(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=invalid_reason(setting["mode"]),
            setting=setting,
            include_category=include_category,
            include_mode=include_mode,
            include_setting=include_setting,
        )

    if disabled_reason is not None and mode is PermissionMode.DISABLED:
        return _auto_write_gate_result(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=disabled_reason(),
            setting=setting,
            include_category=include_category,
            include_mode=include_mode,
            include_setting=include_setting,
        )

    if mode is not PermissionMode.AUTO_WRITE:
        return _auto_write_gate_result(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=not_auto_write_reason(mode.value),
            setting=setting,
            include_category=include_category,
            include_mode=include_mode,
            include_setting=include_setting,
        )

    return _auto_write_gate_result(
        allowed=True,
        category=category,
        mode=mode.value,
        reason=success_reason,
        setting=setting,
        include_category=include_category,
        include_mode=include_mode,
        include_setting=include_setting,
    )


def _auto_write_gate_result(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: dict[str, Any] | None,
    include_category: bool,
    include_mode: bool,
    include_setting: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {"allowed": allowed}
    if include_category:
        result["category"] = category
    if include_mode:
        result["mode"] = mode
    result["reason"] = reason
    if include_setting:
        result["setting"] = setting
    return result

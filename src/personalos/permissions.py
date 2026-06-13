"""Default permission model for future Personal OS execution modules."""

from dataclasses import dataclass
from enum import StrEnum


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

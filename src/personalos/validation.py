"""Dry-run/no-send validation for future execution modules."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from personalos.events import EventType, create_system_event, record_system_event
from personalos.permissions import (
    ActionCategory,
    PermissionDecision,
    PermissionMode,
    ProposedAction,
    RiskLevel,
    evaluate_permission,
)


class ValidationStatus(StrEnum):
    ALLOWED_DRY_RUN = "allowed_dry_run"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ProposedExecutionAction:
    category: ActionCategory | str
    risk_level: RiskLevel | str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    action: ProposedExecutionAction
    status: ValidationStatus
    permission_decision: PermissionDecision
    executed: bool
    sent: bool
    reason: str


def validate_no_send(
    actions: ProposedExecutionAction | list[ProposedExecutionAction],
    *,
    permissions: dict[ActionCategory, PermissionMode] | None = None,
    event_connection: Any | None = None,
) -> list[ValidationResult]:
    action_list = actions if isinstance(actions, list) else [actions]
    results = [
        _validate_one(action, permissions=permissions, event_connection=event_connection)
        for action in action_list
    ]
    return results


def _validate_one(
    action: ProposedExecutionAction,
    *,
    permissions: dict[ActionCategory, PermissionMode] | None,
    event_connection: Any | None,
) -> ValidationResult:
    permission_decision = evaluate_permission(
        ProposedAction(category=action.category, risk_level=action.risk_level),
        permissions=permissions,
    )
    status = _status_for(permission_decision)
    result = ValidationResult(
        action=action,
        status=status,
        permission_decision=permission_decision,
        executed=False,
        sent=False,
        reason=_reason_for(status),
    )

    if event_connection is not None and status is not ValidationStatus.ALLOWED_DRY_RUN:
        event_type = (
            EventType.SAFETY_BLOCK if status is ValidationStatus.BLOCKED else EventType.WARNING
        )
        record_system_event(
            event_connection,
            create_system_event(
                source="personalos.validation",
                event_type=event_type,
                message=result.reason,
                metadata={
                    "category": str(action.category),
                    "risk_level": str(action.risk_level),
                    "status": status.value,
                },
            ),
        )

    return result


def _status_for(permission_decision: PermissionDecision) -> ValidationStatus:
    if permission_decision is PermissionDecision.ALLOW_AUTOMATIC:
        return ValidationStatus.ALLOWED_DRY_RUN
    if permission_decision is PermissionDecision.BLOCKED:
        return ValidationStatus.BLOCKED
    return ValidationStatus.REQUIRES_APPROVAL


def _reason_for(status: ValidationStatus) -> str:
    if status is ValidationStatus.ALLOWED_DRY_RUN:
        return "Action is allowed for dry-run validation only; no send or execution occurred."
    if status is ValidationStatus.BLOCKED:
        return "Action is blocked by permissions; no send or execution occurred."
    return "Action requires approval; no send or execution occurred."

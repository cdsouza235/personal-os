import unittest

from personalos.permissions import (
    DEFAULT_PERMISSIONS,
    ActionCategory,
    PermissionDecision,
    PermissionMode,
    ProposedAction,
    RiskLevel,
    evaluate_permission,
)


class PermissionDefaultsTest(unittest.TestCase):
    def test_default_permission_values_match_docs(self) -> None:
        self.assertEqual(
            DEFAULT_PERMISSIONS,
            {
                ActionCategory.ROUTINE_TODOIST_TASKS: PermissionMode.AUTO_WRITE,
                ActionCategory.SELF_CALENDAR_BLOCKS: PermissionMode.AUTO_WRITE,
                ActionCategory.HIGH_VALUE_REVIEW_TASKS: PermissionMode.AUTO_WRITE,
                ActionCategory.HIGH_VALUE_EXECUTION_ACTIONS: PermissionMode.APPROVAL_REQUIRED,
                ActionCategory.MESSAGES_TO_OTHER_PEOPLE: PermissionMode.APPROVAL_REQUIRED,
                ActionCategory.EXTERNAL_CALENDAR_EVENTS: PermissionMode.APPROVAL_REQUIRED,
            },
        )

    def test_low_risk_routine_todoist_tasks_are_auto_write(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
            )
        )

        self.assertEqual(decision, PermissionDecision.ALLOW_AUTOMATIC)

    def test_self_only_calendar_blocks_are_auto_write(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.SELF_CALENDAR_BLOCKS,
                risk_level=RiskLevel.LOW,
            )
        )

        self.assertEqual(decision, PermissionDecision.ALLOW_AUTOMATIC)

    def test_high_value_execution_actions_require_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.HIGH_VALUE_EXECUTION_ACTIONS,
                risk_level=RiskLevel.MEDIUM,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_messages_to_other_people_require_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.MESSAGES_TO_OTHER_PEOPLE,
                risk_level=RiskLevel.MEDIUM,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_external_calendar_events_require_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.EXTERNAL_CALENDAR_EVENTS,
                risk_level=RiskLevel.MEDIUM,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_unknown_action_categories_do_not_auto_write_by_default(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category="unknown_future_action",
                risk_level=RiskLevel.LOW,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_empty_permissions_do_not_fall_back_to_defaults(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
            ),
            permissions={},
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_unknown_risk_level_requires_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level="unknown_future_risk",
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_medium_risk_auto_write_category_requires_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.MEDIUM,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_high_risk_items_do_not_bypass_approval(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.HIGH,
            )
        )

        self.assertEqual(decision, PermissionDecision.REQUIRES_APPROVAL)

    def test_disabled_permission_blocks_action(self) -> None:
        decision = evaluate_permission(
            ProposedAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
            ),
            permissions={
                **DEFAULT_PERMISSIONS,
                ActionCategory.ROUTINE_TODOIST_TASKS: PermissionMode.DISABLED,
            },
        )

        self.assertEqual(decision, PermissionDecision.BLOCKED)

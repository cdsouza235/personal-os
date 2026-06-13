import json
import unittest
from datetime import UTC, datetime

from personalos.completion import (
    CompletionMode,
    CompletionStatus,
    completion_report_from_validation_results,
    create_completion_report,
)
from personalos.permissions import ActionCategory, PermissionMode, RiskLevel
from personalos.validation import ProposedExecutionAction, validate_no_send


class CompletionReportTest(unittest.TestCase):
    def test_report_ids_are_unique(self) -> None:
        first_report = create_completion_report(
            status=CompletionStatus.SUCCESS,
            mode=CompletionMode.DRY_RUN,
            dry_run=True,
            no_send=True,
        )
        second_report = create_completion_report(
            status=CompletionStatus.SUCCESS,
            mode=CompletionMode.DRY_RUN,
            dry_run=True,
            no_send=True,
        )

        self.assertNotEqual(first_report.report_id, second_report.report_id)

    def test_timestamps_are_utc_iso_formatted(self) -> None:
        report = create_completion_report(
            status=CompletionStatus.SUCCESS,
            mode=CompletionMode.TEST,
            dry_run=True,
            no_send=True,
        )

        started_at = datetime.fromisoformat(report.started_at_utc)
        finished_at = datetime.fromisoformat(report.finished_at_utc)

        self.assertEqual(started_at.tzinfo, UTC)
        self.assertEqual(finished_at.tzinfo, UTC)
        self.assertTrue(report.started_at_utc.endswith("+00:00"))
        self.assertTrue(report.finished_at_utc.endswith("+00:00"))

    def test_report_serializes_to_json_safe_dict_and_string(self) -> None:
        report = create_completion_report(
            status=CompletionStatus.WARNING,
            mode=CompletionMode.DRY_RUN,
            dry_run=True,
            no_send=True,
            actions_considered=1,
            actions_allowed_dry_run=1,
            safety_flags=["dev_test_only"],
            warnings=["preview only"],
            metadata={"module": "tests"},
        )

        report_dict = report.to_dict()
        report_json = report.to_json()

        self.assertEqual(report_dict["status"], "warning")
        self.assertEqual(report_dict["mode"], "dry_run")
        self.assertEqual(json.loads(report_json), report_dict)

    def test_dry_run_and_no_send_fields_remain_explicit(self) -> None:
        report = create_completion_report(
            status=CompletionStatus.SUCCESS,
            mode=CompletionMode.DEVELOPMENT,
            dry_run=True,
            no_send=True,
        )

        self.assertTrue(report.dry_run)
        self.assertTrue(report.no_send)
        self.assertTrue(report.to_dict()["dry_run"])
        self.assertTrue(report.to_dict()["no_send"])

    def test_action_counts_can_be_populated_from_validation_results(self) -> None:
        validation_results = validate_no_send(
            [
                ProposedExecutionAction(
                    category=ActionCategory.ROUTINE_TODOIST_TASKS,
                    risk_level=RiskLevel.LOW,
                    summary="Routine task preview",
                ),
                ProposedExecutionAction(
                    category=ActionCategory.MESSAGES_TO_OTHER_PEOPLE,
                    risk_level=RiskLevel.MEDIUM,
                    summary="Message preview",
                ),
                ProposedExecutionAction(
                    category=ActionCategory.EXTERNAL_CALENDAR_EVENTS,
                    risk_level=RiskLevel.LOW,
                    summary="Blocked task preview",
                ),
            ],
            permissions={
                ActionCategory.ROUTINE_TODOIST_TASKS: PermissionMode.AUTO_WRITE,
                ActionCategory.MESSAGES_TO_OTHER_PEOPLE: PermissionMode.APPROVAL_REQUIRED,
                ActionCategory.EXTERNAL_CALENDAR_EVENTS: PermissionMode.DISABLED,
            },
        )

        report = completion_report_from_validation_results(validation_results)

        self.assertEqual(report.actions_considered, 3)
        self.assertEqual(report.actions_allowed_dry_run, 1)
        self.assertEqual(report.actions_requiring_approval, 1)
        self.assertEqual(report.actions_blocked, 1)

    def test_report_never_marks_actions_as_sent_or_executed(self) -> None:
        report = create_completion_report(
            status=CompletionStatus.BLOCKED,
            mode=CompletionMode.DRY_RUN,
            dry_run=True,
            no_send=True,
            errors=["blocked by safety policy"],
        )

        self.assertFalse(report.executed)
        self.assertFalse(report.sent)
        self.assertFalse(report.to_dict()["executed"])
        self.assertFalse(report.to_dict()["sent"])

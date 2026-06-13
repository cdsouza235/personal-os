import tempfile
import unittest
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import ActionCategory, PermissionMode, RiskLevel
from personalos.validation import ProposedExecutionAction, ValidationStatus, validate_no_send


class ValidationHarnessTest(unittest.TestCase):
    def test_low_risk_routine_todoist_task_validates_as_allowed_dry_run(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
                summary="Create routine task preview",
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.ALLOWED_DRY_RUN)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_high_value_execution_action_requires_approval(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.HIGH_VALUE_EXECUTION_ACTIONS,
                risk_level=RiskLevel.MEDIUM,
                summary="High-value execution preview",
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.REQUIRES_APPROVAL)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_message_to_another_person_requires_approval(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.MESSAGES_TO_OTHER_PEOPLE,
                risk_level=RiskLevel.MEDIUM,
                summary="Message preview",
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.REQUIRES_APPROVAL)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_external_calendar_event_requires_approval(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.EXTERNAL_CALENDAR_EVENTS,
                risk_level=RiskLevel.MEDIUM,
                summary="External calendar event preview",
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.REQUIRES_APPROVAL)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_disabled_category_blocks(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
                summary="Disabled routine task preview",
            ),
            permissions={ActionCategory.ROUTINE_TODOIST_TASKS: PermissionMode.DISABLED},
        )[0]

        self.assertEqual(result.status, ValidationStatus.BLOCKED)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_unknown_category_requires_approval(self) -> None:
        result = validate_no_send(
            ProposedExecutionAction(
                category="unknown_future_action",
                risk_level=RiskLevel.LOW,
                summary="Unknown action preview",
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.REQUIRES_APPROVAL)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_validation_does_not_call_external_services(self) -> None:
        class ExternalServiceProbe:
            called = False

            def send(self) -> None:
                self.called = True

        probe = ExternalServiceProbe()

        result = validate_no_send(
            ProposedExecutionAction(
                category=ActionCategory.ROUTINE_TODOIST_TASKS,
                risk_level=RiskLevel.LOW,
                summary="No external call preview",
                metadata={"probe": "not-called"},
            )
        )[0]

        self.assertEqual(result.status, ValidationStatus.ALLOWED_DRY_RUN)
        self.assertFalse(probe.called)
        self.assertFalse(result.executed)
        self.assertFalse(result.sent)

    def test_validation_can_record_approval_event_with_injected_temp_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                result = validate_no_send(
                    ProposedExecutionAction(
                        category=ActionCategory.MESSAGES_TO_OTHER_PEOPLE,
                        risk_level=RiskLevel.MEDIUM,
                        summary="Message preview",
                    ),
                    event_connection=connection,
                )[0]
                row = connection.execute(
                    "SELECT event_type, source FROM system_events"
                ).fetchone()

            self.assertEqual(result.status, ValidationStatus.REQUIRES_APPROVAL)
            self.assertEqual(row["event_type"], "warning")
            self.assertEqual(row["source"], "personalos.validation")
            self.assertFalse(result.executed)
            self.assertFalse(result.sent)


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )

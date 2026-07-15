import os
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from personalos import status
from personalos.briefings import (
    BRIEFING_LOOP_RUN_PERMISSION,
    BRIEFING_LOOP_WRITE_PERMISSION,
    build_no_send_candidate_output,
)
from personalos.composer import (
    COMPOSER_MODULE_RUN_PERMISSION,
    COMPOSER_MODULE_WRITE_PERMISSION,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.rail_dispatch import (
    OUTCOME_DISPATCHED,
    OUTCOME_FAILED,
    OUTCOME_PREVIEW,
    dispatch_morning_candidates,
)
from personalos.rails import gmail as gmail_rail
from personalos.rails import todoist as todoist_rail
from personalos.rails.gmail import (
    GMAIL_RAIL_APP_PASSWORD_ENV_VAR,
    GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR,
    GMAIL_RAIL_LIVE_SEND_PERMISSION,
    GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR,
)
from personalos.rails.todoist import (
    TODOIST_RAIL_CREDENTIAL_ENV_VAR,
    TODOIST_RAIL_LIVE_WRITE_PERMISSION,
)
from personalos.state import create_routine, upsert_permission_setting

SOURCE_DATE = "2026-06-20"
BRIEFING_WINDOW = "morning"
FAKE_TODOIST_TOKEN = "fake-test-todoist-token"  # noqa: S105 - test fixture only
FAKE_GMAIL_SENDER = "fake.sender@example.com"
FAKE_GMAIL_APP_PASSWORD = "fake-test-app-password"  # noqa: S105 - test fixture only
FAKE_GMAIL_RECIPIENT = "fake.controlled.recipient@example.com"


class RailDispatchAllInertBaselineTest(unittest.TestCase):
    def test_all_candidates_preview_and_no_rail_function_is_ever_called(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)
            self.assertEqual(status.RAIL_STATES["todoist"], "inert")
            self.assertEqual(status.RAIL_STATES["gmail"], "inert")

            with mock.patch(
                "personalos.rail_dispatch.todoist_rail.create_live_todoist_task"
            ) as todoist_call, mock.patch(
                "personalos.rail_dispatch.gmail_rail.send_live_gmail_message"
            ) as gmail_call:
                result = dispatch_morning_candidates(
                    connection,
                    source_date=SOURCE_DATE,
                    timezone=DEFAULT_TIMEZONE,
                    briefing_window_name=BRIEFING_WINDOW,
                    run_at=f"{SOURCE_DATE}T09:00:00+00:00",
                )

                todoist_call.assert_not_called()
                gmail_call.assert_not_called()

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["live_write"])
        self.assertTrue(result["candidates"])
        outcomes = {candidate["outcome"] for candidate in result["candidates"]}
        self.assertEqual(outcomes, {OUTCOME_PREVIEW})
        self.assertIn("Todoist: 0 dispatched", result["report_text"])


class RailDispatchTodoistLiveTest(unittest.TestCase):
    def test_live_todoist_rail_is_actually_called_with_candidate_fields(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)
            _set_permission(connection, TODOIST_RAIL_LIVE_WRITE_PERMISSION)

            recorded: list[dict] = []

            class _RecordingTodoistClient:
                def __init__(self, *, token: str) -> None:
                    self.token = token

                def create_task(self, payload):
                    recorded.append(dict(payload))
                    return {
                        "status": todoist_rail.STATUS_CLIENT_CALL_PASSED,
                        "external_task_id": "ext-task-1",
                        "network_called": True,
                        "external_mutation": True,
                    }

            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict(
                    os.environ, {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TODOIST_TOKEN}
                ):
                    with mock.patch(
                        "personalos.rails.todoist.TodoistRailClient",
                        _RecordingTodoistClient,
                    ):
                        result = dispatch_morning_candidates(
                            connection,
                            source_date=SOURCE_DATE,
                            timezone=DEFAULT_TIMEZONE,
                            briefing_window_name=BRIEFING_WINDOW,
                            run_at=f"{SOURCE_DATE}T09:00:00+00:00",
                        )

        todoist_entries = [c for c in result["candidates"] if c["rail"] == "todoist"]
        self.assertEqual(len(todoist_entries), 1)
        self.assertEqual(todoist_entries[0]["outcome"], OUTCOME_DISPATCHED)
        self.assertEqual(todoist_entries[0]["external_id"], "ext-task-1")
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["content"], "Complete: Due today routine")
        self.assertTrue(result["live_write"])

        # Gmail rail stayed inert -- its candidate must still be a preview.
        gmail_entries = [c for c in result["candidates"] if c["rail"] == "gmail"]
        self.assertEqual(gmail_entries[0]["outcome"], OUTCOME_PREVIEW)


class RailDispatchGmailLiveTest(unittest.TestCase):
    def test_live_gmail_rail_is_actually_called_with_controlled_recipient(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)
            _set_permission(connection, GMAIL_RAIL_LIVE_SEND_PERMISSION)

            recorded: list[dict] = []

            class _RecordingGmailClient:
                def __init__(self, *, app_password: str) -> None:
                    self.app_password = app_password

                def send_message(self, *, sender, to_address, subject, body):
                    recorded.append(
                        {
                            "sender": sender,
                            "to_address": to_address,
                            "subject": subject,
                            "body": body,
                        }
                    )
                    return {
                        "status": gmail_rail.STATUS_CLIENT_CALL_PASSED,
                        "network_called": True,
                        "external_mutation": True,
                    }

            env = {
                GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_GMAIL_SENDER,
                GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_GMAIL_APP_PASSWORD,
                GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR: FAKE_GMAIL_RECIPIENT,
            }
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(os.environ, env):
                    with mock.patch(
                        "personalos.rails.gmail.GmailSmtpClient",
                        _RecordingGmailClient,
                    ):
                        result = dispatch_morning_candidates(
                            connection,
                            source_date=SOURCE_DATE,
                            timezone=DEFAULT_TIMEZONE,
                            briefing_window_name=BRIEFING_WINDOW,
                            run_at=f"{SOURCE_DATE}T09:00:00+00:00",
                        )

        gmail_entries = [c for c in result["candidates"] if c["rail"] == "gmail"]
        self.assertEqual(len(gmail_entries), 1)
        self.assertEqual(gmail_entries[0]["outcome"], OUTCOME_DISPATCHED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["to_address"], FAKE_GMAIL_RECIPIENT)
        self.assertTrue(result["live_write"])

        # Todoist rail stayed inert -- its candidate must still be a preview.
        todoist_entries = [c for c in result["candidates"] if c["rail"] == "todoist"]
        self.assertEqual(todoist_entries[0]["outcome"], OUTCOME_PREVIEW)

    def test_unresolved_controlled_recipient_previews_and_never_calls_the_rail(self) -> None:
        # Gmail rail is live and credentials/permission are all satisfied, but the
        # controlled-recipient env var is unset -> to_address on the candidate is
        # empty. The dispatcher must never guess a recipient: preview, don't call.
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)
            _set_permission(connection, GMAIL_RAIL_LIVE_SEND_PERMISSION)

            env = {
                GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_GMAIL_SENDER,
                GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_GMAIL_APP_PASSWORD,
            }
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(os.environ, env):
                    os.environ.pop(GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR, None)
                    with mock.patch(
                        "personalos.rail_dispatch.gmail_rail.send_live_gmail_message"
                    ) as gmail_call:
                        result = dispatch_morning_candidates(
                            connection,
                            source_date=SOURCE_DATE,
                            timezone=DEFAULT_TIMEZONE,
                            briefing_window_name=BRIEFING_WINDOW,
                            run_at=f"{SOURCE_DATE}T09:00:00+00:00",
                        )
                        gmail_call.assert_not_called()

        gmail_entries = [c for c in result["candidates"] if c["rail"] == "gmail"]
        self.assertEqual(gmail_entries[0]["outcome"], OUTCOME_PREVIEW)


class RailDispatchPartialFailureTest(unittest.TestCase):
    def test_todoist_succeeds_gmail_fails_report_shows_both_and_no_retry(self) -> None:
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)
            _set_permission(connection, TODOIST_RAIL_LIVE_WRITE_PERMISSION)
            _set_permission(connection, GMAIL_RAIL_LIVE_SEND_PERMISSION)

            class _PassingTodoistClient:
                def __init__(self, *, token: str) -> None:
                    pass

                def create_task(self, payload):
                    return {
                        "status": todoist_rail.STATUS_CLIENT_CALL_PASSED,
                        "external_task_id": "ext-task-2",
                        "network_called": True,
                        "external_mutation": True,
                    }

            gmail_calls: list[dict] = []

            class _FailingGmailClient:
                def __init__(self, *, app_password: str) -> None:
                    pass

                def send_message(self, *, sender, to_address, subject, body):
                    gmail_calls.append(
                        {"sender": sender, "to_address": to_address, "subject": subject}
                    )
                    return {
                        "status": gmail_rail.STATUS_CLIENT_CALL_FAILED,
                        "network_called": True,
                        "external_mutation": "unconfirmed",
                        "error_type": "SimulatedFailure",
                        "error_message": "simulated transport failure",
                    }

            env = {
                TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TODOIST_TOKEN,
                GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_GMAIL_SENDER,
                GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_GMAIL_APP_PASSWORD,
                GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR: FAKE_GMAIL_RECIPIENT,
            }
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live", "gmail": "live"}):
                with mock.patch.dict(os.environ, env):
                    with mock.patch(
                        "personalos.rails.todoist.TodoistRailClient",
                        _PassingTodoistClient,
                    ), mock.patch(
                        "personalos.rails.gmail.GmailSmtpClient",
                        _FailingGmailClient,
                    ):
                        result = dispatch_morning_candidates(
                            connection,
                            source_date=SOURCE_DATE,
                            timezone=DEFAULT_TIMEZONE,
                            briefing_window_name=BRIEFING_WINDOW,
                            run_at=f"{SOURCE_DATE}T09:00:00+00:00",
                        )

        todoist_entries = [c for c in result["candidates"] if c["rail"] == "todoist"]
        gmail_entries = [c for c in result["candidates"] if c["rail"] == "gmail"]
        self.assertEqual(todoist_entries[0]["outcome"], OUTCOME_DISPATCHED)
        self.assertEqual(gmail_entries[0]["outcome"], OUTCOME_FAILED)
        self.assertEqual(len(gmail_calls), 1)  # attempted exactly once -- no retry
        self.assertIn("Todoist: 1 dispatched.", result["report_text"])
        self.assertIn("Gmail: FAILED (not retried).", result["report_text"])
        self.assertTrue(result["warnings"])


class RailDispatchIdempotencyFixTest(unittest.TestCase):
    def test_dedupe_key_and_source_id_are_day_stable_across_two_runs(self) -> None:
        # This is the actual D-PO-017 item 3 bug: before the fix, dedupe_key/source_id
        # were derived from the per-run packet_id (which embeds wall-clock started_at),
        # so two invocations for the SAME day minted DIFFERENT keys and the rail-level
        # idempotency gate could never catch a re-run. Building the candidate output
        # twice with two different run_at timestamps and asserting the keys match
        # proves the fix; asserting a key merely "exists" would not.
        with _migrated_test_connection() as connection:
            _seed_dispatchable_state(connection)

            early = build_no_send_candidate_output(
                connection,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
                briefing_window_name=BRIEFING_WINDOW,
                run_at=f"{SOURCE_DATE}T08:00:00+00:00",
            )
            later = build_no_send_candidate_output(
                connection,
                source_date=SOURCE_DATE,
                timezone=DEFAULT_TIMEZONE,
                briefing_window_name=BRIEFING_WINDOW,
                run_at=f"{SOURCE_DATE}T18:00:00+00:00",
            )

        self.assertNotEqual(early["packet_id"], later["packet_id"])

        early_output = early["composer_result"]["output"]["output_json"]
        later_output = later["composer_result"]["output"]["output_json"]

        early_task = early_output["todoist_tasks"][0]
        later_task = later_output["todoist_tasks"][0]
        self.assertEqual(early_task["dedupe_key"], later_task["dedupe_key"])
        self.assertEqual(early_task["source_id"], later_task["source_id"])
        self.assertNotIn(early["packet_id"], early_task["dedupe_key"])
        self.assertNotIn(early["packet_id"], early_task["source_id"])

        early_brief = early_output["email_briefs"][0]
        later_brief = later_output["email_briefs"][0]
        self.assertEqual(early_brief["dedupe_key"], later_brief["dedupe_key"])
        self.assertEqual(early_brief["source_id"], later_brief["source_id"])
        self.assertNotIn(early["packet_id"], early_brief["dedupe_key"])
        self.assertNotIn(early["packet_id"], early_brief["source_id"])


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        try:
            yield connection
        finally:
            connection.close()


def _seed_dispatchable_state(connection: sqlite3.Connection) -> None:
    _seed_briefing_window(connection)
    _set_permission(connection, BRIEFING_LOOP_WRITE_PERMISSION)
    _set_permission(connection, BRIEFING_LOOP_RUN_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
    _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)
    create_routine(
        connection,
        routine_id="routine-due-today",
        name="Due today routine",
        status="active",
        enabled=True,
        cadence_type="daily",
        created_at_utc=f"{SOURCE_DATE}T00:00:00+00:00",
        updated_at_utc=f"{SOURCE_DATE}T00:00:00+00:00",
    )


def _seed_briefing_window(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO briefing_windows (
                id, name, scheduled_time, timezone, delivery_mode, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "briefing-window-morning",
                BRIEFING_WINDOW,
                "08:00",
                DEFAULT_TIMEZONE,
                "no_send",
                "active",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"packet": "P-RAIL-DISPATCH-01"},
        updated_by="tests",
        updated_at_utc="2026-07-15T10:00:00+00:00",
    )


if __name__ == "__main__":
    unittest.main()

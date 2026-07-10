import json
import os
import smtplib
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from personalos import status
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.idempotency import generate_idempotency_key
from personalos.permissions import PermissionMode
from personalos.rails.gmail import (
    GMAIL_RAIL_APP_PASSWORD_ENV_VAR,
    GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR,
    GMAIL_RAIL_LIVE_SEND_PERMISSION,
    GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR,
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_DUPLICATE,
    STATUS_BLOCKED_PERMISSION,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED,
    STATUS_CLIENT_CALL_PASSED,
    GmailRailPermissionDenied,
    GmailSmtpClient,
    evaluate_gmail_rail_live_send_permission,
    require_gmail_rail_live_send_permission,
    send_live_gmail_message,
)
from personalos.state import upsert_permission_setting

FAKE_SENDER_ADDRESS = "fake.sender@example.com"
FAKE_APP_PASSWORD = "fake-test-app-password-never-real"  # noqa: S105 - test fixture, not a real credential
FAKE_CONTROLLED_RECIPIENT = "fake.controlled.recipient@example.com"

_FAKE_CREDENTIAL_ENV = {
    GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_SENDER_ADDRESS,
    GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_APP_PASSWORD,
    GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR: FAKE_CONTROLLED_RECIPIENT,
}


class _RecordingFakeClient:
    """Bypass client (no smtplib at all) used by the gate-isolation tests."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_message(self, *, sender, to_address, subject, body):
        self.calls.append(
            {"sender": sender, "to_address": to_address, "subject": subject, "body": body}
        )
        return {
            "status": STATUS_CLIENT_CALL_PASSED,
            "network_called": True,
            "external_mutation": True,
        }


class _RecordingFakeSmtp:
    """Fake smtplib.SMTP_SSL-shaped context manager that records login/send calls."""

    def __init__(self, *, raise_on_login: bool = False) -> None:
        self.login_calls: list[tuple[str, str]] = []
        self.sent_messages: list[object] = []
        self._raise_on_login = raise_on_login

    def __call__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def login(self, sender, app_password):
        if self._raise_on_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")
        self.login_calls.append((sender, app_password))

    def send_message(self, message):
        self.sent_messages.append(message)
        return {}


class _FailingSmtpFactory:
    def __call__(self, host, port, timeout=None):
        raise OSError("simulated network failure")


class GmailRailGateTest(unittest.TestCase):
    def test_gate1_permission_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            client = _RecordingFakeClient()
            result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(result["gate_failed"], "permission")
            self.assertFalse(result["permission"]["allowed"])
            self.assertFalse(result["external_mutation"])
            self.assertFalse(result["safety_assertions"]["network_called"])
            self.assertEqual(client.calls, [])

    def test_gate1_permission_approval_required_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, mode=PermissionMode.APPROVAL_REQUIRED)
            client = _RecordingFakeClient()
            result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(result["gate_failed"], "permission")
            self.assertEqual(client.calls, [])

    def test_gate1_todoist_live_write_permission_does_not_satisfy_gmail_gate(self) -> None:
        # Gmail's live-send permission is a structurally distinct category from
        # Todoist's live-write permission; enabling one must never satisfy the other.
        with _migrated_test_connection() as connection:
            upsert_permission_setting(
                connection,
                category="todoist_rail_live_write",
                mode=PermissionMode.AUTO_WRITE.value,
                metadata={},
                updated_by="tests",
                updated_at_utc="2026-07-10T10:00:00+00:00",
            )
            client = _RecordingFakeClient()
            result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(client.calls, [])

    def test_gate2_duplicate_idempotency_key_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            message_input = _message_input()
            _seed_idempotency_record(connection, _expected_idempotency_key(message_input))

            client = _RecordingFakeClient()
            result = send_live_gmail_message(connection, client=client, **message_input)

            self.assertEqual(result["status"], STATUS_BLOCKED_DUPLICATE)
            self.assertEqual(result["gate_failed"], "ledger_dedupe")
            self.assertIsNotNone(result["existing_idempotency_record"])
            self.assertFalse(result["safety_assertions"]["network_called"])
            self.assertEqual(client.calls, [])

    def test_gate3_rail_state_not_live_fails_closed_by_default(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            self.assertEqual(status.RAIL_STATES["gmail"], "inert")

            client = _RecordingFakeClient()
            result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_RAIL_STATE)
            self.assertEqual(result["gate_failed"], "rail_state")
            self.assertEqual(result["rail_state"], "inert")
            self.assertEqual(client.calls, [])

    def test_gate4_both_credential_env_vars_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR, None)
                    os.environ.pop(GMAIL_RAIL_APP_PASSWORD_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_MISSING)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertFalse(result["credential_present"])
            self.assertFalse(result["safety_assertions"]["credential_values_read"])
            self.assertEqual(client.calls, [])

    def test_gate4_one_credential_env_var_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(
                    os.environ, {GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_SENDER_ADDRESS}
                ):
                    os.environ.pop(GMAIL_RAIL_APP_PASSWORD_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_MISSING)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertEqual(client.calls, [])

    def test_gate4_credential_env_var_empty_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(
                    "os.environ",
                    {
                        GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_SENDER_ADDRESS,
                        GMAIL_RAIL_APP_PASSWORD_ENV_VAR: "   ",
                    },
                ):
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_EMPTY)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertEqual(client.calls, [])

    def test_recipient_scoping_missing_controlled_recipient_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict(
                    "os.environ",
                    {
                        GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR: FAKE_SENDER_ADDRESS,
                        GMAIL_RAIL_APP_PASSWORD_ENV_VAR: FAKE_APP_PASSWORD,
                    },
                ):
                    os.environ.pop(GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED)
            self.assertEqual(result["gate_failed"], "recipient_scoping")
            self.assertEqual(client.calls, [])

    def test_recipient_scoping_mismatched_recipient_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(
                        connection,
                        client=client,
                        **_message_input(to_address="someone.else@example.com"),
                    )

            self.assertEqual(result["status"], STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED)
            self.assertEqual(result["gate_failed"], "recipient_scoping")
            self.assertEqual(client.calls, [])

    def test_all_checks_satisfied_reaches_fake_client_with_correct_call(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    client = _RecordingFakeClient()
                    result = send_live_gmail_message(connection, client=client, **_message_input())

            self.assertEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertIsNone(result["gate_failed"])
            self.assertTrue(result["gmail_message_sent"])
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(client.calls[0]["to_address"], FAKE_CONTROLLED_RECIPIENT)
            self.assertEqual(client.calls[0]["subject"], "Test subject")
            self.assertEqual(client.calls[0]["body"], "Test body")
            self.assertEqual(client.calls[0]["sender"], FAKE_SENDER_ADDRESS)
            self.assertTrue(result["safety_assertions"]["credential_values_read"])
            self.assertTrue(result["safety_assertions"]["recipient_is_controlled"])

    def test_all_checks_satisfied_real_client_sends_correct_message_shape(self) -> None:
        # Proves the real SMTP mechanics (host, port, login, send_message) via an
        # injected smtp_factory -- never a real network connection.
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            fake_smtp = _RecordingFakeSmtp()
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GmailSmtpClient(
                        app_password=FAKE_APP_PASSWORD, smtp_factory=fake_smtp
                    )
                    result = send_live_gmail_message(
                        connection, client=real_client, **_message_input()
                    )

            self.assertEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertEqual(fake_smtp.host, "smtp.gmail.com")
            self.assertEqual(fake_smtp.port, 465)
            self.assertEqual(len(fake_smtp.login_calls), 1)
            self.assertEqual(fake_smtp.login_calls[0], (FAKE_SENDER_ADDRESS, FAKE_APP_PASSWORD))
            self.assertEqual(len(fake_smtp.sent_messages), 1)
            sent_message = fake_smtp.sent_messages[0]
            self.assertEqual(sent_message["To"], FAKE_CONTROLLED_RECIPIENT)
            self.assertEqual(sent_message["From"], FAKE_SENDER_ADDRESS)
            self.assertEqual(sent_message["Subject"], "Test subject")
            self.assertEqual(sent_message.get_content().strip(), "Test body")

    def test_real_client_converts_transport_failure_to_structured_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GmailSmtpClient(
                        app_password=FAKE_APP_PASSWORD, smtp_factory=_FailingSmtpFactory()
                    )
                    result = send_live_gmail_message(
                        connection, client=real_client, **_message_input()
                    )

            self.assertNotEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertFalse(result["gmail_message_sent"])
            self.assertIn("error_type", result["client_result"])

    def test_real_client_converts_auth_failure_to_structured_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            fake_smtp = _RecordingFakeSmtp(raise_on_login=True)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GmailSmtpClient(
                        app_password=FAKE_APP_PASSWORD, smtp_factory=fake_smtp
                    )
                    result = send_live_gmail_message(
                        connection, client=real_client, **_message_input()
                    )

            self.assertNotEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertFalse(result["gmail_message_sent"])
            self.assertEqual(fake_smtp.sent_messages, [])

    def test_no_credential_value_ever_appears_in_serialized_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GmailSmtpClient(
                        app_password=FAKE_APP_PASSWORD, smtp_factory=_RecordingFakeSmtp()
                    )
                    result = send_live_gmail_message(
                        connection, client=real_client, **_message_input()
                    )

            serialized = json.dumps(result)
            self.assertNotIn(FAKE_APP_PASSWORD, serialized)
            # The sender address is not secret and may legitimately appear.
            self.assertIn(FAKE_SENDER_ADDRESS, serialized)

            # Also true of every gate-refusal shape (no credential ever read at all).
            with _migrated_test_connection() as blocked_connection:
                blocked_result = send_live_gmail_message(blocked_connection, **_message_input())
                self.assertNotIn(FAKE_APP_PASSWORD, json.dumps(blocked_result))

    def test_successful_live_send_persists_idempotency_record_and_blocks_retry(self) -> None:
        # Mirrors rails.todoist's real-bug regression test: gate 2 must not only
        # CHECK for an existing idempotency record but also WRITE one after a
        # successful send, so an immediate identical-input retry is blocked rather
        # than risking a second live send.
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            client = _RecordingFakeClient()
            message_input = _message_input()

            with mock.patch.dict(status._RAIL_STATES, {"gmail": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    first_result = send_live_gmail_message(
                        connection, client=client, **message_input
                    )
                    second_result = send_live_gmail_message(
                        connection, client=client, **message_input
                    )

            self.assertEqual(first_result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertIsNone(first_result["gate_failed"])
            self.assertTrue(first_result["idempotency_record_persisted"])
            self.assertIsNotNone(first_result["idempotency_record"])

            self.assertEqual(second_result["status"], STATUS_BLOCKED_DUPLICATE)
            self.assertEqual(second_result["gate_failed"], "ledger_dedupe")
            self.assertIsNotNone(second_result["existing_idempotency_record"])
            self.assertFalse(second_result["safety_assertions"]["network_called"])

            self.assertEqual(len(client.calls), 1)

    def test_evaluate_and_require_permission_helpers(self) -> None:
        with _migrated_test_connection() as connection:
            decision = evaluate_gmail_rail_live_send_permission(connection)
            self.assertFalse(decision["allowed"])
            self.assertEqual(decision["category"], GMAIL_RAIL_LIVE_SEND_PERMISSION)
            with self.assertRaises(GmailRailPermissionDenied):
                require_gmail_rail_live_send_permission(connection)

            _set_permission(connection)
            allowed_decision = require_gmail_rail_live_send_permission(connection)
            self.assertTrue(allowed_decision["allowed"])


def _message_input(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "source_type": "routine",
        "source_id": "routine-1",
        "subject": "Test subject",
        "body": "Test body",
        "to_address": FAKE_CONTROLLED_RECIPIENT,
    }
    item.update(overrides)
    return item


def _expected_idempotency_key(message_input: dict[str, object]) -> str:
    from personalos.rails.gmail import _build_gmail_message_record

    message = _build_gmail_message_record(**message_input)
    return generate_idempotency_key(
        target_system="gmail",
        operation_type="send",
        source_type=message["source_type"],
        source_id=message["source_id"],
        dedupe_key=message["dedupe_key"],
        payload={
            "subject": message["subject"],
            "body": message["body"],
            "to_address": message["to_address"],
        },
    )


def _seed_idempotency_record(connection: sqlite3.Connection, idempotency_key: str) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO idempotency_records (
                idempotency_key,
                target_system,
                operation_type,
                source_type,
                source_id,
                dedupe_key,
                payload_fingerprint,
                first_seen_at,
                last_seen_at,
                status,
                linked_intent_id,
                linked_attempt_id
            )
            VALUES (?, 'gmail', 'send', 'routine', 'routine-1', 'seeded-dedupe-key',
                    'sha256:seeded', '2026-07-10T10:00:00+00:00', '2026-07-10T10:00:00+00:00',
                    'blocked', NULL, NULL)
            """,
            (idempotency_key,),
        )


def _set_permission(
    connection: sqlite3.Connection,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=GMAIL_RAIL_LIVE_SEND_PERMISSION,
        mode=mode.value,
        metadata={"phase": "D", "packet": "P-RAIL-GM-01"},
        updated_by="tests",
        updated_at_utc="2026-07-10T10:00:00+00:00",
    )


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


if __name__ == "__main__":
    unittest.main()

import json
import os
import sqlite3
import tempfile
import unittest
import urllib.error
import urllib.request
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
from personalos.rails.calendar import (
    CALENDAR_RAIL_CLIENT_ID_ENV_VAR,
    CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR,
    CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR,
    CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
    CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR,
    STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED,
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_DUPLICATE,
    STATUS_BLOCKED_PERMISSION,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_EVENT_CREATE_PASSED,
    STATUS_TOKEN_REFRESH_FAILED,
    STATUS_TOKEN_REFRESH_PASSED,
    CalendarRailPermissionDenied,
    GoogleCalendarClient,
    create_live_calendar_event,
    evaluate_calendar_rail_live_write_permission,
    require_calendar_rail_live_write_permission,
)
from personalos.state import upsert_permission_setting

FAKE_CLIENT_ID = "fake-test-client-id-never-real"
FAKE_CLIENT_SECRET = "fake-test-client-secret-never-real"  # noqa: S105 - test fixture, not a real credential
FAKE_REFRESH_TOKEN = "fake-test-refresh-token-never-real"  # noqa: S105 - test fixture, not a real credential
FAKE_ACCESS_TOKEN = "fake-test-access-token-never-real"  # noqa: S105 - test fixture, not a real credential
FAKE_CONTROLLED_CALENDAR_ID = "fake.controlled.calendar@group.calendar.google.com"

_FAKE_CREDENTIAL_ENV = {
    CALENDAR_RAIL_CLIENT_ID_ENV_VAR: FAKE_CLIENT_ID,
    CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR: FAKE_CLIENT_SECRET,
    CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR: FAKE_REFRESH_TOKEN,
    CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR: FAKE_CONTROLLED_CALENDAR_ID,
}


class _RecordingFakeClient:
    """Bypass client (no urllib at all) used by the gate-isolation tests."""

    def __init__(self, *, fail_token_refresh: bool = False) -> None:
        self.token_refresh_calls: int = 0
        self.create_event_calls: list[dict] = []
        self._fail_token_refresh = fail_token_refresh

    def refresh_access_token(self):
        self.token_refresh_calls += 1
        if self._fail_token_refresh:
            return {
                "status": STATUS_TOKEN_REFRESH_FAILED,
                "network_called": True,
                "error_type": "HTTPError",
                "error_message": "invalid_grant: Token has been expired or revoked.",
            }
        return {
            "status": STATUS_TOKEN_REFRESH_PASSED,
            "network_called": True,
            "access_token": FAKE_ACCESS_TOKEN,
            "expires_in": 3599,
        }

    def create_event(self, *, access_token, event):
        self.create_event_calls.append({"access_token": access_token, "event": dict(event)})
        return {
            "status": STATUS_EVENT_CREATE_PASSED,
            "external_event_id": "fake-external-event-1",
            "network_called": True,
            "external_mutation": True,
        }


class _RecordingOpener:
    """Fake `urllib.request.urlopen` replacement that records every Request it saw
    and returns a queue of canned responses (one per call, in order)."""

    def __init__(self, *, responses: list[tuple[bytes, int]]) -> None:
        self.requests: list[urllib.request.Request] = []
        self._responses = list(responses)

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        body, status_code = self._responses.pop(0)
        return _FakeHTTPResponse(body, status_code)


class _FailingOpener:
    def __call__(self, request, timeout=None):
        raise urllib.error.URLError("simulated network failure")


class _TokenRefreshFailsOpener:
    """Realistic Google error shape for an expired/revoked refresh token; fails on
    the FIRST call (token refresh) and must never be called a second time."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, request, timeout=None):
        self.call_count += 1
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},
            None,
        )


class _FakeHTTPResponse:
    def __init__(self, body: bytes, status_code: int) -> None:
        self._body = body
        self.status = status_code

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class CalendarRailGateTest(unittest.TestCase):
    def test_gate1_permission_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            client = _RecordingFakeClient()
            result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(result["gate_failed"], "permission")
            self.assertFalse(result["permission"]["allowed"])
            self.assertFalse(result["external_mutation"])
            self.assertFalse(result["safety_assertions"]["network_called"])
            self.assertEqual(client.token_refresh_calls, 0)
            self.assertEqual(client.create_event_calls, [])

    def test_gate1_permission_approval_required_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, mode=PermissionMode.APPROVAL_REQUIRED)
            client = _RecordingFakeClient()
            result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(result["gate_failed"], "permission")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate1_gmail_live_send_permission_does_not_satisfy_calendar_gate(self) -> None:
        # Calendar's live-write permission is a structurally distinct category from
        # Gmail's/Todoist's live permissions; enabling one must never satisfy the other.
        with _migrated_test_connection() as connection:
            upsert_permission_setting(
                connection,
                category="gmail_rail_live_send",
                mode=PermissionMode.AUTO_WRITE.value,
                metadata={},
                updated_by="tests",
                updated_at_utc="2026-07-10T10:00:00+00:00",
            )
            client = _RecordingFakeClient()
            result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate2_duplicate_idempotency_key_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            event_input = _event_input()
            _seed_idempotency_record(connection, _expected_idempotency_key(event_input))

            client = _RecordingFakeClient()
            result = create_live_calendar_event(connection, client=client, **event_input)

            self.assertEqual(result["status"], STATUS_BLOCKED_DUPLICATE)
            self.assertEqual(result["gate_failed"], "ledger_dedupe")
            self.assertIsNotNone(result["existing_idempotency_record"])
            self.assertFalse(result["safety_assertions"]["network_called"])
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate3_rail_state_not_live_fails_closed_by_default(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            self.assertEqual(status.RAIL_STATES["calendar"], "inert")

            client = _RecordingFakeClient()
            result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_RAIL_STATE)
            self.assertEqual(result["gate_failed"], "rail_state")
            self.assertEqual(result["rail_state"], "inert")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate4_all_credential_env_vars_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(CALENDAR_RAIL_CLIENT_ID_ENV_VAR, None)
                    os.environ.pop(CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR, None)
                    os.environ.pop(CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_MISSING)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertFalse(result["credential_present"])
            self.assertFalse(result["safety_assertions"]["credential_values_read"])
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate4_one_credential_env_var_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict(
                    os.environ,
                    {
                        CALENDAR_RAIL_CLIENT_ID_ENV_VAR: FAKE_CLIENT_ID,
                        CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR: FAKE_CLIENT_SECRET,
                    },
                ):
                    os.environ.pop(CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_MISSING)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_gate4_credential_env_var_empty_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict(
                    "os.environ",
                    {
                        CALENDAR_RAIL_CLIENT_ID_ENV_VAR: FAKE_CLIENT_ID,
                        CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR: FAKE_CLIENT_SECRET,
                        CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR: "   ",
                    },
                ):
                    client = _RecordingFakeClient()
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_EMPTY)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_calendar_scoping_missing_controlled_calendar_id_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict(
                    "os.environ",
                    {
                        CALENDAR_RAIL_CLIENT_ID_ENV_VAR: FAKE_CLIENT_ID,
                        CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR: FAKE_CLIENT_SECRET,
                        CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR: FAKE_REFRESH_TOKEN,
                    },
                ):
                    os.environ.pop(CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED)
            self.assertEqual(result["gate_failed"], "calendar_scoping")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_calendar_scoping_mismatched_calendar_id_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    client = _RecordingFakeClient()
                    result = create_live_calendar_event(
                        connection,
                        client=client,
                        **_event_input(calendar_id="someone.else@group.calendar.google.com"),
                    )

            self.assertEqual(result["status"], STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED)
            self.assertEqual(result["gate_failed"], "calendar_scoping")
            self.assertEqual(client.token_refresh_calls, 0)

    def test_token_refresh_failure_does_not_attempt_event_creation(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            client = _RecordingFakeClient(fail_token_refresh=True)
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_TOKEN_REFRESH_FAILED)
            self.assertIsNone(result["gate_failed"])
            self.assertFalse(result["calendar_event_created"])
            self.assertFalse(result["event_create_attempted"])
            self.assertIsNone(result["event_create_result"])
            self.assertEqual(result["token_refresh_result"]["status"], STATUS_TOKEN_REFRESH_FAILED)
            self.assertEqual(client.token_refresh_calls, 1)
            self.assertEqual(client.create_event_calls, [])
            self.assertFalse(result["idempotency_record_persisted"])

    def test_all_checks_satisfied_reaches_fake_client_with_correct_calls(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            client = _RecordingFakeClient()
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            self.assertEqual(result["status"], STATUS_EVENT_CREATE_PASSED)
            self.assertIsNone(result["gate_failed"])
            self.assertTrue(result["calendar_event_created"])
            self.assertTrue(result["event_create_attempted"])
            self.assertEqual(client.token_refresh_calls, 1)
            self.assertEqual(len(client.create_event_calls), 1)
            call = client.create_event_calls[0]
            self.assertEqual(call["access_token"], FAKE_ACCESS_TOKEN)
            self.assertEqual(call["event"]["summary"], "Test event")
            self.assertEqual(call["event"]["start"], {"dateTime": "2026-07-15T10:00:00+00:00"})
            self.assertEqual(call["event"]["end"], {"dateTime": "2026-07-15T11:00:00+00:00"})
            self.assertTrue(result["safety_assertions"]["credential_values_read"])
            self.assertTrue(result["safety_assertions"]["calendar_is_controlled"])
            self.assertTrue(result["token_refresh_result"]["access_token_obtained"])
            self.assertNotIn("access_token", result["token_refresh_result"])

    def test_all_checks_satisfied_real_client_sends_correct_request_shapes(self) -> None:
        # Proves the real two-call HTTPS mechanics (token endpoint, events endpoint,
        # auth header using the token from the FIRST response) via an injected
        # opener -- never a real network call.
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            opener = _RecordingOpener(
                responses=[
                    (json.dumps({"access_token": FAKE_ACCESS_TOKEN, "expires_in": 3599}).encode(), 200),
                    (json.dumps({"id": "real-client-event-1"}).encode(), 200),
                ]
            )
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GoogleCalendarClient(
                        client_id=FAKE_CLIENT_ID,
                        client_secret=FAKE_CLIENT_SECRET,
                        refresh_token=FAKE_REFRESH_TOKEN,
                        calendar_id=FAKE_CONTROLLED_CALENDAR_ID,
                        opener=opener,
                    )
                    result = create_live_calendar_event(
                        connection, client=real_client, **_event_input()
                    )

            self.assertEqual(result["status"], STATUS_EVENT_CREATE_PASSED)
            self.assertEqual(len(opener.requests), 2)

            token_request = opener.requests[0]
            self.assertEqual(token_request.full_url, "https://oauth2.googleapis.com/token")
            self.assertEqual(token_request.get_method(), "POST")
            from urllib.parse import parse_qs

            parsed_token_body = parse_qs(token_request.data.decode("utf-8"))
            self.assertEqual(parsed_token_body["client_id"], [FAKE_CLIENT_ID])
            self.assertEqual(parsed_token_body["client_secret"], [FAKE_CLIENT_SECRET])
            self.assertEqual(parsed_token_body["refresh_token"], [FAKE_REFRESH_TOKEN])
            self.assertEqual(parsed_token_body["grant_type"], ["refresh_token"])

            events_request = opener.requests[1]
            self.assertEqual(
                events_request.full_url,
                f"https://www.googleapis.com/calendar/v3/calendars/{FAKE_CONTROLLED_CALENDAR_ID}/events",
            )
            self.assertEqual(events_request.get_method(), "POST")
            self.assertEqual(
                events_request.get_header("Authorization"), f"Bearer {FAKE_ACCESS_TOKEN}"
            )
            sent_body = json.loads(events_request.data.decode("utf-8"))
            self.assertEqual(sent_body["summary"], "Test event")
            self.assertEqual(sent_body["start"], {"dateTime": "2026-07-15T10:00:00+00:00"})
            self.assertEqual(sent_body["end"], {"dateTime": "2026-07-15T11:00:00+00:00"})

    def test_real_client_token_refresh_failure_is_distinguished_from_event_create_failure(
        self,
    ) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            failing_opener = _TokenRefreshFailsOpener()
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GoogleCalendarClient(
                        client_id=FAKE_CLIENT_ID,
                        client_secret=FAKE_CLIENT_SECRET,
                        refresh_token=FAKE_REFRESH_TOKEN,
                        calendar_id=FAKE_CONTROLLED_CALENDAR_ID,
                        opener=failing_opener,
                    )
                    result = create_live_calendar_event(
                        connection, client=real_client, **_event_input()
                    )

            self.assertEqual(result["status"], STATUS_TOKEN_REFRESH_FAILED)
            self.assertNotEqual(result["status"], STATUS_EVENT_CREATE_PASSED)
            self.assertFalse(result["calendar_event_created"])
            self.assertFalse(result["event_create_attempted"])
            self.assertIsNone(result["event_create_result"])
            self.assertIn("error_type", result["token_refresh_result"])
            # Exactly one call was made (the token refresh); create_event never ran.
            self.assertEqual(failing_opener.call_count, 1)

    def test_real_client_event_create_failure_after_successful_token_refresh(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            opener = _RecordingOpener(
                responses=[
                    (json.dumps({"access_token": FAKE_ACCESS_TOKEN, "expires_in": 3599}).encode(), 200),
                ]
            )

            class _FailsOnSecondCallOpener:
                def __init__(self, first_opener) -> None:
                    self._first_opener = first_opener
                    self._calls = 0

                def __call__(self, request, timeout=None):
                    self._calls += 1
                    if self._calls == 1:
                        return self._first_opener(request, timeout=timeout)
                    raise urllib.error.URLError("simulated event-create network failure")

            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    real_client = GoogleCalendarClient(
                        client_id=FAKE_CLIENT_ID,
                        client_secret=FAKE_CLIENT_SECRET,
                        refresh_token=FAKE_REFRESH_TOKEN,
                        calendar_id=FAKE_CONTROLLED_CALENDAR_ID,
                        opener=_FailsOnSecondCallOpener(opener),
                    )
                    result = create_live_calendar_event(
                        connection, client=real_client, **_event_input()
                    )

            self.assertNotEqual(result["status"], STATUS_EVENT_CREATE_PASSED)
            self.assertNotEqual(result["status"], STATUS_TOKEN_REFRESH_FAILED)
            self.assertTrue(result["event_create_attempted"])
            self.assertFalse(result["calendar_event_created"])
            self.assertEqual(result["token_refresh_result"]["status"], STATUS_TOKEN_REFRESH_PASSED)
            self.assertIn("error_type", result["event_create_result"])
            self.assertFalse(result["idempotency_record_persisted"])

    def test_no_credential_or_access_token_value_ever_appears_in_serialized_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            client = _RecordingFakeClient()
            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    result = create_live_calendar_event(connection, client=client, **_event_input())

            serialized = json.dumps(result)
            self.assertNotIn(FAKE_CLIENT_ID, serialized)
            self.assertNotIn(FAKE_CLIENT_SECRET, serialized)
            self.assertNotIn(FAKE_REFRESH_TOKEN, serialized)
            self.assertNotIn(FAKE_ACCESS_TOKEN, serialized)

            # Also true of every gate-refusal shape (no credential ever read at all).
            with _migrated_test_connection() as blocked_connection:
                blocked_result = create_live_calendar_event(blocked_connection, **_event_input())
                blocked_serialized = json.dumps(blocked_result)
                self.assertNotIn(FAKE_CLIENT_ID, blocked_serialized)
                self.assertNotIn(FAKE_CLIENT_SECRET, blocked_serialized)
                self.assertNotIn(FAKE_REFRESH_TOKEN, blocked_serialized)
                self.assertNotIn(FAKE_ACCESS_TOKEN, blocked_serialized)

    def test_successful_live_write_persists_idempotency_record_and_blocks_retry(self) -> None:
        # Mirrors rails.todoist's / rails.gmail's real-bug regression test: gate 2
        # must not only CHECK for an existing idempotency record but also WRITE one
        # after a successful create, so an immediate identical-input retry is
        # blocked rather than risking a second live write.
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            client = _RecordingFakeClient()
            event_input = _event_input()

            with mock.patch.dict(status._RAIL_STATES, {"calendar": "live"}):
                with mock.patch.dict("os.environ", _FAKE_CREDENTIAL_ENV):
                    first_result = create_live_calendar_event(
                        connection, client=client, **event_input
                    )
                    second_result = create_live_calendar_event(
                        connection, client=client, **event_input
                    )

            self.assertEqual(first_result["status"], STATUS_EVENT_CREATE_PASSED)
            self.assertIsNone(first_result["gate_failed"])
            self.assertTrue(first_result["idempotency_record_persisted"])
            self.assertIsNotNone(first_result["idempotency_record"])

            self.assertEqual(second_result["status"], STATUS_BLOCKED_DUPLICATE)
            self.assertEqual(second_result["gate_failed"], "ledger_dedupe")
            self.assertIsNotNone(second_result["existing_idempotency_record"])
            self.assertFalse(second_result["safety_assertions"]["network_called"])

            self.assertEqual(client.token_refresh_calls, 1)
            self.assertEqual(len(client.create_event_calls), 1)

    def test_evaluate_and_require_permission_helpers(self) -> None:
        with _migrated_test_connection() as connection:
            decision = evaluate_calendar_rail_live_write_permission(connection)
            self.assertFalse(decision["allowed"])
            self.assertEqual(decision["category"], CALENDAR_RAIL_LIVE_WRITE_PERMISSION)
            with self.assertRaises(CalendarRailPermissionDenied):
                require_calendar_rail_live_write_permission(connection)

            _set_permission(connection)
            allowed_decision = require_calendar_rail_live_write_permission(connection)
            self.assertTrue(allowed_decision["allowed"])


def _event_input(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "source_type": "routine",
        "source_id": "routine-1",
        "summary": "Test event",
        "description": "Test description",
        "start_time": "2026-07-15T10:00:00+00:00",
        "end_time": "2026-07-15T11:00:00+00:00",
        "calendar_id": FAKE_CONTROLLED_CALENDAR_ID,
    }
    item.update(overrides)
    return item


def _expected_idempotency_key(event_input: dict[str, object]) -> str:
    from personalos.rails.calendar import _build_calendar_event_record

    event = _build_calendar_event_record(**event_input)
    return generate_idempotency_key(
        target_system="calendar",
        operation_type="create",
        source_type=event["source_type"],
        source_id=event["source_id"],
        dedupe_key=event["dedupe_key"],
        payload={
            "summary": event["summary"],
            "description": event["description"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "calendar_id": event["calendar_id"],
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
            VALUES (?, 'calendar', 'create', 'routine', 'routine-1', 'seeded-dedupe-key',
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
        category=CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
        mode=mode.value,
        metadata={"phase": "D", "packet": "P-RAIL-CAL-01"},
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

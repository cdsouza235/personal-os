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
from personalos.rails.todoist import (
    STATUS_BLOCKED_CREDENTIAL_EMPTY,
    STATUS_BLOCKED_CREDENTIAL_MISSING,
    STATUS_BLOCKED_DUPLICATE,
    STATUS_BLOCKED_PERMISSION,
    STATUS_BLOCKED_RAIL_STATE,
    STATUS_CLIENT_CALL_PASSED,
    TODOIST_RAIL_CREDENTIAL_ENV_VAR,
    TODOIST_RAIL_LIVE_WRITE_PERMISSION,
    TodoistRailClient,
    TodoistRailPermissionDenied,
    create_live_todoist_task,
    evaluate_todoist_rail_live_write_permission,
    require_todoist_rail_live_write_permission,
)
from personalos.state import upsert_permission_setting

FAKE_TOKEN = "fake-test-token-value-never-real"  # noqa: S105 - test fixture, not a real credential


class _RecordingOpener:
    """Fake `urllib.request.urlopen` replacement that records the Request it received."""

    def __init__(self, *, response_body: bytes = b'{"id": "9999999"}', status_code: int = 200) -> None:
        self.requests: list[urllib.request.Request] = []
        self._response_body = response_body
        self._status_code = status_code

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        return _FakeHTTPResponse(self._response_body, self._status_code)


class _FailingOpener:
    def __call__(self, request, timeout=None):
        raise urllib.error.URLError("simulated network failure")


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


class _RecordingFakeClient:
    """Bypass client (no urllib at all) used by the gate-isolation tests."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_task(self, payload):
        self.calls.append(dict(payload))
        return {
            "status": STATUS_CLIENT_CALL_PASSED,
            "external_task_id": "fake-external-1",
            "network_called": True,
            "external_mutation": True,
        }


class TodoistRailGateTest(unittest.TestCase):
    def test_gate1_permission_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            client = _RecordingFakeClient()
            result = create_live_todoist_task(connection, client=client, **_task_input())

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
            result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(result["gate_failed"], "permission")
            self.assertEqual(client.calls, [])

    def test_gate1_dev_test_simulated_write_permission_does_not_satisfy_live_gate(self) -> None:
        # The existing dev/test simulated-write permission is a structurally distinct
        # category; enabling it must never be able to satisfy the live rail's gate.
        with _migrated_test_connection() as connection:
            upsert_permission_setting(
                connection,
                category="todoist_module_dev_test_simulated_write",
                mode=PermissionMode.AUTO_WRITE.value,
                metadata={"dev_test_only": True},
                updated_by="tests",
                updated_at_utc="2026-07-10T10:00:00+00:00",
            )
            client = _RecordingFakeClient()
            result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_PERMISSION)
            self.assertEqual(client.calls, [])

    def test_gate2_duplicate_idempotency_key_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            task_input = _task_input()
            _seed_idempotency_record(connection, _expected_idempotency_key(task_input))

            client = _RecordingFakeClient()
            result = create_live_todoist_task(connection, client=client, **task_input)

            self.assertEqual(result["status"], STATUS_BLOCKED_DUPLICATE)
            self.assertEqual(result["gate_failed"], "ledger_dedupe")
            self.assertIsNotNone(result["existing_idempotency_record"])
            self.assertFalse(result["safety_assertions"]["network_called"])
            self.assertEqual(client.calls, [])

    def test_gate3_rail_state_not_live_fails_closed_by_default(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            self.assertEqual(status.RAIL_STATES["todoist"], "inert")

            client = _RecordingFakeClient()
            result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_RAIL_STATE)
            self.assertEqual(result["gate_failed"], "rail_state")
            self.assertEqual(result["rail_state"], "inert")
            self.assertEqual(client.calls, [])

    def test_gate4_credential_env_var_missing_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(TODOIST_RAIL_CREDENTIAL_ENV_VAR, None)
                    client = _RecordingFakeClient()
                    result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_MISSING)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertFalse(result["credential_present"])
            self.assertFalse(result["safety_assertions"]["credential_values_read"])
            self.assertEqual(client.calls, [])

    def test_gate4_credential_env_var_empty_fails_closed(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict("os.environ", {TODOIST_RAIL_CREDENTIAL_ENV_VAR: "   "}):
                    client = _RecordingFakeClient()
                    result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_BLOCKED_CREDENTIAL_EMPTY)
            self.assertEqual(result["gate_failed"], "credentials")
            self.assertEqual(client.calls, [])

    def test_all_four_gates_satisfied_reaches_fake_client_with_correct_call(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict("os.environ", {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TOKEN}):
                    client = _RecordingFakeClient()
                    result = create_live_todoist_task(connection, client=client, **_task_input())

            self.assertEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertIsNone(result["gate_failed"])
            self.assertTrue(result["todoist_task_created"])
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(client.calls[0]["content"], "Buy milk")
            self.assertEqual(client.calls[0]["priority"], 2)
            self.assertTrue(result["safety_assertions"]["credential_values_read"])

    def test_all_four_gates_satisfied_real_client_sends_correct_request_shape(self) -> None:
        # Proves the real HTTPS mechanics (endpoint, auth header, JSON body) via an
        # injected opener -- never a real network call.
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            opener = _RecordingOpener()
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict("os.environ", {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TOKEN}):
                    real_client = TodoistRailClient(token=FAKE_TOKEN, opener=opener)
                    result = create_live_todoist_task(
                        connection,
                        client=real_client,
                        **_task_input(),
                    )

            self.assertEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertEqual(len(opener.requests), 1)
            sent_request = opener.requests[0]
            self.assertEqual(sent_request.full_url, "https://api.todoist.com/api/v1/tasks")
            self.assertEqual(sent_request.get_method(), "POST")
            self.assertEqual(sent_request.get_header("Authorization"), f"Bearer {FAKE_TOKEN}")
            sent_body = json.loads(sent_request.data.decode("utf-8"))
            self.assertEqual(sent_body["content"], "Buy milk")

    def test_real_client_converts_transport_failure_to_structured_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict("os.environ", {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TOKEN}):
                    real_client = TodoistRailClient(token=FAKE_TOKEN, opener=_FailingOpener())
                    result = create_live_todoist_task(
                        connection,
                        client=real_client,
                        **_task_input(),
                    )

            self.assertNotEqual(result["status"], STATUS_CLIENT_CALL_PASSED)
            self.assertFalse(result["todoist_task_created"])
            self.assertIn("error_type", result["client_result"])

    def test_no_credential_value_ever_appears_in_serialized_result(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection)
            with mock.patch.dict(status._RAIL_STATES, {"todoist": "live"}):
                with mock.patch.dict("os.environ", {TODOIST_RAIL_CREDENTIAL_ENV_VAR: FAKE_TOKEN}):
                    real_client = TodoistRailClient(token=FAKE_TOKEN, opener=_RecordingOpener())
                    result = create_live_todoist_task(
                        connection,
                        client=real_client,
                        **_task_input(),
                    )

            serialized = json.dumps(result)
            self.assertNotIn(FAKE_TOKEN, serialized)

            # Also true of every gate-refusal shape (no credential ever read at all).
            with _migrated_test_connection() as blocked_connection:
                blocked_result = create_live_todoist_task(blocked_connection, **_task_input())
                self.assertNotIn(FAKE_TOKEN, json.dumps(blocked_result))

    def test_evaluate_and_require_permission_helpers(self) -> None:
        with _migrated_test_connection() as connection:
            decision = evaluate_todoist_rail_live_write_permission(connection)
            self.assertFalse(decision["allowed"])
            self.assertEqual(decision["category"], TODOIST_RAIL_LIVE_WRITE_PERMISSION)
            with self.assertRaises(TodoistRailPermissionDenied):
                require_todoist_rail_live_write_permission(connection)

            _set_permission(connection)
            allowed_decision = require_todoist_rail_live_write_permission(connection)
            self.assertTrue(allowed_decision["allowed"])


def _task_input(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "task_title": "Buy milk",
        "description": "",
        "source_type": "routine",
        "source_id": "routine-1",
        "project": "Inbox",
        "labels": [],
        "due_date_or_due_string": "",
        "priority": 2,
    }
    item.update(overrides)
    return item


def _expected_idempotency_key(task_input: dict[str, object]) -> str:
    from personalos.state import build_todoist_task_record

    task = build_todoist_task_record(**task_input)
    return generate_idempotency_key(
        target_system="todoist",
        operation_type="create",
        source_type=task["source_type"],
        source_id=task["source_id"],
        dedupe_key=task["dedupe_key"],
        payload={
            "task_title": task["task_title"],
            "description": task["description"],
            "labels": list(task["labels"]),
            "due_date_or_due_string": task["due_date_or_due_string"],
            "priority": task["priority"],
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
            VALUES (?, 'todoist', 'create', 'routine', 'routine-1', 'seeded-dedupe-key',
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
        category=TODOIST_RAIL_LIVE_WRITE_PERMISSION,
        mode=mode.value,
        metadata={"phase": "D", "packet": "P-RAIL-TD-01"},
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

"""Live Todoist rail adapter (P-RAIL-TD-01) — inert until P-RAIL-TD-02 (G5) flips it.

This module is the ONE place in the codebase allowed to make a genuine HTTPS call to
Todoist. `create_live_todoist_task` is the sole public entry point and it enforces the
fixed gating order from docs/ARCHITECTURE.md invariant #3:

    permission -> ledger/dedupe -> rail-state -> credentials

Any gate left unsatisfied is a hard stop: the function returns a structured refusal
(never a silent no-op, never a raised exception) and the live HTTPS client is never
constructed. Today RAIL_STATES["todoist"] is "inert" (status.py), so the rail-state
gate always fails closed in real usage; flipping that rail live is a separate,
G5-gated packet (P-RAIL-TD-02), not this one.

Only `TodoistRailClient.create_task` may raise on a genuine transport failure, and only
after every gate has passed; it is always called through a try/except that converts
any such failure into the same structured shape the gates use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from personalos.idempotency import generate_idempotency_key, payload_fingerprint
from personalos.permissions import PermissionMode
from personalos.side_effects import get_idempotency_record
from personalos.state import build_todoist_task_record, get_permission_setting
from personalos.status import RAIL_STATES

TODOIST_RAIL_LIVE_WRITE_PERMISSION = "todoist_rail_live_write"

# Phase D rail credential (deliberately renamed from the retired Phase 14-C var — see
# .env.example for the rationale). Read via os.environ only; never hardcoded/logged.
TODOIST_RAIL_CREDENTIAL_ENV_VAR = "PERSONALOS_RAIL_TODOIST_TOKEN"

TODOIST_REST_ENDPOINT = "https://api.todoist.com/api/v1/tasks"
TODOIST_REQUEST_TIMEOUT_SECONDS = 10.0

STATUS_BLOCKED_PERMISSION = "todoist_rail_live_write_blocked_permission_denied"
STATUS_BLOCKED_DUPLICATE = "todoist_rail_live_write_blocked_duplicate_idempotency_key"
STATUS_BLOCKED_RAIL_STATE = "todoist_rail_live_write_blocked_rail_state_not_live"
STATUS_BLOCKED_CREDENTIAL_MISSING = "todoist_rail_live_write_blocked_credential_env_var_missing"
STATUS_BLOCKED_CREDENTIAL_EMPTY = "todoist_rail_live_write_blocked_credential_env_var_empty"
STATUS_CLIENT_CALL_PASSED = "todoist_rail_live_write_client_call_passed"
STATUS_CLIENT_CALL_FAILED = "todoist_rail_live_write_client_call_failed"


class TodoistRailPermissionDenied(PermissionError):
    """Raised only by `require_todoist_rail_live_write_permission`, never by the gated entry point."""


class TodoistRailClientProtocol(Protocol):
    def create_task(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Create a Todoist task from an API-shaped payload (POST /api/v1/tasks body)."""


class TodoistRailClient:
    """Thin stdlib-only HTTPS client for the real Todoist REST API.

    Uses `urllib.request`/`urllib.error` only (no third-party HTTP library) so the
    manifest's network-primitive tripwire (RISK_REGISTER.md) has exactly one narrow,
    reviewed surface to watch. `opener` is injectable so tests can exercise the real
    request-construction path (endpoint, auth header, JSON body) without ever touching
    the network.
    """

    def __init__(
        self,
        *,
        token: str,
        endpoint: str = TODOIST_REST_ENDPOINT,
        timeout_seconds: float = TODOIST_REQUEST_TIMEOUT_SECONDS,
        opener: Any | None = None,
    ) -> None:
        self._token = token
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._opener = opener if opener is not None else urllib.request.urlopen

    def create_task(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(dict(payload)).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
                http_status = response.status if hasattr(response, "status") else response.getcode()
            parsed_body = json.loads(raw_body.decode("utf-8"))
            return {
                "status": STATUS_CLIENT_CALL_PASSED,
                "http_status": http_status,
                "external_task_id": parsed_body.get("id"),
                "network_called": True,
                "external_mutation": True,
                "mutation_state": "confirmed_after_task_create_response",
            }
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return {
                "status": STATUS_CLIENT_CALL_FAILED,
                "network_called": True,
                "external_mutation": "unconfirmed",
                "mutation_state": "unconfirmed_after_task_create_attempt",
                "error_type": type(error).__name__,
                "error_message": str(error),
            }


def create_live_todoist_task(
    connection: sqlite3.Connection,
    *,
    client: TodoistRailClientProtocol | None = None,
    credential_env_var: str = TODOIST_RAIL_CREDENTIAL_ENV_VAR,
    **task_input: Any,
) -> dict[str, Any]:
    """Enforce all four gates, in fixed order, then (only if every gate passes) create
    exactly one Todoist task via `client` (or a real `TodoistRailClient` if omitted).

    Every path returns a structured dict with `status`, `reason`, `gate_failed`
    (None once every gate has passed), and a `safety_assertions` block. Nothing this
    function returns ever contains a credential value.
    """
    task = build_todoist_task_record(**task_input)

    permission = evaluate_todoist_rail_live_write_permission(connection)
    if not permission["allowed"]:
        return _refusal(
            status=STATUS_BLOCKED_PERMISSION,
            reason=permission["reason"],
            gate_failed="permission",
            task=task,
            permission=permission,
        )

    idempotency_key = generate_idempotency_key(
        target_system="todoist",
        operation_type="create",
        source_type=task["source_type"],
        source_id=task["source_id"],
        dedupe_key=task["dedupe_key"],
        payload=_idempotency_payload(task),
    )
    existing_record = get_idempotency_record(connection, idempotency_key)
    if existing_record is not None:
        return _refusal(
            status=STATUS_BLOCKED_DUPLICATE,
            reason=(
                "An idempotency record already exists for this exact Todoist create "
                "intent; refusing to risk a duplicate live write."
            ),
            gate_failed="ledger_dedupe",
            task=task,
            permission=permission,
            idempotency_key=idempotency_key,
            existing_idempotency_record=existing_record,
        )

    rail_state = RAIL_STATES["todoist"]
    if rail_state != "live":
        return _refusal(
            status=STATUS_BLOCKED_RAIL_STATE,
            reason=f"Todoist rail state is '{rail_state}', not 'live'; refusing to call out.",
            gate_failed="rail_state",
            task=task,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
        )

    credential_present = credential_env_var in os.environ
    if not credential_present:
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_MISSING,
            reason=f"Credential env var is not set: {credential_env_var}",
            gate_failed="credentials",
            task=task,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_var=credential_env_var,
            credential_present=False,
        )

    token = os.environ[credential_env_var]
    if not token.strip():
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_EMPTY,
            reason=f"Credential env var is set but empty: {credential_env_var}",
            gate_failed="credentials",
            task=task,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_var=credential_env_var,
            credential_present=True,
            credential_values_read=True,
        )

    selected_client = client if client is not None else TodoistRailClient(token=token)
    client_result = selected_client.create_task(_todoist_api_payload(task))

    idempotency_record_persisted = False
    persisted_idempotency_record = None
    if client_result["status"] == STATUS_CLIENT_CALL_PASSED:
        # Persist the dedupe record ONLY once the live call is confirmed to have
        # succeeded, so that an immediate identical-input retry hits gate 2 above
        # and refuses, instead of repeating the live call (the exact hazard the
        # dedupe gate exists to prevent). A failed/uncertain client_result leaves
        # no record behind, so a genuinely transient failure can still be retried.
        persisted_idempotency_record = _persist_live_write_idempotency_record(
            connection,
            idempotency_key=idempotency_key,
            task=task,
        )
        idempotency_record_persisted = True

    return {
        "status": client_result["status"],
        "reason": (
            "Todoist rail client call attempted after every gate passed; see "
            "client_result for the outcome."
        ),
        "gate_failed": None,
        "dry_run": False,
        "no_send": False,
        "external_mutation": client_result.get("external_mutation", False),
        "todoist_task_created": client_result["status"] == STATUS_CLIENT_CALL_PASSED,
        "would_write": task,
        "permission": permission,
        "idempotency_key": idempotency_key,
        "idempotency_record_persisted": idempotency_record_persisted,
        "idempotency_record": persisted_idempotency_record,
        "rail_state": rail_state,
        "credential_env_var": credential_env_var,
        "client_result": client_result,
        "safety_assertions": {
            "credential_values_read": True,
            "credential_values_logged": False,
            "network_called": client_result.get("network_called", True),
            "external_mutation": client_result.get("external_mutation", False),
            "max_one_task_create": True,
            "gate_failed": None,
        },
    }


def evaluate_todoist_rail_live_write_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    setting = get_permission_setting(connection, TODOIST_RAIL_LIVE_WRITE_PERMISSION)
    if setting is None:
        return _permission_decision(
            allowed=False,
            mode=None,
            reason=f"Missing permission setting: {TODOIST_RAIL_LIVE_WRITE_PERMISSION}",
            setting=None,
        )
    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            mode=setting["mode"],
            reason=f"Invalid permission mode: {setting['mode']}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            mode=mode.value,
            reason=(
                f"Todoist live-write rail permission is not auto_write "
                f"(this dev/test simulated-write permission being enabled does not "
                f"count): {mode.value}"
            ),
            setting=setting,
        )
    return _permission_decision(
        allowed=True,
        mode=mode.value,
        reason="Todoist live-write rail permission is explicitly set to auto_write.",
        setting=setting,
    )


def require_todoist_rail_live_write_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    decision = evaluate_todoist_rail_live_write_permission(connection)
    if not decision["allowed"]:
        raise TodoistRailPermissionDenied(decision["reason"])
    return decision


def _todoist_api_payload(task: Mapping[str, Any]) -> dict[str, Any]:
    """Build the POST /api/v1/tasks request body. Deliberately does not set project_id
    (so the task lands in Inbox/default), recurrence, subtasks, comments, or attachments."""
    payload: dict[str, Any] = {"content": task["task_title"]}
    if task["description"]:
        payload["description"] = task["description"]
    if task["labels"]:
        payload["labels"] = list(task["labels"])
    if task["due_date_or_due_string"]:
        payload["due_string"] = task["due_date_or_due_string"]
    payload["priority"] = task["priority"]
    return payload


def _persist_live_write_idempotency_record(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    task: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert the row gate 2's `get_idempotency_record` lookup will find on retry.

    Mirrors the check-then-insert shape of `side_effects.create_external_write_intent_record`
    (same `idempotency_records` table, same columns), but inserts ONLY into
    `idempotency_records` rather than also creating an `external_write_intents` row:
    that table's schema (migrations/00011_side_effect_idempotency_ledger_tables.sql)
    hard-CHECKs `live_write = 0` and `no_external_writes = 1`, so it structurally
    cannot represent a real live write and is out of scope to alter here.
    `idempotency_records.status` carries the same CHECK-constrained enum; the closest
    existing member for a completed external action is "completed_simulated" (the
    same value `side_effects._intent_status_after_attempt` returns for a successful
    non-dry-run attempt) -- adding a dedicated "completed_live" enum member would
    require a migration change, out of this packet's scope.
    """
    now = _utc_now()
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
            VALUES (?, 'todoist', 'create', ?, ?, ?, ?, ?, ?, 'completed_simulated', NULL, NULL)
            """,
            (
                idempotency_key,
                task["source_type"],
                task["source_id"],
                task["dedupe_key"],
                payload_fingerprint(_idempotency_payload(task)),
                now,
                now,
            ),
        )
    return get_idempotency_record(connection, idempotency_key)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _idempotency_payload(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_title": task["task_title"],
        "description": task["description"],
        "labels": list(task["labels"]),
        "due_date_or_due_string": task["due_date_or_due_string"],
        "priority": task["priority"],
    }


def _permission_decision(
    *,
    allowed: bool,
    mode: str | None,
    reason: str,
    setting: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": TODOIST_RAIL_LIVE_WRITE_PERMISSION,
        "mode": mode,
        "reason": reason,
        "setting": setting,
    }


def _refusal(
    *,
    status: str,
    reason: str,
    gate_failed: str,
    task: Mapping[str, Any],
    permission: Mapping[str, Any],
    idempotency_key: str | None = None,
    existing_idempotency_record: Mapping[str, Any] | None = None,
    rail_state: str | None = None,
    credential_env_var: str | None = None,
    credential_present: bool | None = None,
    credential_values_read: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "gate_failed": gate_failed,
        "dry_run": False,
        "no_send": True,
        "external_mutation": False,
        "todoist_task_created": False,
        "would_write": dict(task),
        "permission": dict(permission),
        "idempotency_key": idempotency_key,
        "existing_idempotency_record": (
            dict(existing_idempotency_record) if existing_idempotency_record is not None else None
        ),
        "rail_state": rail_state,
        "credential_env_var": credential_env_var,
        "credential_present": credential_present,
        "client_result": None,
        "safety_assertions": {
            "credential_values_read": credential_values_read,
            "credential_values_logged": False,
            "network_called": False,
            "external_mutation": False,
            "max_one_task_create": True,
            "gate_failed": gate_failed,
        },
    }

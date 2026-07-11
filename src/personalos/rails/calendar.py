"""Live Google Calendar rail adapter (P-RAIL-CAL-01) — inert until a future G5 packet.

This module is the ONE place in the codebase allowed to make a genuine HTTPS call to
Google's OAuth token endpoint or the Calendar API. `create_live_calendar_event` is the
sole public entry point and it enforces the same fixed gating order from
docs/ARCHITECTURE.md invariant #3 that `rails.todoist.create_live_todoist_task` and
`rails.gmail.send_live_gmail_message` enforce:

    permission -> ledger/dedupe -> rail-state -> credentials

Any gate left unsatisfied is a hard stop: the function returns a structured refusal
(never a silent no-op, never a raised exception) and no HTTPS client is ever
constructed. Today RAIL_STATES["calendar"] is "inert" (status.py), so the rail-state
gate always fails closed in real usage; flipping that rail live is a separate,
G5-gated packet, not this one.

Unlike Todoist (one HTTP call, one secret) or Gmail (one SMTP call, two secrets),
a live Calendar write is a TWO-CALL flow against THREE secrets:

  (a) POST https://oauth2.googleapis.com/token (form-encoded: client_id,
      client_secret, refresh_token, grant_type=refresh_token) -> a short-lived
      access_token.
  (b) POST https://www.googleapis.com/calendar/v3/calendars/<calendarId>/events
      (JSON, Authorization: Bearer <access_token>) -> the created event.

This packet assumes a valid refresh token already exists in the host environment by
the time the live path would ever run (which it won't, since the rail stays inert).
It builds the refresh-and-call mechanics that CONSUME an existing refresh token; the
one-time interactive OAuth consent flow that produces that refresh token is Chris's
own action, entirely outside this packet and outside what an agent can do.

Call (a) failing (expired/revoked refresh token, malformed token response, transport
error) must NEVER be treated the same as call (b) failing (event-creation rejected,
transport error after a valid access token). These are different failure classes with
different implications -- a failed refresh means no external state changed and no
credential was even proven to work; a failed create means the credential chain was
valid but the specific write did not land -- so `create_live_calendar_event` keeps them
in separate `token_refresh_result` / `event_create_result` fields and uses distinct
`STATUS_TOKEN_REFRESH_FAILED` / `STATUS_EVENT_CREATE_FAILED` status values. Call (b) is
only ever attempted after call (a) reports success; a failed refresh short-circuits
before `GoogleCalendarClient.create_event` is invoked at all.

Idempotency persistence uses the exact same "persist only after a confirmed
successful client call" ordering as the Todoist and Gmail rails (the fix for the real
duplicate-send bug found on the first rail packet) -- see
`_persist_live_write_idempotency_record` below. Here "confirmed successful" means the
event-creation call (b) succeeded, not merely the token refresh (a).

Calendar-scoping (design decision, flag explicitly in review): a calendar event is
hard to fully undo -- it can be deleted after creation, but an attendee/notification
recipient may already have seen it, which is the same one-way-door concern the Gmail
packet's recipient-scoping check exists for. This first inert adapter packet applies
the identical pattern: it does NOT accept an arbitrary `calendar_id` from the caller.
Instead it reads a single controlled calendar ID from
`PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID` and refuses (as a fifth, additional
safety check layered after the four fixed gates) if that env var is absent or empty,
or if the caller-supplied `calendar_id` does not exactly match it. Widening this to
arbitrary calendar IDs is out of scope for this packet and would need its own explicit
review, exactly like Gmail's recipient scoping.

Only `GoogleCalendarClient.refresh_access_token` / `.create_event` may raise on a
genuine transport failure, and only after every gate has passed; each is always
called through a try/except that converts any such failure into the same structured
shape the gates use.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from personalos.execution_rails import (
    generate_dedupe_key,
    stable_local_id,
    validate_required_text,
    validate_text,
    validate_timezone_aware_datetime,
)
from personalos.idempotency import generate_idempotency_key, payload_fingerprint
from personalos.permissions import evaluate_auto_write_gate
from personalos.side_effects import get_idempotency_record
from personalos.status import RAIL_STATES

CALENDAR_RAIL_LIVE_WRITE_PERMISSION = "calendar_rail_live_write"

# Phase D rail credentials -- new names, not reusing any retired Phase 14-C var (see
# .env.example: PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL was a single opaque
# marker, not real OAuth client material). Google's refresh-token flow needs THREE
# secrets, not one (Todoist) or two (Gmail app-password auth). Read via os.environ
# only; never hardcoded/logged.
CALENDAR_RAIL_CLIENT_ID_ENV_VAR = "PERSONALOS_RAIL_CALENDAR_CLIENT_ID"
CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR = "PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET"
CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR = "PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN"

# Additional safety rail beyond the four fixed gates (see module docstring
# "Calendar-scoping"): the only calendar ID this adapter will ever write to.
CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR = "PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID"

GOOGLE_OAUTH_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_ENDPOINT_TEMPLATE = (
    "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
)
CALENDAR_REQUEST_TIMEOUT_SECONDS = 10.0

STATUS_BLOCKED_PERMISSION = "calendar_rail_live_write_blocked_permission_denied"
STATUS_BLOCKED_DUPLICATE = "calendar_rail_live_write_blocked_duplicate_idempotency_key"
STATUS_BLOCKED_RAIL_STATE = "calendar_rail_live_write_blocked_rail_state_not_live"
STATUS_BLOCKED_CREDENTIAL_MISSING = "calendar_rail_live_write_blocked_credential_env_var_missing"
STATUS_BLOCKED_CREDENTIAL_EMPTY = "calendar_rail_live_write_blocked_credential_env_var_empty"
STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED = "calendar_rail_live_write_blocked_calendar_not_controlled"
STATUS_TOKEN_REFRESH_PASSED = "calendar_rail_live_write_token_refresh_passed"
STATUS_TOKEN_REFRESH_FAILED = "calendar_rail_live_write_token_refresh_failed"
STATUS_EVENT_CREATE_PASSED = "calendar_rail_live_write_event_create_passed"
STATUS_EVENT_CREATE_FAILED = "calendar_rail_live_write_event_create_failed"


class CalendarRailPermissionDenied(PermissionError):
    """Raised only by `require_calendar_rail_live_write_permission`, never by the gated entry point."""


class CalendarRailClientProtocol(Protocol):
    def refresh_access_token(self) -> dict[str, Any]:
        """Exchange the refresh token for a short-lived access token. Never raises."""

    def create_event(self, *, access_token: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Create exactly one calendar event using a previously obtained access token.

        Never raises; only called after `refresh_access_token` reports success.
        """


class GoogleCalendarClient:
    """Thin stdlib-only HTTPS client for the real Google OAuth token endpoint and
    Calendar API v3 events endpoint.

    Uses `urllib.request`/`urllib.error` only (no `google-auth`/`google-api-python-
    client`, no third-party HTTP library) so the manifest's network-primitive
    tripwire (RISK_REGISTER.md) has exactly one narrow, reviewed surface to watch --
    same discipline as `rails.todoist.TodoistRailClient`. `opener` is injectable so
    tests can exercise the real request-construction path for BOTH calls (endpoint,
    headers, body) without ever touching the network.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        calendar_id: str,
        token_endpoint: str = GOOGLE_OAUTH_TOKEN_ENDPOINT,
        events_endpoint_template: str = GOOGLE_CALENDAR_EVENTS_ENDPOINT_TEMPLATE,
        timeout_seconds: float = CALENDAR_REQUEST_TIMEOUT_SECONDS,
        opener: Any | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._events_endpoint = events_endpoint_template.format(calendar_id=calendar_id)
        self._token_endpoint = token_endpoint
        self._timeout_seconds = timeout_seconds
        self._opener = opener if opener is not None else urllib.request.urlopen

    def refresh_access_token(self) -> dict[str, Any]:
        form_body = urllib.parse.urlencode(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._token_endpoint,
            data=form_body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
                http_status = response.status if hasattr(response, "status") else response.getcode()
            parsed_body = json.loads(raw_body.decode("utf-8"))
            access_token = parsed_body.get("access_token")
            if not access_token:
                return {
                    "status": STATUS_TOKEN_REFRESH_FAILED,
                    "http_status": http_status,
                    "network_called": True,
                    "error_type": "MissingAccessToken",
                    "error_message": "Token endpoint response did not include an access_token.",
                }
            return {
                "status": STATUS_TOKEN_REFRESH_PASSED,
                "http_status": http_status,
                "network_called": True,
                "access_token": access_token,
                "expires_in": parsed_body.get("expires_in"),
            }
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return {
                "status": STATUS_TOKEN_REFRESH_FAILED,
                "network_called": True,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }

    def create_event(self, *, access_token: str, event: Mapping[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._events_endpoint,
            data=json.dumps(dict(event)).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
                http_status = response.status if hasattr(response, "status") else response.getcode()
            parsed_body = json.loads(raw_body.decode("utf-8"))
            return {
                "status": STATUS_EVENT_CREATE_PASSED,
                "http_status": http_status,
                "external_event_id": parsed_body.get("id"),
                "network_called": True,
                "external_mutation": True,
                "mutation_state": "confirmed_after_event_create_response",
            }
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return {
                "status": STATUS_EVENT_CREATE_FAILED,
                "network_called": True,
                "external_mutation": "unconfirmed",
                "mutation_state": "unconfirmed_after_event_create_attempt",
                "error_type": type(error).__name__,
                "error_message": str(error),
            }


def create_live_calendar_event(
    connection: sqlite3.Connection,
    *,
    source_type: str,
    source_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str,
    description: str = "",
    client: CalendarRailClientProtocol | None = None,
    client_id_env_var: str = CALENDAR_RAIL_CLIENT_ID_ENV_VAR,
    client_secret_env_var: str = CALENDAR_RAIL_CLIENT_SECRET_ENV_VAR,
    refresh_token_env_var: str = CALENDAR_RAIL_REFRESH_TOKEN_ENV_VAR,
    controlled_calendar_id_env_var: str = CALENDAR_RAIL_CONTROLLED_CALENDAR_ID_ENV_VAR,
    **_ignored: Any,
) -> dict[str, Any]:
    """Enforce all four fixed gates, in fixed order, plus the calendar-scoping safety
    check (see module docstring), then (only if every check passes) run the two-call
    token-refresh-then-create flow via `client` (or a real `GoogleCalendarClient` if
    omitted).

    Every path returns a structured dict with `status`, `reason`, `gate_failed`
    (None once every gate has passed), and a `safety_assertions` block. Nothing this
    function returns ever contains a credential value or the access token obtained
    from the token-refresh call.

    If the token-refresh call fails, `event_create_result` stays None and
    `create_event` is never invoked -- the two failure classes are never collapsed
    into one generic error (see module docstring).

    The idempotency record is persisted ONLY after `client.create_event` returns a
    confirmed-success result, mirroring `create_live_todoist_task` and
    `send_live_gmail_message` exactly.
    """
    event = _build_calendar_event_record(
        source_type=source_type,
        source_id=source_id,
        summary=summary,
        description=description,
        start_time=start_time,
        end_time=end_time,
        calendar_id=calendar_id,
    )

    permission = evaluate_calendar_rail_live_write_permission(connection)
    if not permission["allowed"]:
        return _refusal(
            status=STATUS_BLOCKED_PERMISSION,
            reason=permission["reason"],
            gate_failed="permission",
            event=event,
            permission=permission,
        )

    idempotency_key = generate_idempotency_key(
        target_system="calendar",
        operation_type="create",
        source_type=event["source_type"],
        source_id=event["source_id"],
        dedupe_key=event["dedupe_key"],
        payload=_idempotency_payload(event),
    )
    existing_record = get_idempotency_record(connection, idempotency_key)
    if existing_record is not None:
        return _refusal(
            status=STATUS_BLOCKED_DUPLICATE,
            reason=(
                "An idempotency record already exists for this exact Calendar create "
                "intent; refusing to risk a duplicate live write."
            ),
            gate_failed="ledger_dedupe",
            event=event,
            permission=permission,
            idempotency_key=idempotency_key,
            existing_idempotency_record=existing_record,
        )

    rail_state = RAIL_STATES["calendar"]
    if rail_state != "live":
        return _refusal(
            status=STATUS_BLOCKED_RAIL_STATE,
            reason=f"Calendar rail state is '{rail_state}', not 'live'; refusing to call out.",
            gate_failed="rail_state",
            event=event,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
        )

    credential_env_vars = [client_id_env_var, client_secret_env_var, refresh_token_env_var]
    missing_credential_env_vars = [
        env_var for env_var in credential_env_vars if env_var not in os.environ
    ]
    if missing_credential_env_vars:
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_MISSING,
            reason=f"Credential env var(s) not set: {', '.join(missing_credential_env_vars)}",
            gate_failed="credentials",
            event=event,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=credential_env_vars,
            credential_present=False,
        )

    client_id_value = os.environ[client_id_env_var]
    client_secret_value = os.environ[client_secret_env_var]
    refresh_token_value = os.environ[refresh_token_env_var]
    credential_values_by_env_var = (
        (client_id_env_var, client_id_value),
        (client_secret_env_var, client_secret_value),
        (refresh_token_env_var, refresh_token_value),
    )
    empty_credential_env_vars = [
        env_var for env_var, value in credential_values_by_env_var if not value.strip()
    ]
    if empty_credential_env_vars:
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_EMPTY,
            reason=f"Credential env var(s) set but empty: {', '.join(empty_credential_env_vars)}",
            gate_failed="credentials",
            event=event,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=credential_env_vars,
            credential_present=True,
            credential_values_read=True,
        )

    controlled_calendar_id = os.environ.get(controlled_calendar_id_env_var, "")
    if not controlled_calendar_id.strip() or event["calendar_id"] != controlled_calendar_id:
        return _refusal(
            status=STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED,
            reason=(
                "Calendar ID is not the single controlled calendar configured via "
                f"{controlled_calendar_id_env_var}; refusing to write to an uncontrolled calendar."
            ),
            gate_failed="calendar_scoping",
            event=event,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=credential_env_vars,
            credential_present=True,
            credential_values_read=True,
        )

    selected_client = (
        client
        if client is not None
        else GoogleCalendarClient(
            client_id=client_id_value,
            client_secret=client_secret_value,
            refresh_token=refresh_token_value,
            calendar_id=event["calendar_id"],
        )
    )

    token_result = selected_client.refresh_access_token()
    redacted_token_result = _redact_token_result(token_result)
    if token_result["status"] != STATUS_TOKEN_REFRESH_PASSED:
        # Distinct failure class from event-creation failure: no external state
        # changed, and `create_event` is never invoked. See module docstring.
        return {
            "status": token_result["status"],
            "reason": (
                "Calendar rail token refresh failed; the event-creation call was "
                "never attempted. See token_refresh_result for the outcome."
            ),
            "gate_failed": None,
            "dry_run": False,
            "no_send": False,
            "external_mutation": False,
            "calendar_event_created": False,
            "would_write": event,
            "permission": permission,
            "idempotency_key": idempotency_key,
            "idempotency_record_persisted": False,
            "idempotency_record": None,
            "rail_state": rail_state,
            "credential_env_vars": credential_env_vars,
            "controlled_calendar_id_env_var": controlled_calendar_id_env_var,
            "token_refresh_result": redacted_token_result,
            "event_create_result": None,
            "event_create_attempted": False,
            "safety_assertions": {
                "credential_values_read": True,
                "credential_values_logged": False,
                "network_called": True,
                "external_mutation": False,
                "max_one_event_create": True,
                "calendar_is_controlled": True,
                "gate_failed": None,
            },
        }

    access_token = token_result["access_token"]
    event_create_result = selected_client.create_event(
        access_token=access_token,
        event=_google_calendar_event_payload(event),
    )

    idempotency_record_persisted = False
    persisted_idempotency_record = None
    if event_create_result["status"] == STATUS_EVENT_CREATE_PASSED:
        # Persist the dedupe record ONLY once the live create is confirmed to have
        # succeeded, so that an immediate identical-input retry hits gate 2 above and
        # refuses, instead of repeating the live write -- same discipline as
        # rails.todoist / rails.gmail. A failed/uncertain event_create_result leaves
        # no record behind, so a genuinely transient failure can still be retried.
        persisted_idempotency_record = _persist_live_write_idempotency_record(
            connection,
            idempotency_key=idempotency_key,
            event=event,
        )
        idempotency_record_persisted = True

    return {
        "status": event_create_result["status"],
        "reason": (
            "Calendar rail token refresh succeeded and the event-creation call was "
            "attempted; see event_create_result for the outcome."
        ),
        "gate_failed": None,
        "dry_run": False,
        "no_send": False,
        "external_mutation": event_create_result.get("external_mutation", False),
        "calendar_event_created": event_create_result["status"] == STATUS_EVENT_CREATE_PASSED,
        "would_write": event,
        "permission": permission,
        "idempotency_key": idempotency_key,
        "idempotency_record_persisted": idempotency_record_persisted,
        "idempotency_record": persisted_idempotency_record,
        "rail_state": rail_state,
        "credential_env_vars": credential_env_vars,
        "controlled_calendar_id_env_var": controlled_calendar_id_env_var,
        "token_refresh_result": redacted_token_result,
        "event_create_result": event_create_result,
        "event_create_attempted": True,
        "safety_assertions": {
            "credential_values_read": True,
            "credential_values_logged": False,
            "network_called": True,
            "external_mutation": event_create_result.get("external_mutation", False),
            "max_one_event_create": True,
            "calendar_is_controlled": True,
            "gate_failed": None,
        },
    }


def evaluate_calendar_rail_live_write_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    return evaluate_auto_write_gate(
        connection,
        category=CALENDAR_RAIL_LIVE_WRITE_PERMISSION,
        missing_reason=lambda: f"Missing permission setting: {CALENDAR_RAIL_LIVE_WRITE_PERMISSION}",
        invalid_reason=lambda raw_mode: f"Invalid permission mode: {raw_mode}",
        not_auto_write_reason=lambda mode_value: (
            f"Calendar live-write rail permission is not auto_write "
            f"(any other rail's or module's permission being enabled does not "
            f"count): {mode_value}"
        ),
        success_reason="Calendar live-write rail permission is explicitly set to auto_write.",
    )


def require_calendar_rail_live_write_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    decision = evaluate_calendar_rail_live_write_permission(connection)
    if not decision["allowed"]:
        raise CalendarRailPermissionDenied(decision["reason"])
    return decision


def _build_calendar_event_record(
    *,
    source_type: str,
    source_id: str,
    summary: str,
    description: str,
    start_time: str,
    end_time: str,
    calendar_id: str,
) -> dict[str, Any]:
    source_type = validate_required_text("source_type", source_type)
    source_id = validate_required_text("source_id", source_id)
    summary = validate_required_text("summary", summary)
    description = validate_text("description", description)
    calendar_id = validate_required_text("calendar_id", calendar_id)
    start = validate_timezone_aware_datetime("start_time", start_time)
    end = validate_timezone_aware_datetime("end_time", end_time)
    if end <= start:
        raise ValueError("end_time must be after start_time")
    dedupe_key = generate_dedupe_key(
        module_name="calendar",
        object_type="event",
        source_type=source_type,
        source_id=source_id,
        title=summary,
        scheduled_marker=start_time,
    )
    return {
        "calendar_event_id": stable_local_id("calendar-event", dedupe_key),
        "source_type": source_type,
        "source_id": source_id,
        "summary": summary,
        "description": description,
        "start_time": start_time,
        "end_time": end_time,
        "calendar_id": calendar_id,
        "dedupe_key": dedupe_key,
        "created_at_utc": _utc_now(),
    }


def _google_calendar_event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Build the POST .../events request body. Deliberately does not set attendees,
    recurrence, reminders, or conferencing -- summary/start/end/description only."""
    payload: dict[str, Any] = {
        "summary": event["summary"],
        "start": {"dateTime": event["start_time"]},
        "end": {"dateTime": event["end_time"]},
    }
    if event["description"]:
        payload["description"] = event["description"]
    return payload


def _redact_token_result(token_result: Mapping[str, Any]) -> dict[str, Any]:
    """Strip the access token before it can ever reach a returned/serialized result."""
    redacted = {key: value for key, value in token_result.items() if key != "access_token"}
    redacted["access_token_obtained"] = "access_token" in token_result
    return redacted


def _persist_live_write_idempotency_record(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    event: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert the row gate 2's `get_idempotency_record` lookup will find on retry.

    Mirrors `rails.todoist._persist_live_write_idempotency_record` and
    `rails.gmail._persist_live_write_idempotency_record` exactly (same
    `idempotency_records` table, same columns, same closest-existing-enum-member
    choice `'completed_simulated'` for a completed live action -- dedicating a
    `'completed_live'` enum member would need a migration change, out of this
    packet's scope). Called only after a confirmed successful `client.create_event`
    result, exactly like the other two rails.
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
            VALUES (?, 'calendar', 'create', ?, ?, ?, ?, ?, ?, 'completed_simulated', NULL, NULL)
            """,
            (
                idempotency_key,
                event["source_type"],
                event["source_id"],
                event["dedupe_key"],
                payload_fingerprint(_idempotency_payload(event)),
                now,
                now,
            ),
        )
    return get_idempotency_record(connection, idempotency_key)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _idempotency_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "summary": event["summary"],
        "description": event["description"],
        "start_time": event["start_time"],
        "end_time": event["end_time"],
        "calendar_id": event["calendar_id"],
    }


def _refusal(
    *,
    status: str,
    reason: str,
    gate_failed: str,
    event: Mapping[str, Any],
    permission: Mapping[str, Any],
    idempotency_key: str | None = None,
    existing_idempotency_record: Mapping[str, Any] | None = None,
    rail_state: str | None = None,
    credential_env_vars: list[str] | None = None,
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
        "calendar_event_created": False,
        "would_write": dict(event),
        "permission": dict(permission),
        "idempotency_key": idempotency_key,
        "existing_idempotency_record": (
            dict(existing_idempotency_record) if existing_idempotency_record is not None else None
        ),
        "rail_state": rail_state,
        "credential_env_vars": credential_env_vars,
        "credential_present": credential_present,
        "controlled_calendar_id_env_var": None,
        "token_refresh_result": None,
        "event_create_result": None,
        "event_create_attempted": False,
        "safety_assertions": {
            "credential_values_read": credential_values_read,
            "credential_values_logged": False,
            "network_called": False,
            "external_mutation": False,
            "max_one_event_create": True,
            "calendar_is_controlled": gate_failed != "calendar_scoping",
            "gate_failed": gate_failed,
        },
    }

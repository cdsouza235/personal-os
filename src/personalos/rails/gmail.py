"""Live Gmail rail adapter (P-RAIL-GM-01) — inert until P-RAIL-GM-02 (G5) flips it.

This module is the ONE place in the codebase allowed to make a genuine SMTP call to
Gmail. `send_live_gmail_message` is the sole public entry point and it enforces the
same fixed gating order from docs/ARCHITECTURE.md invariant #3 that
`rails.todoist.create_live_todoist_task` enforces:

    permission -> ledger/dedupe -> rail-state -> credentials

Any gate left unsatisfied is a hard stop: the function returns a structured refusal
(never a silent no-op, never a raised exception) and the live SMTP client is never
constructed. Today RAIL_STATES["gmail"] is "inert" (status.py), so the rail-state
gate always fails closed in real usage; flipping that rail live is a separate,
G5-gated packet (P-RAIL-GM-02), not this one.

Email is IRREVERSIBLE (worse than Todoist's task-creation, which can at least be
manually deleted after the fact): once sent, a message cannot be unsent. Two things
follow from that, beyond mirroring the four fixed gates:

  1. Idempotency persistence uses the exact same "persist only after a confirmed
     successful client call" ordering as `rails.todoist.create_live_todoist_task`
     (the fix for the real duplicate-send bug GLM found on that packet) — see
     `_persist_live_write_idempotency_record` below.
  2. The recipient is NOT an arbitrary caller-supplied address. `send_live_gmail_
     message` only ever sends to a single controlled recipient, resolved from an
     env var at call time (mirroring the deleted Phase 14-C reference's
     `PHASE14C_GMAIL_CONTROLLED_RECIPIENT` self-send model) — see the module
     docstring section "Recipient scoping" below.

Recipient scoping (design decision, flag explicitly in review): this first inert
adapter packet does not accept an arbitrary `to_address` from the caller. Instead it
reads a single controlled recipient from `GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR`
and refuses (as a fifth, additional safety check layered after the four fixed gates)
if that env var is absent or empty, or if the caller supplies a `to_address` that
does not exactly match it. This is deliberately more restrictive than Todoist's
adapter (which has no equivalent recipient-scoping concept) because a stray outbound
email to an uncontrolled address cannot be recalled. Widening this to arbitrary
recipients is out of scope for this packet and would need its own explicit review.

Only `GmailSmtpClient.send_message` may raise on a genuine transport failure, and
only after every gate has passed; it is always called through a try/except that
converts any such failure into the same structured shape the gates use.
"""

from __future__ import annotations

import os
import smtplib
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any, Protocol

from personalos.execution_rails import (
    generate_dedupe_key,
    stable_local_id,
    validate_required_text,
    validate_text,
)
from personalos.idempotency import generate_idempotency_key, payload_fingerprint
from personalos.permissions import evaluate_auto_write_gate
from personalos.side_effects import get_idempotency_record
from personalos.status import RAIL_STATES

GMAIL_RAIL_LIVE_SEND_PERMISSION = "gmail_rail_live_send"

# Phase D rail credentials (deliberately new names, not the retired Phase 14-C
# `PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS`/`PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD`
# vars from .env.example — same "don't reuse a retired module's var name"
# discipline as the Todoist rail's PERSONALOS_RAIL_TODOIST_TOKEN. Unlike Todoist,
# Gmail SMTP auth needs TWO secrets, not one: the sender address and its app
# password (Gmail app-password auth, not OAuth — confirmed by the Phase 14-C
# reference). Documenting the chosen names here since .env.example itself is out
# of scope for this packet:
#   PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS
#   PERSONALOS_RAIL_GMAIL_APP_PASSWORD
GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR = "PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS"
GMAIL_RAIL_APP_PASSWORD_ENV_VAR = "PERSONALOS_RAIL_GMAIL_APP_PASSWORD"

# Additional safety rail beyond the four fixed gates (see module docstring
# "Recipient scoping"): the only address this adapter will ever send to. Also a
# new name, not the retired Phase 14-C `PHASE14C_GMAIL_CONTROLLED_RECIPIENT`.
GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR = "PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT"

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465
GMAIL_SMTP_TIMEOUT_SECONDS = 10.0

STATUS_BLOCKED_PERMISSION = "gmail_rail_live_send_blocked_permission_denied"
STATUS_BLOCKED_DUPLICATE = "gmail_rail_live_send_blocked_duplicate_idempotency_key"
STATUS_BLOCKED_RAIL_STATE = "gmail_rail_live_send_blocked_rail_state_not_live"
STATUS_BLOCKED_CREDENTIAL_MISSING = "gmail_rail_live_send_blocked_credential_env_var_missing"
STATUS_BLOCKED_CREDENTIAL_EMPTY = "gmail_rail_live_send_blocked_credential_env_var_empty"
STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED = "gmail_rail_live_send_blocked_recipient_not_controlled"
STATUS_CLIENT_CALL_PASSED = "gmail_rail_live_send_client_call_passed"
STATUS_CLIENT_CALL_FAILED = "gmail_rail_live_send_client_call_failed"


class GmailRailPermissionDenied(PermissionError):
    """Raised only by `require_gmail_rail_live_send_permission`, never by the gated entry point."""


class GmailClientProtocol(Protocol):
    def send_message(
        self, *, sender: str, to_address: str, subject: str, body: str
    ) -> dict[str, Any]:
        """Send exactly one email. Returns a structured result, never raises on failure."""


class GmailSmtpClient:
    """Thin stdlib-only SMTP client for the real Gmail SMTP endpoint.

    Uses `smtplib.SMTP_SSL` only (no third-party library, no OAuth library) so the
    manifest's network-primitive tripwire (RISK_REGISTER.md) has exactly one narrow,
    reviewed surface to watch — same discipline as `rails.todoist.TodoistRailClient`'s
    `urllib`-only HTTPS surface. `smtp_factory` is injectable so tests can exercise
    the real message-construction and login/send call sequence without ever touching
    the network.
    """

    def __init__(
        self,
        *,
        app_password: str,
        host: str = GMAIL_SMTP_HOST,
        port: int = GMAIL_SMTP_PORT,
        timeout_seconds: float = GMAIL_SMTP_TIMEOUT_SECONDS,
        smtp_factory: Any | None = None,
    ) -> None:
        self._app_password = app_password
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._smtp_factory = smtp_factory if smtp_factory is not None else smtplib.SMTP_SSL

    def send_message(
        self, *, sender: str, to_address: str, subject: str, body: str
    ) -> dict[str, Any]:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        try:
            with self._smtp_factory(self._host, self._port, timeout=self._timeout_seconds) as smtp:
                smtp.login(sender, self._app_password)
                send_errors = smtp.send_message(message)
            return {
                "status": STATUS_CLIENT_CALL_PASSED,
                "network_called": True,
                "external_mutation": True,
                "mutation_state": "confirmed_after_send_message_call",
                "send_errors": dict(send_errors) if send_errors else {},
            }
        except (OSError, smtplib.SMTPException) as error:
            return {
                "status": STATUS_CLIENT_CALL_FAILED,
                "network_called": True,
                "external_mutation": "unconfirmed",
                "mutation_state": "unconfirmed_after_send_message_attempt",
                "error_type": type(error).__name__,
                "error_message": str(error),
            }


def send_live_gmail_message(
    connection: sqlite3.Connection,
    *,
    source_type: str,
    source_id: str,
    subject: str,
    body: str,
    to_address: str,
    client: GmailClientProtocol | None = None,
    sender_env_var: str = GMAIL_RAIL_SENDER_ADDRESS_ENV_VAR,
    app_password_env_var: str = GMAIL_RAIL_APP_PASSWORD_ENV_VAR,
    controlled_recipient_env_var: str = GMAIL_RAIL_CONTROLLED_RECIPIENT_ENV_VAR,
    **_ignored: Any,
) -> dict[str, Any]:
    """Enforce all four fixed gates, in fixed order, plus the recipient-scoping
    safety check (see module docstring), then (only if every check passes) send
    exactly one email via `client` (or a real `GmailSmtpClient` if omitted).

    Every path returns a structured dict with `status`, `reason`, `gate_failed`
    (None once every gate has passed), and a `safety_assertions` block. Nothing
    this function returns ever contains a credential value.

    The idempotency record is persisted ONLY after `client.send_message` returns a
    confirmed-success result, mirroring `create_live_todoist_task` exactly (the fix
    for a real bug: persisting before the call, or unconditionally after it, would
    let an immediate identical-input retry either wrongly block a genuinely
    transient failure or -- worse, given email is irreversible -- risk a second
    live send).
    """
    message = _build_gmail_message_record(
        source_type=source_type,
        source_id=source_id,
        subject=subject,
        body=body,
        to_address=to_address,
    )

    permission = evaluate_gmail_rail_live_send_permission(connection)
    if not permission["allowed"]:
        return _refusal(
            status=STATUS_BLOCKED_PERMISSION,
            reason=permission["reason"],
            gate_failed="permission",
            message=message,
            permission=permission,
        )

    idempotency_key = generate_idempotency_key(
        target_system="gmail",
        operation_type="send",
        source_type=message["source_type"],
        source_id=message["source_id"],
        dedupe_key=message["dedupe_key"],
        payload=_idempotency_payload(message),
    )
    existing_record = get_idempotency_record(connection, idempotency_key)
    if existing_record is not None:
        return _refusal(
            status=STATUS_BLOCKED_DUPLICATE,
            reason=(
                "An idempotency record already exists for this exact Gmail send "
                "intent; refusing to risk a duplicate live send."
            ),
            gate_failed="ledger_dedupe",
            message=message,
            permission=permission,
            idempotency_key=idempotency_key,
            existing_idempotency_record=existing_record,
        )

    rail_state = RAIL_STATES["gmail"]
    if rail_state != "live":
        return _refusal(
            status=STATUS_BLOCKED_RAIL_STATE,
            reason=f"Gmail rail state is '{rail_state}', not 'live'; refusing to call out.",
            gate_failed="rail_state",
            message=message,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
        )

    missing_credential_env_vars = [
        env_var
        for env_var in (sender_env_var, app_password_env_var)
        if env_var not in os.environ
    ]
    if missing_credential_env_vars:
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_MISSING,
            reason=f"Credential env var(s) not set: {', '.join(missing_credential_env_vars)}",
            gate_failed="credentials",
            message=message,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=[sender_env_var, app_password_env_var],
            credential_present=False,
        )

    sender_address = os.environ[sender_env_var]
    app_password = os.environ[app_password_env_var]
    credential_values_by_env_var = (
        (sender_env_var, sender_address),
        (app_password_env_var, app_password),
    )
    empty_credential_env_vars = [
        env_var for env_var, value in credential_values_by_env_var if not value.strip()
    ]
    if empty_credential_env_vars:
        return _refusal(
            status=STATUS_BLOCKED_CREDENTIAL_EMPTY,
            reason=f"Credential env var(s) set but empty: {', '.join(empty_credential_env_vars)}",
            gate_failed="credentials",
            message=message,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=[sender_env_var, app_password_env_var],
            credential_present=True,
            credential_values_read=True,
        )

    controlled_recipient = os.environ.get(controlled_recipient_env_var, "")
    if not controlled_recipient.strip() or message["to_address"] != controlled_recipient:
        return _refusal(
            status=STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED,
            reason=(
                "Recipient is not the single controlled recipient configured via "
                f"{controlled_recipient_env_var}; refusing to send to an uncontrolled address."
            ),
            gate_failed="recipient_scoping",
            message=message,
            permission=permission,
            idempotency_key=idempotency_key,
            rail_state=rail_state,
            credential_env_vars=[sender_env_var, app_password_env_var],
            credential_present=True,
            credential_values_read=True,
        )

    selected_client = (
        client if client is not None else GmailSmtpClient(app_password=app_password)
    )
    client_result = selected_client.send_message(
        sender=sender_address,
        to_address=message["to_address"],
        subject=message["subject"],
        body=message["body"],
    )

    idempotency_record_persisted = False
    persisted_idempotency_record = None
    if client_result["status"] == STATUS_CLIENT_CALL_PASSED:
        # Persist the dedupe record ONLY once the live send is confirmed to have
        # succeeded, so that an immediate identical-input retry hits gate 2 above
        # and refuses, instead of repeating the live send (the exact hazard the
        # dedupe gate exists to prevent -- see rails.todoist's identical pattern
        # and the bug it fixed). A failed/uncertain client_result leaves no record
        # behind, so a genuinely transient failure can still be retried.
        persisted_idempotency_record = _persist_live_write_idempotency_record(
            connection,
            idempotency_key=idempotency_key,
            message=message,
        )
        idempotency_record_persisted = True

    return {
        "status": client_result["status"],
        "reason": (
            "Gmail rail client call attempted after every gate and safety check "
            "passed; see client_result for the outcome."
        ),
        "gate_failed": None,
        "dry_run": False,
        "no_send": False,
        "external_mutation": client_result.get("external_mutation", False),
        "gmail_message_sent": client_result["status"] == STATUS_CLIENT_CALL_PASSED,
        "would_write": message,
        "permission": permission,
        "idempotency_key": idempotency_key,
        "idempotency_record_persisted": idempotency_record_persisted,
        "idempotency_record": persisted_idempotency_record,
        "rail_state": rail_state,
        "credential_env_vars": [sender_env_var, app_password_env_var],
        "sender_address": sender_address,
        "client_result": client_result,
        "safety_assertions": {
            "credential_values_read": True,
            "credential_values_logged": False,
            "network_called": client_result.get("network_called", True),
            "external_mutation": client_result.get("external_mutation", False),
            "max_one_message_send": True,
            "recipient_is_controlled": True,
            "gate_failed": None,
        },
    }


def evaluate_gmail_rail_live_send_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    return evaluate_auto_write_gate(
        connection,
        category=GMAIL_RAIL_LIVE_SEND_PERMISSION,
        missing_reason=lambda: f"Missing permission setting: {GMAIL_RAIL_LIVE_SEND_PERMISSION}",
        invalid_reason=lambda raw_mode: f"Invalid permission mode: {raw_mode}",
        not_auto_write_reason=lambda mode_value: (
            f"Gmail live-send rail permission is not auto_write "
            f"(any other rail's or module's permission being enabled does not "
            f"count): {mode_value}"
        ),
        success_reason="Gmail live-send rail permission is explicitly set to auto_write.",
    )


def require_gmail_rail_live_send_permission(connection: sqlite3.Connection) -> dict[str, Any]:
    decision = evaluate_gmail_rail_live_send_permission(connection)
    if not decision["allowed"]:
        raise GmailRailPermissionDenied(decision["reason"])
    return decision


def _build_gmail_message_record(
    *,
    source_type: str,
    source_id: str,
    subject: str,
    body: str,
    to_address: str,
) -> dict[str, Any]:
    source_type = validate_required_text("source_type", source_type)
    source_id = validate_required_text("source_id", source_id)
    subject = validate_required_text("subject", subject)
    body = validate_text("body", body)
    # Deliberately `validate_text` (allows empty), not `validate_required_text`: an
    # empty/unresolved to_address must surface as the recipient_scoping gate's own
    # structured refusal below, not as an uncaught ValueError here -- this function is
    # the sole authority on whether a recipient is acceptable, including "absent".
    to_address = validate_text("to_address", to_address)
    dedupe_key = generate_dedupe_key(
        module_name="gmail",
        object_type="message",
        source_type=source_type,
        source_id=source_id,
        title=subject,
        scheduled_marker=to_address or "(unresolved-recipient)",
    )
    return {
        "gmail_message_id": stable_local_id("gmail-message", dedupe_key),
        "source_type": source_type,
        "source_id": source_id,
        "subject": subject,
        "body": body,
        "to_address": to_address,
        "dedupe_key": dedupe_key,
        "created_at_utc": _utc_now(),
    }


def _persist_live_write_idempotency_record(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    message: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert the row gate 2's `get_idempotency_record` lookup will find on retry.

    Mirrors `rails.todoist._persist_live_write_idempotency_record`'s check-then-insert
    shape (same `idempotency_records` table, same columns), for the same reason: the
    `external_write_intents` table (migrations/00011_side_effect_idempotency_ledger_
    tables.sql) hard-CHECKs `live_write = 0` and `no_external_writes = 1`, so it
    structurally cannot represent a real live send and is out of scope to alter here.
    `status` uses the same closest-existing-enum-member choice as the Todoist rail,
    `'completed_simulated'` (dedicating a `'completed_live'` enum member would need a
    migration change, out of this packet's scope). Called only after a confirmed
    successful `client.send_message` result, exactly like the Todoist rail.
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
            VALUES (?, 'gmail', 'send', ?, ?, ?, ?, ?, ?, 'completed_simulated', NULL, NULL)
            """,
            (
                idempotency_key,
                message["source_type"],
                message["source_id"],
                message["dedupe_key"],
                payload_fingerprint(_idempotency_payload(message)),
                now,
                now,
            ),
        )
    return get_idempotency_record(connection, idempotency_key)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _idempotency_payload(message: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "subject": message["subject"],
        "body": message["body"],
        "to_address": message["to_address"],
    }


def _refusal(
    *,
    status: str,
    reason: str,
    gate_failed: str,
    message: Mapping[str, Any],
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
        "gmail_message_sent": False,
        "would_write": dict(message),
        "permission": dict(permission),
        "idempotency_key": idempotency_key,
        "existing_idempotency_record": (
            dict(existing_idempotency_record) if existing_idempotency_record is not None else None
        ),
        "rail_state": rail_state,
        "credential_env_vars": credential_env_vars,
        "credential_present": credential_present,
        "client_result": None,
        "safety_assertions": {
            "credential_values_read": credential_values_read,
            "credential_values_logged": False,
            "network_called": False,
            "external_mutation": False,
            "max_one_message_send": True,
            "recipient_is_controlled": gate_failed != "recipient_scoping",
            "gate_failed": gate_failed,
        },
    }

"""Bounded Gmail SMTP self-send smoke client for Phase 14-C."""

from __future__ import annotations

import smtplib
import time
from collections.abc import Callable, Iterable, Mapping
from email.message import EmailMessage
from typing import Any

from personalos.phase14c_safety_utils import (
    config_names_only,
    optional_email,
    optional_string,
)

PHASE14C_GMAIL_SMOKE_SCHEMA_VERSION = "personal_os_phase14c_gmail_smoke.v1"
PHASE14C_GMAIL_SMTP_ADDRESS_CONFIG_NAME = "PERSONALOS_PHASE14C_GMAIL_SMTP_ADDRESS"
PHASE14C_GMAIL_APP_PASSWORD_CONFIG_NAME = "PERSONALOS_PHASE14C_GMAIL_APP_PASSWORD"
PHASE14C_GMAIL_CONTROLLED_RECIPIENT_CONFIG_NAME = (
    "PHASE14C_GMAIL_CONTROLLED_RECIPIENT"
)
PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES = (
    PHASE14C_GMAIL_SMTP_ADDRESS_CONFIG_NAME,
    PHASE14C_GMAIL_APP_PASSWORD_CONFIG_NAME,
    PHASE14C_GMAIL_CONTROLLED_RECIPIENT_CONFIG_NAME,
)
PHASE14C_GMAIL_SMOKE_SUBJECT = (
    "[Phase 14-C Test] Clean Kitchen Countertops and Stovetop"
)
PHASE14C_GMAIL_SMOKE_BODY = (
    "This is a bounded Phase 14-C supervised Gmail SMTP self-send smoke test. "
    "It is limited to one controlled test email, with no CC, BCC, attachments, "
    "forwarding, or reply to an existing thread."
)

GMAIL_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG = (
    "gmail_not_run_missing_execute_live_flag"
)
GMAIL_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE = (
    "gmail_not_run_missing_approval_reference"
)
GMAIL_SMOKE_NOT_RUN_MISSING_CONFIG = "gmail_not_run_missing_required_config_names"
GMAIL_SMOKE_NOT_RUN_MISSING_SENDER_OR_RECIPIENT = (
    "gmail_not_run_missing_sender_or_controlled_recipient"
)
GMAIL_SMOKE_PASSED = "gmail_self_send_smoke_passed"
GMAIL_SMOKE_FAILED = "gmail_self_send_smoke_failed"

class GmailSmtpSmokeClient:
    """Minimal Gmail SMTP client for exactly one Phase 14-C test email."""

    def __init__(
        self,
        *,
        sender_email: str,
        app_password: str,
        host: str = "smtp.gmail.com",
        port: int = 465,
        timeout_seconds: float = 10.0,
        smtp_factory: Callable[..., Any] = smtplib.SMTP_SSL,
    ) -> None:
        self._sender_email = sender_email
        self._app_password = app_password
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._smtp_factory = smtp_factory

    def send_email(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        message = EmailMessage()
        message["Subject"] = str(payload["subject"])
        message["From"] = str(payload["from"])
        message["To"] = str(payload["to"])
        message.set_content(str(payload["body"]))
        with self._smtp_factory(
            self._host,
            self._port,
            timeout=self._timeout_seconds,
        ) as smtp:
            smtp.login(self._sender_email, self._app_password)
            smtp.send_message(message)
        return {"provider": "gmail_smtp", "message_accepted": True}


def run_phase14c_gmail_smtp_smoke(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    execute_live: bool = False,
    approval_reference: str | None = None,
    sender_email: str | None = None,
    app_password: str | None = None,
    controlled_recipient: str | None = None,
    client: GmailSmtpSmokeClient | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Run or report readiness for the one-email Gmail SMTP smoke rail."""

    preflight = _gmail_config_preflight(available_config_names)
    sender = optional_email(sender_email)
    recipient = optional_email(controlled_recipient) or sender
    payload = (
        build_phase14c_gmail_email_payload(
            sender_email=sender,
            recipient_email=recipient,
        )
        if sender and recipient
        else None
    )
    base = {
        "schema_version": PHASE14C_GMAIL_SMOKE_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "rail": "gmail",
        "client_type": "gmail_smtp_app_password",
        "title": PHASE14C_GMAIL_SMOKE_SUBJECT,
        "live_execution_requested": execute_live,
        "approval_reference_present": bool(optional_string(approval_reference)),
        "config_preflight": preflight,
        "sender_masked": _mask_email(sender),
        "recipient_masked": _mask_email(recipient),
        "recipient_source": (
            "controlled_recipient_config" if optional_email(controlled_recipient)
            else "smtp_sender_self"
        ),
        "self_send": (
            _normalize_email(sender) == _normalize_email(recipient)
            if sender and recipient
            else False
        ),
        "email_payload_summary": {
            "subject": PHASE14C_GMAIL_SMOKE_SUBJECT,
            "body_contains_bounded_phase14c_notice": True,
            "to_count": 1 if recipient else 0,
            "cc_count": 0,
            "bcc_count": 0,
            "attachments": 0,
            "thread_id": None,
            "reply_to_existing_thread": False,
            "forward_existing_thread": False,
        },
        "call_limits": {
            "max_email_sends": 1,
            "email_send_calls": 0,
        },
        "mutation_state": "not_attempted",
        "safety_assertions": _gmail_safety_assertions(
            credential_values_read=False,
            external_mutation=False,
            gmail_email_sent=False,
            live_client_initialized=False,
        ),
    }
    if not execute_live:
        return {
            **base,
            "status": GMAIL_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG,
            "gmail_email_sent": False,
        }
    if not base["approval_reference_present"]:
        return {
            **base,
            "status": GMAIL_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
            "gmail_email_sent": False,
        }
    if preflight["missing_config_entry_names"]:
        return {
            **base,
            "status": GMAIL_SMOKE_NOT_RUN_MISSING_CONFIG,
            "gmail_email_sent": False,
        }
    app_password_value = optional_string(app_password)
    if sender is None or recipient is None or app_password_value is None:
        return {
            **base,
            "status": GMAIL_SMOKE_NOT_RUN_MISSING_SENDER_OR_RECIPIENT,
            "gmail_email_sent": False,
            "safety_assertions": _gmail_safety_assertions(
                credential_values_read=True,
                external_mutation=False,
                gmail_email_sent=False,
                live_client_initialized=False,
            ),
        }

    live_client = client or GmailSmtpSmokeClient(
        sender_email=sender,
        app_password=app_password_value,
    )
    started = time.monotonic()
    try:
        assert payload is not None
        send_result = dict(live_client.send_email(payload))
    except (OSError, smtplib.SMTPException, ValueError) as error:
        return {
            **base,
            "status": GMAIL_SMOKE_FAILED,
            "gmail_email_sent": None,
            "mutation_state": "unconfirmed_after_send_attempt",
            "failure": _safe_failure(error),
            "call_limits": {
                "max_email_sends": 1,
                "email_send_calls": 1,
            },
            "safety_assertions": _gmail_safety_assertions(
                credential_values_read=True,
                external_mutation=None,
                gmail_email_sent=None,
                live_client_initialized=True,
            ),
        }

    return {
        **base,
        "status": GMAIL_SMOKE_PASSED,
        "gmail_email_sent": True,
        "external_mutation": True,
        "mutation_state": "confirmed_email_sent",
        "send_result": _sanitize_send_result(send_result),
        "call_limits": {
            "max_email_sends": 1,
            "email_send_calls": 1,
        },
        "latency_ms": int((time.monotonic() - started) * 1000),
        "safety_assertions": _gmail_safety_assertions(
            credential_values_read=True,
            external_mutation=True,
            gmail_email_sent=True,
            live_client_initialized=True,
        ),
    }


def build_phase14c_gmail_email_payload(
    *,
    sender_email: str,
    recipient_email: str,
) -> dict[str, Any]:
    """Return the exact one-email Gmail SMTP payload."""

    return {
        "from": sender_email,
        "to": recipient_email,
        "subject": PHASE14C_GMAIL_SMOKE_SUBJECT,
        "body": PHASE14C_GMAIL_SMOKE_BODY,
        "cc": [],
        "bcc": [],
        "attachments": [],
        "thread_id": None,
        "reply_to_existing_thread": False,
        "forward_existing_thread": False,
    }


def _gmail_config_preflight(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    names = set(config_names_only(available_config_names))
    missing = [
        name for name in PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES if name not in names
    ]
    return {
        "required_config_entry_count": len(PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES),
        "missing_config_entry_names": missing,
        "reports_missing_names_only": True,
        "available_config_entry_names_reported": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
    }


def _gmail_safety_assertions(
    *,
    credential_values_read: bool,
    external_mutation: bool | None,
    gmail_email_sent: bool | None,
    live_client_initialized: bool,
) -> dict[str, bool | None]:
    return {
        "credential_values_read": credential_values_read,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
        "environment_dumped": False,
        "live_client_initialized": live_client_initialized,
        "external_mutation": external_mutation,
        "gmail_email_sent": gmail_email_sent,
        "max_one_email_send": True,
        "controlled_recipient_only": True,
        "cc_created": False,
        "bcc_created": False,
        "attachments_created": False,
        "reply_to_existing_thread": False,
        "forward_existing_thread": False,
        "production_db_active": False,
        "protected_paths_touched": False,
        "scheduler_activated": False,
    }


def _sanitize_send_result(result: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key in ("provider", "message_id"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            sanitized[key] = value.strip()
    accepted = result.get("message_accepted")
    if isinstance(accepted, bool):
        sanitized["message_accepted"] = accepted
    return sanitized


def _safe_failure(error: BaseException) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": "Gmail SMTP send attempt failed; details redacted.",
    }


def _normalize_email(value: str | None) -> str | None:
    return value.strip().lower() if isinstance(value, str) else None


def _mask_email(value: str | None) -> str | None:
    if value is None or "@" not in value:
        return None
    local, domain = value.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"

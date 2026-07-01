"""Gated connected live rehearsal runner for Phase 14-C."""

from __future__ import annotations

import json
import re
import smtplib
import time
import urllib.error
from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any, Protocol

from personalos.openclaw_model_strategy import (
    SMOKE_LANE,
    sanitize_openclaw_model_run_metadata,
)
from personalos.phase14c_connected_rehearsal import (
    PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_CONNECTED_REHEARSAL_DUE_DATE,
    PHASE14C_CONNECTED_REHEARSAL_MARKER,
    PHASE14C_CONNECTED_REHEARSAL_SCHEMA_VERSION,
)
from personalos.phase14c_gmail_live_smoke import (
    GmailSmtpSmokeClient,
    PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
)
from personalos.phase14c_todoist_live_smoke import (
    PHASE14C_TODOIST_TOKEN_CONFIG_NAME,
    TodoistRestSmokeClient,
)


CONNECTED_REHEARSAL_NOT_RUN_MISSING_EXECUTE_FLAG = (
    "phase14c_connected_rehearsal_not_run_missing_execute_live_flag"
)
CONNECTED_REHEARSAL_NOT_RUN_MISSING_APPROVAL_REFERENCE = (
    "phase14c_connected_rehearsal_not_run_missing_approval_reference"
)
CONNECTED_REHEARSAL_NOT_RUN_UNAPPROVED_REFERENCE = (
    "phase14c_connected_rehearsal_not_run_unapproved_reference"
)
CONNECTED_REHEARSAL_NOT_RUN_MISSING_CONFIG = (
    "phase14c_connected_rehearsal_not_run_missing_required_config_names"
)
CONNECTED_REHEARSAL_NOT_RUN_MISSING_VALUES = (
    "phase14c_connected_rehearsal_not_run_missing_config_values"
)
CONNECTED_REHEARSAL_NOT_RUN_PROVIDER_NOT_OPENROUTER = (
    "phase14c_connected_rehearsal_not_run_provider_not_openrouter"
)
CONNECTED_REHEARSAL_MODEL_FAILED = (
    "phase14c_connected_rehearsal_model_validation_failed"
)
CONNECTED_REHEARSAL_TODOIST_FAILED = "phase14c_connected_rehearsal_todoist_failed"
CONNECTED_REHEARSAL_GMAIL_FAILED = "phase14c_connected_rehearsal_gmail_failed"
CONNECTED_REHEARSAL_PASSED = "phase14c_connected_rehearsal_passed"

CONNECTED_REHEARSAL_PROMPT = (
    "Personal OS Phase 14-C connected rehearsal. Generate a bounded kitchen "
    "reset briefing for the marker "
    f"{PHASE14C_CONNECTED_REHEARSAL_MARKER}. Reply with exactly three short "
    "action bullets. Do not include personal data, links, file paths, account "
    "identifiers, credentials, or secrets."
)

CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES: tuple[str, ...] = (
    "PERSONALOS_OPENCLAW_MODEL_PROVIDER",
    "PERSONALOS_OPENCLAW_MODEL_API_KEY",
    "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
    "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
    PHASE14C_TODOIST_TOKEN_CONFIG_NAME,
    *PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORBIDDEN_BRIEF_FRAGMENTS = (
    "secret",
    "password",
    "token",
    "api key",
    "apikey",
    "/users/coldstake",
    ".env",
    "oauth",
)


class ConnectedModelClient(Protocol):
    def run_probe(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run one bounded model request."""


class ConnectedTodoistClient(Protocol):
    def create_task(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create one Todoist task."""


class ConnectedGmailClient(Protocol):
    def send_email(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Send one Gmail message."""


def run_phase14c_connected_rehearsal(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    execute_live: bool = False,
    approval_reference: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    nemotron_super_model: str | None = None,
    glm_5_2_model: str | None = None,
    todoist_token: str | None = None,
    gmail_sender_email: str | None = None,
    gmail_app_password: str | None = None,
    gmail_controlled_recipient: str | None = None,
    model_client: ConnectedModelClient | None = None,
    todoist_client: ConnectedTodoistClient | None = None,
    gmail_client: ConnectedGmailClient | None = None,
    source_date: date | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Run or gate the one connected model-to-task-to-email rehearsal."""

    preflight = _connected_config_preflight(available_config_names)
    due_date = _connected_due_date(source_date)
    base = {
        "schema_version": PHASE14C_CONNECTED_REHEARSAL_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "status": CONNECTED_REHEARSAL_NOT_RUN_MISSING_EXECUTE_FLAG,
        "rail": "connected_rehearsal",
        "marker": PHASE14C_CONNECTED_REHEARSAL_MARKER,
        "due_date": due_date,
        "live_execution_requested": execute_live,
        "approval_reference_required": PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
        "approval_reference_present": bool(_optional_string(approval_reference)),
        "approval_reference_matched": (
            _optional_string(approval_reference)
            == PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE
        ),
        "config_preflight": preflight,
        "sequence": ("openrouter", "todoist", "gmail"),
        "call_limits": _call_limits(),
        "model_brief_summary": _empty_brief_summary(),
        "todoist_task_created": False,
        "gmail_email_sent": False,
        "mutation_state": "not_attempted",
        "safety_assertions": _safety_assertions(
            credential_values_read=False,
            live_clients_initialized=False,
            model_provider_called=False,
            external_mutation=False,
            todoist_task_created=False,
            gmail_email_sent=False,
        ),
    }
    if not execute_live:
        return base
    if not base["approval_reference_present"]:
        return {**base, "status": CONNECTED_REHEARSAL_NOT_RUN_MISSING_APPROVAL_REFERENCE}
    if not base["approval_reference_matched"]:
        return {**base, "status": CONNECTED_REHEARSAL_NOT_RUN_UNAPPROVED_REFERENCE}
    if preflight["missing_config_entry_names"]:
        return {**base, "status": CONNECTED_REHEARSAL_NOT_RUN_MISSING_CONFIG}

    credential_values_read = True
    values = {
        "provider": _optional_string(provider),
        "api_key": _optional_string(api_key),
        "nemotron_super_model": _optional_string(nemotron_super_model),
        "glm_5_2_model": _optional_string(glm_5_2_model),
        "todoist_token": _optional_string(todoist_token),
        "gmail_sender_email": _optional_email(gmail_sender_email),
        "gmail_app_password": _optional_string(gmail_app_password),
        "gmail_controlled_recipient": _optional_email(gmail_controlled_recipient),
    }
    if any(value is None for value in values.values()):
        return {
            **base,
            "status": CONNECTED_REHEARSAL_NOT_RUN_MISSING_VALUES,
            "missing_config_value_count": sum(
                1 for value in values.values() if value is None
            ),
            "safety_assertions": _safety_assertions(
                credential_values_read=credential_values_read,
                live_clients_initialized=False,
                model_provider_called=False,
                external_mutation=False,
                todoist_task_created=False,
                gmail_email_sent=False,
            ),
        }
    if str(values["provider"]).lower() != "openrouter":
        return {
            **base,
            "status": CONNECTED_REHEARSAL_NOT_RUN_PROVIDER_NOT_OPENROUTER,
            "safety_assertions": _safety_assertions(
                credential_values_read=credential_values_read,
                live_clients_initialized=False,
                model_provider_called=False,
                external_mutation=False,
                todoist_task_created=False,
                gmail_email_sent=False,
            ),
        }

    live_model_client = model_client or _openrouter_client(
        api_key=str(values["api_key"]),
        nemotron_super_model=str(values["nemotron_super_model"]),
        glm_5_2_model=str(values["glm_5_2_model"]),
    )
    model_report, brief = _run_model_step(live_model_client)
    call_limits = {
        **_call_limits(),
        "openrouter_primary_calls": 1,
        "openrouter_fallback_calls": int(model_report["fallback_calls"]),
    }
    if brief is None:
        return {
            **base,
            "status": CONNECTED_REHEARSAL_MODEL_FAILED,
            "call_limits": call_limits,
            "model": model_report,
            "model_brief_summary": _empty_brief_summary(),
            "safety_assertions": _safety_assertions(
                credential_values_read=credential_values_read,
                live_clients_initialized=True,
                model_provider_called=True,
                external_mutation=False,
                todoist_task_created=False,
                gmail_email_sent=False,
            ),
        }

    live_todoist_client = todoist_client or TodoistRestSmokeClient(
        token=str(values["todoist_token"])
    )
    try:
        todoist_result = dict(
            live_todoist_client.create_task(_todoist_payload(due_date=due_date))
        )
    except urllib.error.HTTPError as error:
        failure = _safe_failure(error)
        error.close()
        return _post_todoist_failure_report(
            base=base,
            call_limits=call_limits,
            model_report=model_report,
            brief=brief,
            failure=failure,
            credential_values_read=credential_values_read,
        )
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        return _post_todoist_failure_report(
            base=base,
            call_limits=call_limits,
            model_report=model_report,
            brief=brief,
            failure=_safe_failure(error),
            credential_values_read=credential_values_read,
        )

    live_gmail_client = gmail_client or GmailSmtpSmokeClient(
        sender_email=str(values["gmail_sender_email"]),
        app_password=str(values["gmail_app_password"]),
    )
    gmail_payload = _gmail_payload(
        sender_email=str(values["gmail_sender_email"]),
        recipient_email=str(values["gmail_controlled_recipient"]),
        brief=brief,
    )
    try:
        gmail_result = dict(live_gmail_client.send_email(gmail_payload))
    except (OSError, smtplib.SMTPException, ValueError) as error:
        return {
            **base,
            "status": CONNECTED_REHEARSAL_GMAIL_FAILED,
            "external_mutation": True,
            "external_writes": "todoist_task_created_gmail_send_attempted",
            "todoist_task_created": True,
            "gmail_email_sent": None,
            "mutation_state": "todoist_created_gmail_unconfirmed_after_send_attempt",
            "call_limits": {
                **call_limits,
                "todoist_task_create_calls": 1,
                "gmail_email_send_calls": 1,
            },
            "model": model_report,
            "model_brief_summary": _brief_summary(brief),
            "todoist_result": _sanitize_todoist_result(todoist_result),
            "gmail_failure": _safe_failure(error),
            "safety_assertions": _safety_assertions(
                credential_values_read=credential_values_read,
                live_clients_initialized=True,
                model_provider_called=True,
                external_mutation=True,
                todoist_task_created=True,
                gmail_email_sent=None,
            ),
        }

    return {
        **base,
        "status": CONNECTED_REHEARSAL_PASSED,
        "external_mutation": True,
        "external_writes": "todoist_task_created_gmail_email_sent",
        "todoist_task_created": True,
        "gmail_email_sent": True,
        "mutation_state": "confirmed_task_created_and_email_sent",
        "call_limits": {
            **call_limits,
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 1,
        },
        "model": model_report,
        "model_brief_summary": _brief_summary(brief),
        "todoist_result": _sanitize_todoist_result(todoist_result),
        "gmail_result": _sanitize_gmail_result(gmail_result),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=True,
            todoist_task_created=True,
            gmail_email_sent=True,
        ),
    }


def _openrouter_client(
    *,
    api_key: str,
    nemotron_super_model: str,
    glm_5_2_model: str,
) -> ConnectedModelClient:
    from personalos.openrouter_model_smoke_client import OpenRouterModelSmokeClient

    return OpenRouterModelSmokeClient(
        api_key=api_key,
        models_by_alias={
            "nemotron_super": nemotron_super_model,
            "glm_5_2": glm_5_2_model,
        },
    )


def _run_model_step(
    client: ConnectedModelClient,
) -> tuple[dict[str, Any], str | None]:
    attempts: list[dict[str, Any]] = []
    primary = _run_one_model_attempt(client=client, model_alias="nemotron_super")
    attempts.append(primary)
    selected = primary
    if primary["validation_passed"] is not True:
        fallback = _run_one_model_attempt(client=client, model_alias="glm_5_2")
        attempts.append(fallback)
        selected = fallback
    brief = selected["brief"] if selected["validation_passed"] is True else None
    safe_attempts = []
    for attempt in attempts:
        safe_attempts.append(
            {
                key: value
                for key, value in attempt.items()
                if key not in {"brief"}
            }
        )
    return (
        {
            "prompt_logged": False,
            "raw_provider_response_logged": False,
            "configured_model_ids_logged": False,
            "credential_values_logged": False,
            "primary_calls": 1,
            "fallback_calls": len(attempts) - 1,
            "attempts": safe_attempts,
            "selected_attempt": selected["attempt"],
            "selected_model_alias": selected["model_alias"],
            "selected_validation_passed": selected["validation_passed"],
        },
        brief,
    )


def _run_one_model_attempt(
    *,
    client: ConnectedModelClient,
    model_alias: str,
) -> dict[str, Any]:
    request = {
        "lane": SMOKE_LANE,
        "task_type": "connected_rehearsal_brief",
        "model_alias": model_alias,
        "prompt": CONNECTED_REHEARSAL_PROMPT,
        "max_output_tokens": 160,
    }
    started = time.monotonic()
    raw = dict(client.run_probe(request))
    brief = _validated_brief(raw.get("response_text"))
    metadata = sanitize_openclaw_model_run_metadata(
        {
            **raw,
            "model_alias": model_alias,
            "lane": SMOKE_LANE,
        }
    )
    return {
        "attempt": "primary" if model_alias == "nemotron_super" else "fallback",
        "model_alias": model_alias,
        "validation_passed": brief is not None and raw.get("success") is True,
        "metadata": metadata,
        "brief": brief,
        "latency_ms_observed": int((time.monotonic() - started) * 1000),
    }


def _validated_brief(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    lines = [line.strip(" -\t") for line in value.strip().splitlines()]
    cleaned = [line for line in lines if line]
    if not cleaned:
        return None
    selected = cleaned[:3]
    for line in selected:
        lowered = line.lower()
        if len(line) > 160 or any(fragment in lowered for fragment in _FORBIDDEN_BRIEF_FRAGMENTS):
            return None
        if "@" in line or "http://" in lowered or "https://" in lowered:
            return None
    return "\n".join(f"- {line}" for line in selected)


def _connected_due_date(source_date: date | None) -> str:
    if source_date is None:
        return PHASE14C_CONNECTED_REHEARSAL_DUE_DATE
    return PHASE14C_CONNECTED_REHEARSAL_DUE_DATE


def _todoist_payload(*, due_date: str) -> dict[str, Any]:
    return {
        "content": PHASE14C_CONNECTED_REHEARSAL_MARKER,
        "due_date": due_date,
    }


def _gmail_payload(
    *,
    sender_email: str,
    recipient_email: str,
    brief: str,
) -> dict[str, Any]:
    return {
        "from": sender_email,
        "to": recipient_email,
        "subject": PHASE14C_CONNECTED_REHEARSAL_MARKER,
        "body": (
            "This is a bounded Phase 14-C connected rehearsal email. "
            "It is limited to one controlled self-send, with no CC, BCC, "
            "attachments, forwarding, or reply to an existing thread.\n\n"
            f"Marker: {PHASE14C_CONNECTED_REHEARSAL_MARKER}\n\n"
            "Model-generated bounded test brief:\n"
            f"{brief}\n"
        ),
        "cc": [],
        "bcc": [],
        "attachments": [],
        "thread_id": None,
        "reply_to_existing_thread": False,
        "forward_existing_thread": False,
    }


def _post_todoist_failure_report(
    *,
    base: Mapping[str, Any],
    call_limits: Mapping[str, int],
    model_report: Mapping[str, Any],
    brief: str,
    failure: Mapping[str, Any],
    credential_values_read: bool,
) -> dict[str, Any]:
    return {
        **dict(base),
        "status": CONNECTED_REHEARSAL_TODOIST_FAILED,
        "external_mutation": None,
        "external_writes": "todoist_task_create_attempted",
        "todoist_task_created": None,
        "gmail_email_sent": False,
        "mutation_state": "unconfirmed_after_task_create_attempt",
        "call_limits": {
            **dict(call_limits),
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 0,
        },
        "model": dict(model_report),
        "model_brief_summary": _brief_summary(brief),
        "todoist_failure": dict(failure),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=None,
            todoist_task_created=None,
            gmail_email_sent=False,
        ),
    }


def _connected_config_preflight(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    names = set(_config_names_only(available_config_names))
    missing = tuple(
        name for name in CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES if name not in names
    )
    return {
        "required_config_entry_count": len(CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES),
        "missing_config_entry_names": list(missing),
        "reports_missing_names_only": True,
        "available_config_entry_names_reported": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
    }


def _call_limits() -> dict[str, int]:
    return {
        "max_openrouter_primary_calls": 1,
        "max_openrouter_fallback_calls": 1,
        "max_todoist_task_creates": 1,
        "max_gmail_email_sends": 1,
        "max_calendar_event_creates": 0,
        "max_protected_openclaw_runtime_invocations": 0,
        "openrouter_primary_calls": 0,
        "openrouter_fallback_calls": 0,
        "todoist_task_create_calls": 0,
        "gmail_email_send_calls": 0,
        "calendar_event_create_calls": 0,
        "protected_openclaw_runtime_invocation_calls": 0,
    }


def _brief_summary(brief: str) -> dict[str, Any]:
    lines = [line for line in brief.splitlines() if line.strip()]
    return {
        "brief_generated": True,
        "brief_line_count": len(lines),
        "brief_char_count": len(brief),
        "brief_text_logged": False,
        "raw_provider_response_logged": False,
    }


def _empty_brief_summary() -> dict[str, Any]:
    return {
        "brief_generated": False,
        "brief_line_count": 0,
        "brief_char_count": 0,
        "brief_text_logged": False,
        "raw_provider_response_logged": False,
    }


def _sanitize_todoist_result(result: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key in ("id", "url", "content"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            sanitized[key] = value.strip()
    due = result.get("due")
    if isinstance(due, Mapping):
        date_value = due.get("date")
        if isinstance(date_value, str) and date_value.strip():
            sanitized["due_date"] = date_value.strip()
    return sanitized


def _sanitize_gmail_result(result: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key in ("provider", "message_id"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            sanitized[key] = value.strip()
    accepted = result.get("message_accepted")
    if isinstance(accepted, bool):
        sanitized["message_accepted"] = accepted
    return sanitized


def _safe_failure(error: BaseException) -> dict[str, Any]:
    failure: dict[str, Any] = {
        "type": type(error).__name__,
        "message": "Connected rehearsal live step failed; details redacted.",
    }
    if isinstance(error, urllib.error.HTTPError):
        failure["http_status"] = int(error.code)
    return failure


def _safety_assertions(
    *,
    credential_values_read: bool,
    live_clients_initialized: bool,
    model_provider_called: bool,
    external_mutation: bool | None,
    todoist_task_created: bool | None,
    gmail_email_sent: bool | None,
) -> dict[str, bool | None]:
    return {
        "credential_values_read": credential_values_read,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
        "environment_dumped": False,
        "live_clients_initialized": live_clients_initialized,
        "model_provider_called": model_provider_called,
        "external_mutation": external_mutation,
        "todoist_task_created": todoist_task_created,
        "gmail_email_sent": gmail_email_sent,
        "calendar_event_created": False,
        "protected_openclaw_runtime_called": False,
        "scheduler_activated": False,
        "production_db_active": False,
        "protected_paths_touched": False,
        "dynamic_cleaning_started": False,
        "max_one_openrouter_primary_call": True,
        "max_one_openrouter_fallback_call": True,
        "max_one_todoist_task_create": True,
        "max_one_gmail_email_send": True,
    }


def _config_names_only(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> tuple[str, ...]:
    if isinstance(available_config_names, Mapping):
        return tuple(str(name) for name in available_config_names.keys())
    return tuple(str(name) for name in available_config_names)


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_email(value: object) -> str | None:
    text = _optional_string(value)
    if text is None or _EMAIL_RE.match(text) is None:
        return None
    return text

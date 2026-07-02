"""Gated wide-net rehearsal runner for Phase 14-C."""

from __future__ import annotations

import json
import smtplib
import time
import urllib.error
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Any, Protocol

from personalos.openclaw_model_strategy import (
    SMOKE_LANE,
    sanitize_openclaw_model_run_metadata,
)
from personalos.phase14c_gmail_live_smoke import (
    GmailSmtpSmokeClient,
    PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
)
from personalos.phase14c_todoist_live_smoke import (
    PHASE14C_TODOIST_TOKEN_CONFIG_NAME,
    TodoistRestSmokeClient,
    next_upcoming_monday,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
    PHASE14C_WIDE_NET_REHEARSAL_SCHEMA_VERSION,
)


WIDE_NET_NOT_RUN_MISSING_EXECUTE_FLAG = (
    "phase14c_wide_net_rehearsal_not_run_missing_execute_live_flag"
)
WIDE_NET_NOT_RUN_MISSING_APPROVAL_REFERENCE = (
    "phase14c_wide_net_rehearsal_not_run_missing_approval_reference"
)
WIDE_NET_NOT_RUN_UNAPPROVED_REFERENCE = (
    "phase14c_wide_net_rehearsal_not_run_unapproved_reference"
)
WIDE_NET_NOT_RUN_MISSING_CONFIG = (
    "phase14c_wide_net_rehearsal_not_run_missing_required_config_names"
)
WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT = (
    "phase14c_wide_net_rehearsal_not_run_missing_calendar_connector_or_client"
)
WIDE_NET_NOT_RUN_MISSING_VALUES = (
    "phase14c_wide_net_rehearsal_not_run_missing_config_values"
)
WIDE_NET_NOT_RUN_PROVIDER_NOT_OPENROUTER = (
    "phase14c_wide_net_rehearsal_not_run_provider_not_openrouter"
)
WIDE_NET_TODOIST_FAILED = "phase14c_wide_net_rehearsal_todoist_failed"
WIDE_NET_GMAIL_FAILED = "phase14c_wide_net_rehearsal_gmail_failed"
WIDE_NET_CALENDAR_FAILED = "phase14c_wide_net_rehearsal_calendar_failed"
WIDE_NET_PASSED = "phase14c_wide_net_rehearsal_passed"
WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE = (
    "phase14c_wide_net_rehearsal_passed_with_model_diagnostic_failure"
)

WIDE_NET_PROMPT = (
    "Personal OS Phase 14-C wide-net diagnostic. Reply exactly with "
    "PHASE14C_WIDE_NET_DIAGNOSTIC_OK. Do not include personal data, links, "
    "file paths, account identifiers, credentials, or secrets."
)
WIDE_NET_EXPECTED_MODEL_TEXT = "PHASE14C_WIDE_NET_DIAGNOSTIC_OK"
WIDE_NET_CALENDAR_TIMEZONE = "America/Chicago"
WIDE_NET_CALENDAR_START_LOCAL_TIME = datetime_time(hour=17, minute=0)
WIDE_NET_CALENDAR_DURATION_MINUTES = 15
WIDE_NET_CALENDAR_CONFIG_NAME = "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL"

WIDE_NET_REQUIRED_CONFIG_NAMES: tuple[str, ...] = (
    "PERSONALOS_OPENCLAW_MODEL_PROVIDER",
    "PERSONALOS_OPENCLAW_MODEL_API_KEY",
    "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
    "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
    PHASE14C_TODOIST_TOKEN_CONFIG_NAME,
    *PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
    WIDE_NET_CALENDAR_CONFIG_NAME,
)


class WideNetModelClient(Protocol):
    def run_probe(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run one bounded model request."""


class WideNetTodoistClient(Protocol):
    def create_task(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create one Todoist task."""


class WideNetGmailClient(Protocol):
    def send_email(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Send one Gmail message."""


class WideNetCalendarClient(Protocol):
    def create_event(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create one Calendar event."""


def run_phase14c_wide_net_rehearsal(
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
    calendar_connector_label: str | None = None,
    model_client: WideNetModelClient | None = None,
    todoist_client: WideNetTodoistClient | None = None,
    gmail_client: WideNetGmailClient | None = None,
    calendar_client: WideNetCalendarClient | None = None,
    source_date: date | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Run or gate the one wide-net rehearsal."""

    preflight = _wide_net_config_preflight(available_config_names)
    due_date = _wide_net_due_date(source_date)
    calendar_payload = _calendar_payload(source_date=source_date)
    base = {
        "schema_version": PHASE14C_WIDE_NET_REHEARSAL_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "status": WIDE_NET_NOT_RUN_MISSING_EXECUTE_FLAG,
        "rail": "wide_net_rehearsal",
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "due_date": due_date,
        "calendar_connector_payload": _redacted_calendar_payload(calendar_payload),
        "live_execution_requested": execute_live,
        "approval_reference_required": PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
        "approval_reference_present": bool(_optional_string(approval_reference)),
        "approval_reference_matched": (
            _optional_string(approval_reference)
            == PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE
        ),
        "config_preflight": preflight,
        "calendar_client_available": calendar_client is not None,
        "sequence": ("openrouter", "todoist", "gmail", "google_calendar"),
        "call_limits": _call_limits(),
        "model_diagnostic": _empty_model_diagnostic(),
        "todoist_task_created": False,
        "gmail_email_sent": False,
        "calendar_event_created": False,
        "mutation_state": "not_attempted",
        "safety_assertions": _safety_assertions(
            credential_values_read=False,
            live_clients_initialized=False,
            model_provider_called=False,
            external_mutation=False,
            todoist_task_created=False,
            gmail_email_sent=False,
            calendar_event_created=False,
        ),
    }
    if not execute_live:
        return base
    if not base["approval_reference_present"]:
        return {**base, "status": WIDE_NET_NOT_RUN_MISSING_APPROVAL_REFERENCE}
    if not base["approval_reference_matched"]:
        return {**base, "status": WIDE_NET_NOT_RUN_UNAPPROVED_REFERENCE}
    if preflight["missing_config_entry_names"]:
        return {**base, "status": WIDE_NET_NOT_RUN_MISSING_CONFIG}
    if calendar_client is None:
        return {**base, "status": WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT}

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
        "calendar_connector_label": _optional_string(calendar_connector_label),
    }
    if any(value is None for value in values.values()):
        return {
            **base,
            "status": WIDE_NET_NOT_RUN_MISSING_VALUES,
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
                calendar_event_created=False,
            ),
        }
    if str(values["provider"]).lower() != "openrouter":
        return {
            **base,
            "status": WIDE_NET_NOT_RUN_PROVIDER_NOT_OPENROUTER,
            "safety_assertions": _safety_assertions(
                credential_values_read=credential_values_read,
                live_clients_initialized=False,
                model_provider_called=False,
                external_mutation=False,
                todoist_task_created=False,
                gmail_email_sent=False,
                calendar_event_created=False,
            ),
        }

    live_model_client = model_client or _openrouter_client(
        api_key=str(values["api_key"]),
        nemotron_super_model=str(values["nemotron_super_model"]),
        glm_5_2_model=str(values["glm_5_2_model"]),
    )
    model_report = _run_model_diagnostic(live_model_client)
    call_limits = {
        **_call_limits(),
        "openrouter_primary_calls": 1,
        "openrouter_fallback_calls": int(model_report["fallback_calls"]),
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
            failure=failure,
            credential_values_read=credential_values_read,
        )
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        return _post_todoist_failure_report(
            base=base,
            call_limits=call_limits,
            model_report=model_report,
            failure=_safe_failure(error),
            credential_values_read=credential_values_read,
        )

    live_gmail_client = gmail_client or GmailSmtpSmokeClient(
        sender_email=str(values["gmail_sender_email"]),
        app_password=str(values["gmail_app_password"]),
    )
    try:
        gmail_result = dict(
            live_gmail_client.send_email(
                _gmail_payload(
                    sender_email=str(values["gmail_sender_email"]),
                    recipient_email=str(values["gmail_controlled_recipient"]),
                )
            )
        )
    except (OSError, smtplib.SMTPException, ValueError) as error:
        return _post_gmail_failure_report(
            base=base,
            call_limits=call_limits,
            model_report=model_report,
            todoist_result=todoist_result,
            failure=_safe_failure(error),
            credential_values_read=credential_values_read,
        )

    try:
        calendar_result = dict(calendar_client.create_event(calendar_payload))
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        return _post_calendar_failure_report(
            base=base,
            call_limits=call_limits,
            model_report=model_report,
            todoist_result=todoist_result,
            gmail_result=gmail_result,
            failure=_safe_failure(error),
            credential_values_read=credential_values_read,
        )

    model_passed = model_report["selected_validation_passed"] is True
    return {
        **base,
        "status": WIDE_NET_PASSED
        if model_passed
        else WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
        "external_mutation": True,
        "external_writes": "todoist_task_created_gmail_email_sent_calendar_event_created",
        "todoist_task_created": True,
        "gmail_email_sent": True,
        "calendar_event_created": True,
        "mutation_state": "confirmed_task_email_and_calendar_event_created",
        "call_limits": {
            **call_limits,
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 1,
            "calendar_event_create_calls": 1,
        },
        "model_diagnostic": model_report,
        "todoist_result": _sanitize_todoist_result(todoist_result),
        "gmail_result": _sanitize_gmail_result(gmail_result),
        "calendar_result": _sanitize_calendar_result(calendar_result),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=True,
            todoist_task_created=True,
            gmail_email_sent=True,
            calendar_event_created=True,
        ),
    }


def _openrouter_client(
    *,
    api_key: str,
    nemotron_super_model: str,
    glm_5_2_model: str,
) -> WideNetModelClient:
    from personalos.openrouter_model_smoke_client import OpenRouterModelSmokeClient

    return OpenRouterModelSmokeClient(
        api_key=api_key,
        models_by_alias={
            "nemotron_super": nemotron_super_model,
            "glm_5_2": glm_5_2_model,
        },
    )


def _run_model_diagnostic(client: WideNetModelClient) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    primary = _run_one_model_attempt(client=client, model_alias="nemotron_super")
    attempts.append(primary)
    selected = primary
    if primary["validation_passed"] is not True:
        fallback = _run_one_model_attempt(client=client, model_alias="glm_5_2")
        attempts.append(fallback)
        selected = fallback
    return {
        "diagnostic_only": True,
        "model_output_drives_external_writes": False,
        "prompt_logged": False,
        "raw_provider_response_logged": False,
        "generated_model_text_logged": False,
        "configured_model_ids_logged": False,
        "credential_values_logged": False,
        "primary_calls": 1,
        "fallback_calls": len(attempts) - 1,
        "attempts": attempts,
        "selected_attempt": selected["attempt"],
        "selected_model_alias": selected["model_alias"],
        "selected_validation_passed": selected["validation_passed"],
    }


def _run_one_model_attempt(
    *,
    client: WideNetModelClient,
    model_alias: str,
) -> dict[str, Any]:
    request = {
        "lane": SMOKE_LANE,
        "task_type": "wide_net_diagnostic_probe",
        "model_alias": model_alias,
        "prompt": WIDE_NET_PROMPT,
        "max_output_tokens": 48,
    }
    started = time.monotonic()
    raw = dict(client.run_probe(request))
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
        "validation_passed": _model_text_passed(raw.get("response_text"))
        and raw.get("success") is True,
        "metadata": metadata,
        "latency_ms_observed": int((time.monotonic() - started) * 1000),
    }


def _model_text_passed(value: object) -> bool:
    return isinstance(value, str) and value.strip() == WIDE_NET_EXPECTED_MODEL_TEXT


def _wide_net_due_date(source_date: date | None) -> str:
    today = source_date or date.today()
    return next_upcoming_monday(today).isoformat()


def _calendar_date(source_date: date | None) -> date:
    today = source_date or date.today()
    return next_upcoming_monday(today)


def _todoist_payload(*, due_date: str) -> dict[str, Any]:
    return {
        "content": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "due_date": due_date,
    }


def _gmail_payload(*, sender_email: str, recipient_email: str) -> dict[str, Any]:
    return {
        "from": sender_email,
        "to": recipient_email,
        "subject": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "body": (
            "This is a bounded Phase 14-C wide-net rehearsal email. "
            "It is limited to one controlled self-send, with no CC, BCC, "
            "attachments, forwarding, or reply to an existing thread.\n\n"
            f"Marker: {PHASE14C_WIDE_NET_REHEARSAL_MARKER}\n\n"
            "The model probe for this run is diagnostic-only; model-generated "
            "text is not used for this email."
        ),
        "cc": [],
        "bcc": [],
        "attachments": [],
        "thread_id": None,
        "reply_to_existing_thread": False,
        "forward_existing_thread": False,
    }


def _calendar_payload(*, source_date: date | None) -> dict[str, Any]:
    event_date = _calendar_date(source_date)
    start = datetime.combine(event_date, WIDE_NET_CALENDAR_START_LOCAL_TIME)
    end = start + timedelta(minutes=WIDE_NET_CALENDAR_DURATION_MINUTES)
    return {
        "calendar_id": "primary",
        "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "start_time": start.isoformat(timespec="seconds"),
        "end_time": end.isoformat(timespec="seconds"),
        "timezone_str": WIDE_NET_CALENDAR_TIMEZONE,
        "attendees": [],
        "add_google_meet": False,
        "recurrence": None,
        "attachments": [],
        "description": (
            "Bounded Phase 14-C wide-net rehearsal marker. Self-only event; "
            "no attendees, recurrence, conference link, or attachments."
        ),
    }


def _redacted_calendar_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "calendar_id": payload.get("calendar_id"),
        "title": payload.get("title"),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "timezone_str": payload.get("timezone_str"),
        "attendee_count": len(_string_list(payload.get("attendees"))),
        "add_google_meet": payload.get("add_google_meet") is True,
        "recurrence_present": payload.get("recurrence") is not None,
        "attachment_count": len(_string_list(payload.get("attachments"))),
    }


def _post_todoist_failure_report(
    *,
    base: Mapping[str, Any],
    call_limits: Mapping[str, int],
    model_report: Mapping[str, Any],
    failure: Mapping[str, Any],
    credential_values_read: bool,
) -> dict[str, Any]:
    return {
        **dict(base),
        "status": WIDE_NET_TODOIST_FAILED,
        "external_mutation": None,
        "external_writes": "todoist_task_create_attempted",
        "todoist_task_created": None,
        "gmail_email_sent": False,
        "calendar_event_created": False,
        "mutation_state": "unconfirmed_after_task_create_attempt",
        "call_limits": {
            **dict(call_limits),
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 0,
            "calendar_event_create_calls": 0,
        },
        "model_diagnostic": dict(model_report),
        "todoist_failure": dict(failure),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=None,
            todoist_task_created=None,
            gmail_email_sent=False,
            calendar_event_created=False,
        ),
    }


def _post_gmail_failure_report(
    *,
    base: Mapping[str, Any],
    call_limits: Mapping[str, int],
    model_report: Mapping[str, Any],
    todoist_result: Mapping[str, Any],
    failure: Mapping[str, Any],
    credential_values_read: bool,
) -> dict[str, Any]:
    return {
        **dict(base),
        "status": WIDE_NET_GMAIL_FAILED,
        "external_mutation": True,
        "external_writes": "todoist_task_created_gmail_send_attempted",
        "todoist_task_created": True,
        "gmail_email_sent": None,
        "calendar_event_created": False,
        "mutation_state": "task_created_gmail_unconfirmed_after_send_attempt",
        "call_limits": {
            **dict(call_limits),
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 1,
            "calendar_event_create_calls": 0,
        },
        "model_diagnostic": dict(model_report),
        "todoist_result": _sanitize_todoist_result(todoist_result),
        "gmail_failure": dict(failure),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=True,
            todoist_task_created=True,
            gmail_email_sent=None,
            calendar_event_created=False,
        ),
    }


def _post_calendar_failure_report(
    *,
    base: Mapping[str, Any],
    call_limits: Mapping[str, int],
    model_report: Mapping[str, Any],
    todoist_result: Mapping[str, Any],
    gmail_result: Mapping[str, Any],
    failure: Mapping[str, Any],
    credential_values_read: bool,
) -> dict[str, Any]:
    return {
        **dict(base),
        "status": WIDE_NET_CALENDAR_FAILED,
        "external_mutation": True,
        "external_writes": "todoist_task_created_gmail_sent_calendar_create_attempted",
        "todoist_task_created": True,
        "gmail_email_sent": True,
        "calendar_event_created": None,
        "mutation_state": "task_created_email_sent_calendar_unconfirmed_after_create_attempt",
        "call_limits": {
            **dict(call_limits),
            "todoist_task_create_calls": 1,
            "gmail_email_send_calls": 1,
            "calendar_event_create_calls": 1,
        },
        "model_diagnostic": dict(model_report),
        "todoist_result": _sanitize_todoist_result(todoist_result),
        "gmail_result": _sanitize_gmail_result(gmail_result),
        "calendar_failure": dict(failure),
        "safety_assertions": _safety_assertions(
            credential_values_read=credential_values_read,
            live_clients_initialized=True,
            model_provider_called=True,
            external_mutation=True,
            todoist_task_created=True,
            gmail_email_sent=True,
            calendar_event_created=None,
        ),
    }


def _wide_net_config_preflight(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    names = set(_config_names_only(available_config_names))
    missing = tuple(name for name in WIDE_NET_REQUIRED_CONFIG_NAMES if name not in names)
    return {
        "required_config_entry_count": len(WIDE_NET_REQUIRED_CONFIG_NAMES),
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
        "max_calendar_event_creates": 1,
        "max_protected_openclaw_runtime_invocations": 0,
        "openrouter_primary_calls": 0,
        "openrouter_fallback_calls": 0,
        "todoist_task_create_calls": 0,
        "gmail_email_send_calls": 0,
        "calendar_event_create_calls": 0,
        "protected_openclaw_runtime_invocation_calls": 0,
    }


def _empty_model_diagnostic() -> dict[str, Any]:
    return {
        "diagnostic_only": True,
        "model_output_drives_external_writes": False,
        "prompt_logged": False,
        "raw_provider_response_logged": False,
        "generated_model_text_logged": False,
        "configured_model_ids_logged": False,
        "credential_values_logged": False,
        "primary_calls": 0,
        "fallback_calls": 0,
        "attempts": [],
        "selected_attempt": None,
        "selected_model_alias": None,
        "selected_validation_passed": False,
    }


def _sanitize_todoist_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in ("id", "content")
        if key in result and isinstance(result[key], str)
    }


def _sanitize_gmail_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in ("provider", "message_id", "message_accepted")
        if key in result and isinstance(result[key], str | bool)
    }


def _sanitize_calendar_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in ("id", "event_id", "status")
        if key in result and isinstance(result[key], str | bool)
    }


def _safe_failure(error: BaseException) -> dict[str, Any]:
    return {
        "type": error.__class__.__name__,
        "message": "Phase 14-C wide-net live attempt failed; details redacted.",
    }


def _safety_assertions(
    *,
    credential_values_read: bool,
    live_clients_initialized: bool,
    model_provider_called: bool,
    external_mutation: bool | None,
    todoist_task_created: bool | None,
    gmail_email_sent: bool | None,
    calendar_event_created: bool | None,
) -> dict[str, Any]:
    return {
        "credential_values_read": credential_values_read,
        "credential_values_logged": False,
        "credential_values_committed": False,
        "environment_dumped": False,
        "live_clients_initialized": live_clients_initialized,
        "model_provider_called": model_provider_called,
        "external_mutation": external_mutation,
        "todoist_task_created": todoist_task_created,
        "gmail_email_sent": gmail_email_sent,
        "calendar_event_created": calendar_event_created,
        "protected_openclaw_runtime_called": False,
        "scheduler_or_background_activated": False,
        "production_db_active": False,
        "protected_paths_touched": False,
        "dynamic_cleaning_triggered": False,
        "broad_live_activation": False,
    }


def _config_names_only(values: Iterable[str] | Mapping[str, Any]) -> tuple[str, ...]:
    if isinstance(values, Mapping):
        return tuple(str(name) for name in values.keys())
    return tuple(str(name) for name in values)


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_email(value: object) -> str | None:
    candidate = _optional_string(value)
    if candidate is None or "@" not in candidate or " " in candidate:
        return None
    return candidate


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, str))

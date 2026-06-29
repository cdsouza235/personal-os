"""Bounded Todoist Inbox/default smoke client for Phase 14-C."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from datetime import date, timedelta
from typing import Any


PHASE14C_TODOIST_SMOKE_SCHEMA_VERSION = "personal_os_phase14c_todoist_smoke.v1"
PHASE14C_TODOIST_TOKEN_CONFIG_NAME = "PERSONALOS_PHASE14C_TODOIST_TOKEN"
PHASE14C_TODOIST_TASK_TITLE = "[Phase 14-C Test] Clean Kitchen Countertops and Stovetop"
PHASE14C_TODOIST_API_ENDPOINT = "https://api.todoist.com/api/v1/tasks"

TODOIST_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG = (
    "todoist_not_run_missing_execute_live_flag"
)
TODOIST_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE = (
    "todoist_not_run_missing_approval_reference"
)
TODOIST_SMOKE_NOT_RUN_MISSING_CONFIG = "todoist_not_run_missing_required_config_names"
TODOIST_SMOKE_PASSED = "todoist_inbox_default_task_smoke_passed"
TODOIST_SMOKE_FAILED = "todoist_inbox_default_task_smoke_failed"


class TodoistRestSmokeClient:
    """Minimal Todoist REST client for exactly one Inbox task smoke write."""

    def __init__(
        self,
        *,
        token: str,
        endpoint: str = PHASE14C_TODOIST_API_ENDPOINT,
        timeout_seconds: float = 10.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._token = token
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def create_task(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps(dict(payload)).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with self._opener(request, timeout=self._timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
        if not response_body.strip():
            return {}
        parsed = json.loads(response_body)
        if not isinstance(parsed, Mapping):
            raise ValueError("Todoist create task response was not a JSON object.")
        return parsed


def run_phase14c_todoist_inbox_smoke(
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    execute_live: bool = False,
    approval_reference: str | None = None,
    token: str | None = None,
    client: TodoistRestSmokeClient | None = None,
    source_date: date | None = None,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Run or report readiness for the one-task Todoist smoke rail.

    The default path is report-only and does not read credential values. The
    live path must be explicitly requested and supplied a token by the caller.
    """

    due_date = next_upcoming_monday(source_date or date.today())
    payload = build_phase14c_todoist_task_payload(due_date=due_date)
    preflight = _todoist_config_preflight(available_config_names)
    base = {
        "schema_version": PHASE14C_TODOIST_SMOKE_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "rail": "todoist",
        "target": "inbox_default",
        "title": PHASE14C_TODOIST_TASK_TITLE,
        "due_date": due_date.isoformat(),
        "live_execution_requested": execute_live,
        "approval_reference_present": bool(_optional_string(approval_reference)),
        "config_preflight": preflight,
        "task_payload_summary": {
            "content": PHASE14C_TODOIST_TASK_TITLE,
            "due_date": due_date.isoformat(),
            "project_id_omitted_for_inbox_default": True,
            "recurrence": None,
            "subtasks": 0,
            "labels": [],
            "comments": 0,
            "attachments": 0,
        },
        "call_limits": {
            "max_task_creates": 1,
            "task_create_calls": 0,
        },
        "safety_assertions": _todoist_safety_assertions(
            credential_values_read=False,
            external_mutation=False,
            live_client_initialized=False,
        ),
    }
    if not execute_live:
        return {
            **base,
            "status": TODOIST_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG,
            "todoist_task_created": False,
        }
    if not base["approval_reference_present"]:
        return {
            **base,
            "status": TODOIST_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
            "todoist_task_created": False,
        }
    if preflight["missing_config_entry_names"]:
        return {
            **base,
            "status": TODOIST_SMOKE_NOT_RUN_MISSING_CONFIG,
            "todoist_task_created": False,
        }
    token_value = _optional_string(token)
    if token_value is None and client is None:
        return {
            **base,
            "status": TODOIST_SMOKE_NOT_RUN_MISSING_CONFIG,
            "todoist_task_created": False,
            "safety_assertions": _todoist_safety_assertions(
                credential_values_read=True,
                external_mutation=False,
                live_client_initialized=False,
            ),
        }

    live_client = client or TodoistRestSmokeClient(token=token_value or "")
    started = time.monotonic()
    try:
        response = dict(live_client.create_task(payload))
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        return {
            **base,
            "status": TODOIST_SMOKE_FAILED,
            "todoist_task_created": False,
            "failure": _safe_failure(error),
            "call_limits": {
                "max_task_creates": 1,
                "task_create_calls": 1,
            },
            "safety_assertions": _todoist_safety_assertions(
                credential_values_read=True,
                external_mutation=False,
                live_client_initialized=True,
            ),
        }

    return {
        **base,
        "status": TODOIST_SMOKE_PASSED,
        "todoist_task_created": True,
        "external_mutation": True,
        "task_result": _sanitize_todoist_task_response(response),
        "call_limits": {
            "max_task_creates": 1,
            "task_create_calls": 1,
        },
        "latency_ms": int((time.monotonic() - started) * 1000),
        "safety_assertions": _todoist_safety_assertions(
            credential_values_read=True,
            external_mutation=True,
            live_client_initialized=True,
        ),
    }


def build_phase14c_todoist_task_payload(*, due_date: date) -> dict[str, Any]:
    """Return the exact one-task Todoist payload for Inbox/default."""

    return {
        "content": PHASE14C_TODOIST_TASK_TITLE,
        "due_date": due_date.isoformat(),
    }


def next_upcoming_monday(source_date: date) -> date:
    """Return the next Monday strictly after source_date."""

    days_ahead = (0 - source_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return source_date + timedelta(days=days_ahead)


def _todoist_config_preflight(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    names = set(_config_names_only(available_config_names))
    missing = (
        []
        if PHASE14C_TODOIST_TOKEN_CONFIG_NAME in names
        else [PHASE14C_TODOIST_TOKEN_CONFIG_NAME]
    )
    return {
        "required_config_entry_count": 1,
        "missing_config_entry_names": missing,
        "reports_missing_names_only": True,
        "available_config_entry_names_reported": False,
        "credential_values_read": False,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
    }


def _sanitize_todoist_task_response(response: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key in ("id", "url", "content"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            sanitized[key] = value.strip()
    due = response.get("due")
    if isinstance(due, Mapping):
        date_value = due.get("date")
        if isinstance(date_value, str) and date_value.strip():
            sanitized["due_date"] = date_value.strip()
    return sanitized


def _todoist_safety_assertions(
    *,
    credential_values_read: bool,
    external_mutation: bool,
    live_client_initialized: bool,
) -> dict[str, bool]:
    return {
        "credential_values_read": credential_values_read,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
        "environment_dumped": False,
        "live_client_initialized": live_client_initialized,
        "external_mutation": external_mutation,
        "todoist_task_created": external_mutation,
        "max_one_task_create": True,
        "recurrence_created": False,
        "subtasks_created": False,
        "labels_created_or_applied": False,
        "comments_created": False,
        "automatic_edits_or_deletes": False,
        "automatic_reschedule": False,
        "scheduler_activated": False,
        "production_db_active": False,
        "protected_paths_touched": False,
    }


def _safe_failure(error: BaseException) -> dict[str, str]:
    return {
        "category": error.__class__.__name__,
        "message": "Todoist smoke call failed before a validated task result.",
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

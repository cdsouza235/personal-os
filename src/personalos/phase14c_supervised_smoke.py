"""Phase 14-C supervised multi-rail smoke-test preparation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION = "personal_os_phase14c_supervised_smoke.v1"
PHASE14C_SUPERVISED_SMOKE_STATUS = "supervised_smoke_test_prepared_not_executed"
PHASE14C_SUPERVISED_SMOKE_DEFAULT_GENERATED_AT_UTC = "2026-06-26T18:00:00+00:00"
PHASE14C_SUPERVISED_SMOKE_MARKER = (
    "[Phase 14-C Test] Clean Kitchen Countertops and Stovetop"
)

DRY_RUN_MODE = "dry_run"
LIVE_RUN_MODE = "live_run"
ALLOWED_MODES: tuple[str, ...] = (DRY_RUN_MODE, LIVE_RUN_MODE)

SMOKE_RAILS: tuple[str, ...] = (
    "todoist",
    "google_calendar",
    "gmail",
    "openclaw",
)

REQUIRED_CONFIG_ENTRY_NAMES: tuple[str, ...] = (
    "PERSONALOS_PHASE14C_TODOIST_TOKEN",
    "PERSONALOS_PHASE14C_GOOGLE_CALENDAR_CREDENTIAL",
    "PERSONALOS_PHASE14C_GMAIL_CREDENTIAL",
    "PERSONALOS_PHASE14C_OPENCLAW_TEST_MODE",
)

BOUNDARY_FIELDS: tuple[str, ...] = (
    "scheduler_background_loop",
    "production_db",
    "dynamic_cleaning",
    "bulk_writes",
    "protected_path_access",
    "broad_openclaw_runtime_handoff",
)

RUNBOOK_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "generated_at_utc",
    "phase_label",
    "status",
    "test_marker",
    "rails",
    "dry_run_boundaries",
    "live_run_boundaries",
    "guardrails",
    "credential_preflight",
    "manual_invocation",
    "readiness",
    "repo_prep_safety",
)

RAIL_REPORT_FIELDS: tuple[str, ...] = (
    "rail",
    "operation",
    "max_live_operations",
    "requires_marker",
    "dry_run_allowed",
    "live_run_allowed_after_human_initiation",
)

PROTECTED_PATH_MARKERS: tuple[str, ...] = (
    "PersonalOS",
    ".openclaw",
)

OPENCLAW_ALLOWED_MODES: tuple[str, ...] = (
    "local_test_sandbox",
    "test",
    "sandbox",
)


class TodoistSmokeClient(Protocol):
    def create_task(self, task: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create the one supervised Todoist test task."""


class CalendarSmokeClient(Protocol):
    def create_event(self, event: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create the one supervised Calendar test event."""


class GmailSmokeClient(Protocol):
    def create_or_send_email(self, email: Mapping[str, Any]) -> Mapping[str, Any]:
        """Create or send the one supervised Gmail test email."""


class OpenClawSmokeClient(Protocol):
    def invoke_smoke(self, invocation: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run the one supervised OpenClaw local/test/sandbox invocation."""


@dataclass(frozen=True)
class Phase14CSupervisedSmokeClients:
    todoist: TodoistSmokeClient | None = None
    google_calendar: CalendarSmokeClient | None = None
    gmail: GmailSmokeClient | None = None
    openclaw: OpenClawSmokeClient | None = None


@dataclass(frozen=True)
class SupervisedSmokeValidation:
    accepted: bool
    status: str
    reasons: tuple[str, ...]
    checked_config_entry_names: tuple[str, ...]
    missing_config_entry_names: tuple[str, ...]
    normalized_request: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "reasons": list(self.reasons),
            "checked_config_entry_names": list(self.checked_config_entry_names),
            "missing_config_entry_names": list(self.missing_config_entry_names),
            "credential_values_read": False,
            "credential_values_logged": False,
            "normalized_request": self.normalized_request,
        }


def build_phase14c_supervised_smoke_runbook(
    *,
    generated_at_utc: str = PHASE14C_SUPERVISED_SMOKE_DEFAULT_GENERATED_AT_UTC,
) -> dict[str, Any]:
    """Build the repo-local runbook for a future supervised smoke test."""

    return {
        "schema_version": PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "phase_label": "Phase 14-C supervised multi-rail smoke test",
        "status": PHASE14C_SUPERVISED_SMOKE_STATUS,
        "test_marker": PHASE14C_SUPERVISED_SMOKE_MARKER,
        "rails": [
            {
                "rail": "todoist",
                "operation": "create_one_test_task",
                "max_live_operations": 1,
                "requires_marker": True,
                "dry_run_allowed": True,
                "live_run_allowed_after_human_initiation": True,
            },
            {
                "rail": "google_calendar",
                "operation": "create_one_self_test_event",
                "max_live_operations": 1,
                "requires_marker": True,
                "dry_run_allowed": True,
                "live_run_allowed_after_human_initiation": True,
            },
            {
                "rail": "gmail",
                "operation": "create_or_send_one_controlled_test_email",
                "max_live_operations": 1,
                "requires_marker": True,
                "dry_run_allowed": True,
                "live_run_allowed_after_human_initiation": True,
            },
            {
                "rail": "openclaw",
                "operation": "run_one_local_test_sandbox_invocation",
                "max_live_operations": 1,
                "requires_marker": True,
                "dry_run_allowed": True,
                "live_run_allowed_after_human_initiation": True,
            },
        ],
        "dry_run_boundaries": {
            "external_mutation": False,
            "credential_values_read": False,
            "scheduler_background_loop": False,
            "production_db": False,
            "protected_path_access": False,
        },
        "live_run_boundaries": {
            "manual_foreground_invocation_only": True,
            "requires_current_human_live_test_initiation": True,
            "requires_injected_live_clients": True,
            "requires_config_entry_name_preflight": True,
            "max_one_operation_per_rail": True,
            "scheduler_background_loop": False,
            "production_db": False,
            "dynamic_cleaning": False,
            "bulk_writes": False,
            "protected_path_access": False,
            "broad_openclaw_runtime_handoff": False,
        },
        "guardrails": [
            "max_one_todoist_task",
            "max_one_calendar_event",
            "max_one_gmail_email",
            "max_one_openclaw_invocation",
            "required_test_marker",
            "no_calendar_attendees_except_self_if_api_requires_it",
            "no_calendar_recurrence",
            "no_gmail_uncontrolled_recipients",
            "no_gmail_attachments",
            "no_gmail_forward_or_reply_to_existing_thread",
            "no_scheduler_background_loop",
            "no_production_db",
            "no_dynamic_cleaning",
            "no_bulk_writes",
            "no_protected_path_access",
            "no_broad_openclaw_runtime_handoff",
        ],
        "credential_preflight": build_phase14c_credential_preflight_report(()),
        "manual_invocation": {
            "repo_prep_runs_live_test": False,
            "future_live_test_must_be_started_by_chris": True,
            "live_execution_function": "execute_phase14c_supervised_smoke_request",
            "cli_surface": "personalos phase14c supervised-smoke-runbook --json",
        },
        "readiness": {
            "status": "not_ready",
            "inert_report_only": True,
            "live_rails_activated": False,
        },
        "repo_prep_safety": {
            "todoist_task_created": False,
            "calendar_event_created": False,
            "gmail_email_created_or_sent": False,
            "openclaw_invoked": False,
            "credential_values_read": False,
            "credential_values_logged": False,
            "production_db_active": False,
            "scheduler_activated": False,
            "protected_paths_touched": False,
        },
    }


def build_default_phase14c_supervised_smoke_request(
    *,
    mode: str = DRY_RUN_MODE,
    controlled_test_recipient: str = "self.phase14c.test@example.test",
    gmail_send: bool = False,
    live_run_requested: bool = False,
    approval_reference: str | None = None,
) -> dict[str, Any]:
    """Build the one-object-per-rail default smoke request payload."""

    return {
        "schema_version": PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION,
        "mode": mode,
        "test_marker": PHASE14C_SUPERVISED_SMOKE_MARKER,
        "live_run_requested": live_run_requested,
        "approval_reference": approval_reference,
        "controlled_test_recipients": [controlled_test_recipient],
        "self_test_identity": controlled_test_recipient,
        "rails": {
            "todoist": {
                "tasks": [
                    {
                        "title": PHASE14C_SUPERVISED_SMOKE_MARKER,
                        "description": "Supervised Phase 14-C Todoist smoke test.",
                        "recurrence": None,
                    }
                ]
            },
            "google_calendar": {
                "events": [
                    {
                        "summary": PHASE14C_SUPERVISED_SMOKE_MARKER,
                        "calendar_id": "primary",
                        "attendees": [],
                        "self_attendee_required_by_api": False,
                        "recurrence": None,
                    }
                ]
            },
            "gmail": {
                "emails": [
                    {
                        "subject": PHASE14C_SUPERVISED_SMOKE_MARKER,
                        "body": "Supervised Phase 14-C Gmail smoke test.",
                        "to": [controlled_test_recipient],
                        "cc": [],
                        "bcc": [],
                        "attachments": [],
                        "send": gmail_send,
                        "create_draft": not gmail_send,
                        "thread_id": None,
                        "reply_to_existing_thread": False,
                        "forward_existing_thread": False,
                    }
                ]
            },
            "openclaw": {
                "invocations": [
                    {
                        "label": PHASE14C_SUPERVISED_SMOKE_MARKER,
                        "mode": "local_test_sandbox",
                        "scope": "single_supervised_smoke_invocation",
                        "allowed_paths": [],
                        "broad_runtime_handoff": False,
                    }
                ]
            },
        },
        "boundaries": {field: False for field in BOUNDARY_FIELDS},
    }


def build_phase14c_credential_preflight_report(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> dict[str, Any]:
    """Report config entry presence by name without reading or logging values."""

    available_names = set(_config_names_only(available_config_names))
    missing = tuple(
        name for name in REQUIRED_CONFIG_ENTRY_NAMES if name not in available_names
    )
    return {
        "checked_config_entry_names": list(REQUIRED_CONFIG_ENTRY_NAMES),
        "missing_config_entry_names": list(missing),
        "reports_missing_names_only": True,
        "credential_values_read": False,
        "credential_values_logged": False,
        "credential_values_copied": False,
        "credential_values_committed": False,
    }


def validate_phase14c_supervised_smoke_request(
    request: Mapping[str, Any] | None,
    *,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
) -> SupervisedSmokeValidation:
    """Validate a future supervised smoke request without contacting live rails."""

    credential_report = build_phase14c_credential_preflight_report(
        available_config_names
    )
    if not isinstance(request, Mapping):
        return _validation(
            accepted=False,
            reasons=("Smoke request must be a mapping.",),
            credential_report=credential_report,
        )

    reasons: list[str] = []
    if request.get("schema_version") != PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION:
        reasons.append("Smoke request schema_version does not match the contract.")

    mode = request.get("mode")
    if mode not in ALLOWED_MODES:
        reasons.append("Smoke request mode must be dry_run or live_run.")

    if request.get("test_marker") != PHASE14C_SUPERVISED_SMOKE_MARKER:
        reasons.append("Smoke request must use the required Phase 14-C test marker.")

    rails = request.get("rails")
    if not isinstance(rails, Mapping):
        reasons.append("Smoke request rails must be a mapping.")
        rails = {}

    for rail in SMOKE_RAILS:
        if rail not in rails:
            reasons.append(f"Smoke request is missing required rail {rail}.")

    boundaries = request.get("boundaries")
    if not isinstance(boundaries, Mapping):
        reasons.append("Smoke request boundaries must be a mapping.")
        boundaries = {}

    for field in BOUNDARY_FIELDS:
        if boundaries.get(field) is not False:
            reasons.append(f"Smoke boundary {field} must remain false.")

    controlled_recipients = _string_set(request.get("controlled_test_recipients"))
    self_identity = _optional_string(request.get("self_test_identity"))
    if not controlled_recipients:
        reasons.append("At least one controlled Gmail test recipient is required.")
    if self_identity is None:
        reasons.append("A self_test_identity is required for Calendar attendee checks.")

    reasons.extend(_validate_todoist(rails.get("todoist")))
    reasons.extend(_validate_calendar(rails.get("google_calendar"), self_identity))
    reasons.extend(_validate_gmail(rails.get("gmail"), controlled_recipients))
    reasons.extend(_validate_openclaw(rails.get("openclaw")))

    if mode == LIVE_RUN_MODE:
        if request.get("live_run_requested") is not True:
            reasons.append("Live run requires live_run_requested=true.")
        if not _optional_string(request.get("approval_reference")):
            reasons.append("Live run requires a current approval_reference.")
        if credential_report["missing_config_entry_names"]:
            reasons.append("Live run requires all config entry names to be present.")

    if reasons:
        return _validation(
            accepted=False,
            reasons=tuple(reasons),
            credential_report=credential_report,
        )

    return _validation(
        accepted=True,
        reasons=("Smoke request satisfies Phase 14-C supervised guardrails.",),
        credential_report=credential_report,
        normalized_request=_normalize_request(request),
    )


def execute_phase14c_supervised_smoke_request(
    request: Mapping[str, Any],
    *,
    clients: Phase14CSupervisedSmokeClients | None = None,
    available_config_names: Iterable[str] | Mapping[str, Any] = (),
    live_run_approved: bool = False,
) -> dict[str, Any]:
    """Execute dry-run planning or a future approved injected-client live smoke."""

    validation = validate_phase14c_supervised_smoke_request(
        request,
        available_config_names=available_config_names,
    )
    if not validation.accepted:
        return _execution_blocked(
            reason="Smoke request failed guardrail validation.",
            validation=validation,
        )

    normalized = validation.normalized_request
    assert normalized is not None
    if normalized["mode"] == DRY_RUN_MODE:
        return {
            "status": "dry_run_validated",
            "live_run_executed": False,
            "external_mutation": False,
            "rail_operation_counts": _operation_counts(0),
            "planned_rail_operation_counts": _operation_counts(1),
            "validation": validation.to_dict(),
            "rail_results": {
                rail: {"status": "would_execute_one_marked_test_operation"}
                for rail in SMOKE_RAILS
            },
        }

    if live_run_approved is not True:
        return _execution_blocked(
            reason="Live smoke execution requires live_run_approved=true.",
            validation=validation,
        )

    selected_clients = clients or Phase14CSupervisedSmokeClients()
    missing_clients = _missing_client_names(selected_clients)
    if missing_clients:
        return _execution_blocked(
            reason="Live smoke execution requires explicit injected clients.",
            validation=validation,
            extra_reasons=tuple(
                f"Missing injected client for {name}." for name in missing_clients
            ),
        )

    rail_payloads = normalized["rails"]
    assert selected_clients.todoist is not None
    assert selected_clients.google_calendar is not None
    assert selected_clients.gmail is not None
    assert selected_clients.openclaw is not None
    rail_results = {
        "todoist": dict(
            selected_clients.todoist.create_task(rail_payloads["todoist"]["task"])
        ),
        "google_calendar": dict(
            selected_clients.google_calendar.create_event(
                rail_payloads["google_calendar"]["event"]
            )
        ),
        "gmail": dict(
            selected_clients.gmail.create_or_send_email(rail_payloads["gmail"]["email"])
        ),
        "openclaw": dict(
            selected_clients.openclaw.invoke_smoke(
                rail_payloads["openclaw"]["invocation"]
            )
        ),
    }
    return {
        "status": "live_run_completed",
        "live_run_executed": True,
        "external_mutation": True,
        "rail_operation_counts": _operation_counts(1),
        "planned_rail_operation_counts": _operation_counts(1),
        "validation": validation.to_dict(),
        "rail_results": rail_results,
    }


def _validate_todoist(todoist: object) -> tuple[str, ...]:
    if not isinstance(todoist, Mapping):
        return ("Todoist rail payload must be a mapping.",)
    tasks = _items(todoist, "tasks")
    reasons = _require_max_one(tasks, "Todoist task")
    if len(tasks) != 1:
        return tuple(reasons)
    task = tasks[0]
    if not _contains_marker(task.get("title")):
        reasons.append("Todoist task title must include the required test marker.")
    if _has_recurrence(task):
        reasons.append("Todoist task recurrence is not allowed.")
    return tuple(reasons)


def _validate_calendar(calendar: object, self_identity: str | None) -> tuple[str, ...]:
    if not isinstance(calendar, Mapping):
        return ("Google Calendar rail payload must be a mapping.",)
    events = _items(calendar, "events")
    reasons = _require_max_one(events, "Calendar event")
    if len(events) != 1:
        return tuple(reasons)
    event = events[0]
    if not _contains_marker(event.get("summary") or event.get("title")):
        reasons.append("Calendar event summary must include the required test marker.")
    if _has_recurrence(event):
        reasons.append("Calendar event recurrence is not allowed.")
    attendees = _string_list(event.get("attendees"))
    if attendees:
        if event.get("self_attendee_required_by_api") is not True:
            reasons.append("Calendar attendees are not allowed unless the API requires self.")
        elif self_identity is None or attendees != [self_identity]:
            reasons.append("Calendar attendees must contain only the self test identity.")
    return tuple(reasons)


def _validate_gmail(gmail: object, controlled_recipients: set[str]) -> tuple[str, ...]:
    if not isinstance(gmail, Mapping):
        return ("Gmail rail payload must be a mapping.",)
    emails = _items(gmail, "emails")
    reasons = _require_max_one(emails, "Gmail email")
    if len(emails) != 1:
        return tuple(reasons)
    email = emails[0]
    if not _contains_marker(email.get("subject")):
        reasons.append("Gmail subject must include the required test marker.")
    to_recipients = _string_list(email.get("to"))
    all_recipients = set(to_recipients)
    all_recipients.update(_string_list(email.get("cc")))
    all_recipients.update(_string_list(email.get("bcc")))
    if not to_recipients:
        reasons.append("Gmail test email requires one controlled to recipient.")
    if not all_recipients.issubset(controlled_recipients):
        reasons.append("Gmail recipients must be controlled test recipients only.")
    if _items(email, "attachments"):
        reasons.append("Gmail attachments are not allowed.")
    if _optional_string(email.get("thread_id")) is not None:
        reasons.append("Gmail must not attach to an existing thread.")
    if email.get("reply_to_existing_thread") is not False:
        reasons.append("Gmail replies to existing threads are not allowed.")
    if email.get("forward_existing_thread") is not False:
        reasons.append("Gmail forwarding existing threads is not allowed.")
    return tuple(reasons)


def _validate_openclaw(openclaw: object) -> tuple[str, ...]:
    if not isinstance(openclaw, Mapping):
        return ("OpenClaw rail payload must be a mapping.",)
    invocations = _items(openclaw, "invocations")
    reasons = _require_max_one(invocations, "OpenClaw invocation")
    if len(invocations) != 1:
        return tuple(reasons)
    invocation = invocations[0]
    if not _contains_marker(invocation.get("label")):
        reasons.append("OpenClaw invocation label must include the required test marker.")
    if invocation.get("mode") not in OPENCLAW_ALLOWED_MODES:
        reasons.append("OpenClaw invocation must use local/test/sandbox mode.")
    if invocation.get("scope") != "single_supervised_smoke_invocation":
        reasons.append("OpenClaw scope must stay to one supervised smoke invocation.")
    if invocation.get("broad_runtime_handoff") is not False:
        reasons.append("OpenClaw broad runtime handoff is not allowed.")
    for path in _string_list(invocation.get("allowed_paths")):
        if any(marker in path for marker in PROTECTED_PATH_MARKERS):
            reasons.append("OpenClaw invocation must not include protected paths.")
            break
    return tuple(reasons)


def _validation(
    *,
    accepted: bool,
    reasons: Sequence[str],
    credential_report: Mapping[str, Any],
    normalized_request: dict[str, Any] | None = None,
) -> SupervisedSmokeValidation:
    return SupervisedSmokeValidation(
        accepted=accepted,
        status="accepted" if accepted else "blocked",
        reasons=tuple(reasons),
        checked_config_entry_names=tuple(
            credential_report["checked_config_entry_names"]
        ),
        missing_config_entry_names=tuple(
            credential_report["missing_config_entry_names"]
        ),
        normalized_request=normalized_request if accepted else None,
    )


def _execution_blocked(
    *,
    reason: str,
    validation: SupervisedSmokeValidation,
    extra_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "live_run_executed": False,
        "external_mutation": False,
        "rail_operation_counts": _operation_counts(0),
        "validation": validation.to_dict(),
        "reasons": [reason, *extra_reasons],
        "rail_results": {},
    }


def _normalize_request(request: Mapping[str, Any]) -> dict[str, Any]:
    rails = request["rails"]
    return {
        "schema_version": PHASE14C_SUPERVISED_SMOKE_SCHEMA_VERSION,
        "mode": str(request["mode"]),
        "test_marker": PHASE14C_SUPERVISED_SMOKE_MARKER,
        "live_run_requested": bool(request.get("live_run_requested")),
        "approval_reference": _optional_string(request.get("approval_reference")),
        "rail_operation_counts": _operation_counts(1),
        "rails": {
            "todoist": {"task": dict(_items(rails["todoist"], "tasks")[0])},
            "google_calendar": {
                "event": dict(_items(rails["google_calendar"], "events")[0])
            },
            "gmail": {"email": dict(_items(rails["gmail"], "emails")[0])},
            "openclaw": {
                "invocation": dict(_items(rails["openclaw"], "invocations")[0])
            },
        },
        "boundaries": {field: False for field in BOUNDARY_FIELDS},
    }


def _missing_client_names(clients: Phase14CSupervisedSmokeClients) -> tuple[str, ...]:
    missing: list[str] = []
    for name in SMOKE_RAILS:
        attr = "google_calendar" if name == "google_calendar" else name
        if getattr(clients, attr) is None:
            missing.append(name)
    return tuple(missing)


def _operation_counts(count: int) -> dict[str, int]:
    return {
        "todoist_tasks": count,
        "calendar_events": count,
        "gmail_emails": count,
        "openclaw_invocations": count,
    }


def _require_max_one(items: Sequence[Mapping[str, Any]], label: str) -> list[str]:
    if len(items) > 1:
        return [f"{label} count must be at most one."]
    if len(items) < 1:
        return [f"{label} count must be exactly one for this smoke request."]
    return []


def _items(source: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = source.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _has_recurrence(source: Mapping[str, Any]) -> bool:
    for key in ("recurrence", "repeat", "rrule"):
        value = source.get(key)
        if value not in (None, "", [], ()):
            return True
    return False


def _contains_marker(value: object) -> bool:
    return isinstance(value, str) and PHASE14C_SUPERVISED_SMOKE_MARKER in value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def _string_set(value: object) -> set[str]:
    return set(_string_list(value))


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _config_names_only(
    available_config_names: Iterable[str] | Mapping[str, Any],
) -> tuple[str, ...]:
    if isinstance(available_config_names, Mapping):
        names = available_config_names.keys()
    else:
        names = available_config_names
    return tuple(str(name) for name in names)

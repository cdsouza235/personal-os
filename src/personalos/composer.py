"""Dev/test-only Composer model integration foundation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any, Protocol

from personalos import execution_rails as rails
from personalos.calendar_blocks import preview_calendar_block
from personalos.config import DEFAULT_TIMEZONE
from personalos.permissions import PermissionMode
from personalos.state import (
    count_calendar_blocks,
    count_composer_outputs,
    count_composer_packets,
    count_followups,
    count_model_runs,
    count_priorities,
    count_routine_completions,
    count_routines,
    count_todoist_tasks,
    create_composer_output,
    create_composer_packet,
    create_model_run,
    get_composer_output,
    get_composer_packet,
    get_model_run,
    get_permission_setting,
    list_calendar_blocks,
    list_composer_outputs,
    list_composer_packets,
    list_followups,
    list_model_runs,
    list_priorities,
    list_routines,
    list_todoist_tasks,
)
from personalos.todoist import preview_todoist_task

COMPOSER_MODULE_READ_PERMISSION = "composer_module_dev_test_read"
COMPOSER_MODULE_WRITE_PERMISSION = "composer_module_dev_test_write"
COMPOSER_MODULE_RUN_PERMISSION = "composer_module_dev_test_run"

COMPOSER_PACKET_SCHEMA_VERSION = "composer_packet.v1"
COMPOSER_OUTPUT_SCHEMA_VERSION = "composer_output.v1"
FAKE_COMPOSER_MODEL_NAME = "fake-composer-v1"
FAKE_COMPOSER_ADAPTER_NAME = "fake_composer_adapter"
COMPOSER_MODEL_ROLE = "composer_model"

PACKET_TYPES = ("daily_brief", "window_brief", "ad_hoc_preview")
BRIEFING_WINDOWS = ("morning", "midday", "afternoon", "evening", "none")
RISK_LEVELS = ("low", "medium", "high")
APPROVAL_MODES = ("auto_allowed", "approval_required", "manual_only")
WARNING_SEVERITIES = ("info", "warning", "blocked")
ROUTING_STATUSES = (
    "accepted",
    "rejected",
    "blocked_review_required",
    "blocked_high_risk",
    "blocked_malformed",
)

PACKET_INPUT_SECTIONS = (
    "routine_state",
    "priority_summaries",
    "followup_summaries",
    "todoist_task_summaries",
    "calendar_block_summaries",
    "calendar_availability_summary",
    "today_schedule_summary",
    "wsp_routine_rules",
    "prior_briefing_summaries",
    "completion_status",
)

OUTPUT_REQUIRED_SECTIONS = (
    "email_briefs",
    "todoist_tasks",
    "calendar_blocks",
    "followups",
    "warnings",
)

FORBIDDEN_COMPOSER_TERMS = (
    "raw_notes",
    "full_vault",
    "full_personalos_vault",
    "vault_path",
    "personalos_path",
    "openclaw_path",
    "credential",
    "credentials",
    "secret",
    "token",
    "api_key",
    "oauth",
    "password",
    "legal_source_documents",
    "tax_source_documents",
    "unrestricted_file_access",
    "arbitrary_filesystem_access",
    "journal_archive",
    "gmail_body",
    "live_todoist_api",
    "live_calendar_api",
)


class ComposerModulePermissionDenied(PermissionError):
    """Raised when a Composer module permission setting does not allow the action."""


class ComposerValidationError(ValueError):
    """Raised when Composer packet or output validation fails."""


class FakeComposerAdapterError(RuntimeError):
    """Raised by the fake Composer adapter failure mode used in tests."""


class ComposerAdapter(Protocol):
    dev_test_fake_adapter: bool
    model_name: str
    adapter_name: str

    def compose(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        """Return a structured Composer output and readable text."""


class FakeComposerAdapter:
    """Deterministic fake adapter; it never touches network, credentials, or live APIs."""

    dev_test_fake_adapter = True
    model_name = FAKE_COMPOSER_MODEL_NAME
    adapter_name = FAKE_COMPOSER_ADAPTER_NAME

    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[dict[str, Any]] = []

    def compose(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        validated_packet = validate_composer_packet(packet)
        self.calls.append({"packet_id": validated_packet["packet_id"]})
        if self.should_fail:
            raise FakeComposerAdapterError("Fake Composer adapter failure mode was requested.")

        packet_id = validated_packet["packet_id"]
        briefing_window = validated_packet["briefing_window"]
        source_date = validated_packet["source_date"]
        start_time = f"{source_date}T09:00:00-05:00"
        end_time = f"{source_date}T09:30:00-05:00"
        output_json = {
            "schema_version": COMPOSER_OUTPUT_SCHEMA_VERSION,
            "packet_id": packet_id,
            "email_briefs": [
                {
                    "briefing_window": briefing_window,
                    "subject": f"Personal OS {briefing_window} brief for {source_date}",
                    "body_markdown": (
                        f"## {briefing_window.title()} Brief\n\n"
                        "Review the safe dev/test summaries and confirm the next action."
                    ),
                    "summary": "Safe dev/test Composer preview generated from packet summaries.",
                }
            ],
            "todoist_tasks": [
                {
                    "task_title": f"Review {briefing_window} Personal OS brief",
                    "description": "Review the generated dev/test brief candidate.",
                    "source_type": "composer_output",
                    "source_id": packet_id,
                    "project": "Admin",
                    "labels": ["composer", "preview"],
                    "due_date_or_due_string": source_date,
                    "priority": 2,
                    "risk_level": "low",
                    "approval_mode": "auto_allowed",
                    "dedupe_key": f"composer:{packet_id}:todoist:review-brief",
                    "status": "proposed",
                }
            ],
            "calendar_blocks": [
                {
                    "title": f"Review {briefing_window} brief",
                    "description": "Self-only review block generated as a dev/test candidate.",
                    "source_type": "composer_output",
                    "source_id": packet_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": 30,
                    "calendar_id": "primary",
                    "timezone": DEFAULT_TIMEZONE,
                    "approval_mode": "auto_allowed",
                    "risk_level": "low",
                    "dedupe_key": f"composer:{packet_id}:calendar:review-brief",
                    "status": "proposed",
                }
            ],
            "followups": [
                {
                    "title": f"Check {briefing_window} brief result",
                    "summary": "Confirm whether the previewed brief needs edits.",
                    "source_type": "composer_output",
                    "source_id": packet_id,
                    "risk_level": "low",
                    "approval_mode": "auto_allowed",
                    "dedupe_key": f"composer:{packet_id}:followup:check-result",
                    "status": "proposed",
                }
            ],
            "warnings": [],
        }
        readable_text = (
            f"{briefing_window.title()} brief preview for {source_date}. "
            "Includes one email brief, one Todoist candidate, one Calendar block, "
            "and one follow-up candidate."
        )
        return {
            "output_json": output_json,
            "readable_text": readable_text,
            "model_name": self.model_name,
            "adapter_name": self.adapter_name,
        }


def build_composer_packet_from_state(
    connection: sqlite3.Connection,
    *,
    packet_id: str,
    packet_type: str = "daily_brief",
    briefing_window: str = "morning",
    source_date: str,
    timezone: str = DEFAULT_TIMEZONE,
    generated_at: str | None = None,
    calendar_availability_summary: Mapping[str, Any] | None = None,
    wsp_routine_rules: list[Mapping[str, Any]] | None = None,
    prior_briefing_summaries: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source_date = _validate_iso_date("source_date", source_date)
    generated = _validate_iso_datetime("generated_at", generated_at or _utc_now())
    packet = {
        "schema_version": COMPOSER_PACKET_SCHEMA_VERSION,
        "packet_id": _validate_required_text("packet_id", packet_id),
        "packet_type": _validate_choice("packet_type", packet_type, PACKET_TYPES),
        "briefing_window": _validate_choice(
            "briefing_window",
            briefing_window,
            BRIEFING_WINDOWS,
        ),
        "source_date": source_date,
        "timezone": _validate_timezone(timezone),
        "generated_at": generated,
        "inputs": {
            "routine_state": _routine_state_summaries(connection),
            "priority_summaries": _priority_summaries(connection),
            "followup_summaries": _followup_summaries(connection),
            "todoist_task_summaries": _todoist_task_summaries(connection),
            "calendar_block_summaries": _calendar_block_summaries(connection),
            "calendar_availability_summary": dict(calendar_availability_summary or {}),
            "today_schedule_summary": _today_schedule_summary(connection, source_date),
            "wsp_routine_rules": [dict(item) for item in (wsp_routine_rules or [])],
            "prior_briefing_summaries": [
                dict(item) for item in (prior_briefing_summaries or [])
            ],
            "completion_status": {
                "source_date": source_date,
                "routine_count": count_routines(connection),
                "routine_completion_count": count_routine_completions(connection),
                "priority_count": count_priorities(connection),
                "followup_count": count_followups(connection),
                "todoist_candidate_count": count_todoist_tasks(connection),
                "calendar_block_count": count_calendar_blocks(connection),
            },
        },
        "omissions": ["Protected source classes omitted by policy."],
        "warnings": [],
    }
    return validate_composer_packet(packet)


def validate_composer_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ComposerValidationError("Composer packet must be a JSON object.")
    _reject_forbidden_content(packet)
    required = {
        "schema_version",
        "packet_id",
        "packet_type",
        "briefing_window",
        "source_date",
        "timezone",
        "generated_at",
        "inputs",
        "omissions",
        "warnings",
    }
    _validate_exact_keys("composer packet", packet, required)

    inputs = _require_mapping(packet["inputs"], "inputs")
    _validate_exact_keys("composer packet inputs", inputs, set(PACKET_INPUT_SECTIONS))

    for section in (
        "routine_state",
        "priority_summaries",
        "followup_summaries",
        "todoist_task_summaries",
        "calendar_block_summaries",
        "today_schedule_summary",
        "wsp_routine_rules",
        "prior_briefing_summaries",
    ):
        _require_list(inputs[section], f"inputs.{section}")

    _require_mapping(
        inputs["calendar_availability_summary"],
        "inputs.calendar_availability_summary",
    )
    _require_mapping(inputs["completion_status"], "inputs.completion_status")

    normalized = {
        "schema_version": _validate_literal(
            "schema_version",
            packet["schema_version"],
            COMPOSER_PACKET_SCHEMA_VERSION,
        ),
        "packet_id": _validate_required_text("packet_id", packet["packet_id"]),
        "packet_type": _validate_choice("packet_type", packet["packet_type"], PACKET_TYPES),
        "briefing_window": _validate_choice(
            "briefing_window",
            packet["briefing_window"],
            BRIEFING_WINDOWS,
        ),
        "source_date": _validate_iso_date("source_date", packet["source_date"]),
        "timezone": _validate_timezone(packet["timezone"]),
        "generated_at": _validate_iso_datetime("generated_at", packet["generated_at"]),
        "inputs": {key: _json_copy(inputs[key]) for key in PACKET_INPUT_SECTIONS},
        "omissions": _require_list(packet["omissions"], "omissions"),
        "warnings": _require_list(packet["warnings"], "warnings"),
    }
    return normalized


def validate_composer_output(
    output_json: Mapping[str, Any] | str,
    *,
    readable_text: str | None,
) -> dict[str, Any]:
    parsed = _parse_output_json(output_json)
    readable_text = _validate_required_text("readable_text", readable_text)
    _reject_forbidden_content(parsed)
    required = {"schema_version", "packet_id", *OUTPUT_REQUIRED_SECTIONS}
    _validate_exact_keys("composer output", parsed, required)

    normalized = {
        "schema_version": _validate_literal(
            "schema_version",
            parsed["schema_version"],
            COMPOSER_OUTPUT_SCHEMA_VERSION,
        ),
        "packet_id": _validate_required_text("packet_id", parsed["packet_id"]),
        "email_briefs": [
            _validate_email_brief(item, index)
            for index, item in enumerate(_require_list(parsed["email_briefs"], "email_briefs"))
        ],
        "todoist_tasks": [
            _validate_todoist_candidate(item, index)
            for index, item in enumerate(_require_list(parsed["todoist_tasks"], "todoist_tasks"))
        ],
        "calendar_blocks": [
            _validate_calendar_candidate(item, index)
            for index, item in enumerate(
                _require_list(parsed["calendar_blocks"], "calendar_blocks")
            )
        ],
        "followups": [
            _validate_followup_candidate(item, index)
            for index, item in enumerate(_require_list(parsed["followups"], "followups"))
        ],
        "warnings": [
            _validate_warning(item, index)
            for index, item in enumerate(_require_list(parsed["warnings"], "warnings"))
        ],
    }
    normalized["_readable_text"] = readable_text
    return normalized


def build_candidate_routing_report(output_json: Mapping[str, Any] | str) -> dict[str, Any]:
    """Route candidate lists only; this is not full Composer Output validation."""

    report: dict[str, Any] = {
        "accepted_candidates": [],
        "rejected_candidates": [],
        "blocked_candidates": [],
        "warnings": [],
        "candidate_routing_only": True,
        "no_external_writes": True,
    }

    try:
        parsed = _parse_output_json(output_json)
    except ComposerValidationError as error:
        report["rejected_candidates"].append(
            _routing_entry(
                candidate_type="composer_output",
                candidate_index=0,
                status="rejected",
                reason=str(error),
            )
        )
        return report

    if isinstance(parsed.get("warnings"), list):
        for index, warning in enumerate(parsed["warnings"]):
            try:
                report["warnings"].append(_validate_warning(warning, index))
            except ComposerValidationError as error:
                report["warnings"].append(
                    {
                        "code": "malformed_warning",
                        "severity": "warning",
                        "message": str(error),
                        "item_ref": f"warnings[{index}]",
                    }
                )

    for index, candidate in enumerate(parsed.get("todoist_tasks", [])):
        _route_candidate(
            report,
            candidate_type="todoist_task",
            candidate_index=index,
            candidate=candidate,
            validator=_validate_todoist_candidate,
        )
    for index, candidate in enumerate(parsed.get("calendar_blocks", [])):
        _route_candidate(
            report,
            candidate_type="calendar_block",
            candidate_index=index,
            candidate=candidate,
            validator=_validate_calendar_candidate,
        )
    return report


def build_validated_candidate_routing_report(
    output_json: Mapping[str, Any] | str,
    *,
    readable_text: str | None,
) -> dict[str, Any]:
    validated_output = validate_composer_output(output_json, readable_text=readable_text)
    output_payload = {
        key: value for key, value in validated_output.items() if key != "_readable_text"
    }
    report = build_candidate_routing_report(output_payload)
    report["candidate_routing_only"] = False
    report["full_output_validation"] = "passed"
    return report


def route_composer_output_candidates(
    connection: sqlite3.Connection,
    *,
    output_json: Mapping[str, Any] | str,
) -> dict[str, Any]:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_RUN_PERMISSION)
    return build_candidate_routing_report(output_json)


def create_composer_packet_record(
    connection: sqlite3.Connection,
    *,
    packet: Mapping[str, Any],
    status: str = "validated",
) -> dict[str, Any]:
    validated_packet = validate_composer_packet(packet)
    permission = evaluate_composer_module_permission(
        connection,
        category=COMPOSER_MODULE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            dry_run=False,
            would_write=validated_packet,
            record_type="packet",
        )

    created = create_composer_packet(
        connection,
        packet_id=validated_packet["packet_id"],
        packet_type=validated_packet["packet_type"],
        briefing_window=validated_packet["briefing_window"],
        source_date=validated_packet["source_date"],
        timezone=validated_packet["timezone"],
        packet_json=validated_packet,
        status=status,
        created_at=validated_packet["generated_at"],
        updated_at=validated_packet["generated_at"],
    )
    return {
        "status": "created",
        "reason": "Composer packet was persisted in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "permission": permission,
        "packet": created,
        "would_write": validated_packet,
    }


def create_composer_output_record(
    connection: sqlite3.Connection,
    *,
    output_id: str,
    packet_id: str,
    output_json: Mapping[str, Any] | str,
    readable_text: str | None,
    route_report: Mapping[str, Any] | None = None,
    validation_status: str = "validated",
    status: str = "routed",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    validated_output = validate_composer_output(output_json, readable_text=readable_text)
    if validated_output["packet_id"] != packet_id:
        raise ComposerValidationError("Composer output packet_id must match packet_id argument.")
    persisted_output = {
        key: value for key, value in validated_output.items() if key != "_readable_text"
    }
    permission = evaluate_composer_module_permission(
        connection,
        category=COMPOSER_MODULE_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            dry_run=False,
            would_write=persisted_output,
            record_type="output",
        )

    created = create_composer_output(
        connection,
        output_id=output_id,
        packet_id=packet_id,
        output_json=persisted_output,
        readable_text=validated_output["_readable_text"],
        validation_status=validation_status,
        route_report=route_report,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )
    return {
        "status": "created",
        "reason": "Composer output was persisted in the dev/test SQLite database only.",
        "dry_run": False,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "permission": permission,
        "output": created,
        "would_write": persisted_output,
    }


def run_fake_composer_model(
    connection: sqlite3.Connection,
    *,
    packet: Mapping[str, Any],
    adapter: ComposerAdapter | None = None,
    run_at: str | None = None,
) -> dict[str, Any]:
    validated_packet = validate_composer_packet(packet)
    run_permission = evaluate_composer_module_permission(
        connection,
        category=COMPOSER_MODULE_RUN_PERMISSION,
    )
    write_permission = evaluate_composer_module_permission(
        connection,
        category=COMPOSER_MODULE_WRITE_PERMISSION,
    )
    if not run_permission["allowed"]:
        return _blocked_result(
            reason=run_permission["reason"],
            permission=run_permission,
            dry_run=True,
            would_write=validated_packet,
            record_type="run",
        )
    if not write_permission["allowed"]:
        return _blocked_result(
            reason=write_permission["reason"],
            permission=write_permission,
            dry_run=True,
            would_write=validated_packet,
            record_type="run",
        )

    selected_adapter = adapter or FakeComposerAdapter()
    _require_fake_adapter(selected_adapter)
    started_at = _validate_iso_datetime("run_at", run_at or _utc_now())
    packet_id = validated_packet["packet_id"]
    model_run_id = stable_composer_id("model-run", f"{packet_id}|{started_at}")
    packet_record: dict[str, Any] | None = None
    output_record: dict[str, Any] | None = None

    try:
        packet_record = create_composer_packet(
            connection,
            packet_id=packet_id,
            packet_type=validated_packet["packet_type"],
            briefing_window=validated_packet["briefing_window"],
            source_date=validated_packet["source_date"],
            timezone=validated_packet["timezone"],
            packet_json=validated_packet,
            status="completed",
            created_at=validated_packet["generated_at"],
            updated_at=started_at,
        )
        adapter_result = selected_adapter.compose(validated_packet)
        output_json = validate_composer_output(
            adapter_result["output_json"],
            readable_text=adapter_result["readable_text"],
        )
        output_payload = {
            key: value for key, value in output_json.items() if key != "_readable_text"
        }
        route_report = build_validated_candidate_routing_report(
            output_payload,
            readable_text=output_json["_readable_text"],
        )
        output_id = stable_composer_id("composer-output", packet_id)
        output_record = create_composer_output(
            connection,
            output_id=output_id,
            packet_id=packet_id,
            output_json=output_payload,
            readable_text=output_json["_readable_text"],
            validation_status="validated",
            route_report=route_report,
            status="routed",
            created_at=started_at,
            updated_at=started_at,
        )
        model_run = create_model_run(
            connection,
            model_run_id=model_run_id,
            packet_id=packet_id,
            output_id=output_record["id"],
            model_name=selected_adapter.model_name,
            model_role=COMPOSER_MODEL_ROLE,
            adapter_name=selected_adapter.adapter_name,
            dry_run=True,
            status="completed",
            input_token_count=_fake_token_count(validated_packet),
            output_token_count=_fake_token_count(output_payload),
            created_at=started_at,
            completed_at=started_at,
        )
    except Exception as error:
        model_run = create_model_run(
            connection,
            model_run_id=model_run_id,
            packet_id=packet_id,
            output_id=None,
            model_name=getattr(selected_adapter, "model_name", FAKE_COMPOSER_MODEL_NAME),
            model_role=COMPOSER_MODEL_ROLE,
            adapter_name=getattr(selected_adapter, "adapter_name", FAKE_COMPOSER_ADAPTER_NAME),
            dry_run=True,
            status="failed",
            input_token_count=_fake_token_count(validated_packet),
            output_token_count=None,
            error_message=_redacted_error_message(error),
            created_at=started_at,
            completed_at=started_at,
        )
        return {
            "status": "failed",
            "reason": "Fake Composer adapter run failed; no external systems were touched.",
            "dry_run": True,
            "no_send": True,
            "database_write": True,
            "external_mutation": False,
            "adapter_called": True,
            "network_called": False,
            "permission": {"run": run_permission, "write": write_permission},
            "packet": packet_record,
            "output": output_record,
            "model_run": model_run,
            "route_report": None,
        }

    return {
        "status": "completed",
        "reason": "Fake Composer adapter produced a routed dev/test output only.",
        "dry_run": True,
        "no_send": True,
        "database_write": True,
        "external_mutation": False,
        "adapter_called": True,
        "network_called": False,
        "permission": {"run": run_permission, "write": write_permission},
        "packet": packet_record,
        "output": output_record,
        "model_run": model_run,
        "route_report": route_report,
    }


def read_composer_packet(
    connection: sqlite3.Connection,
    *,
    packet_id: str,
) -> dict[str, Any] | None:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return get_composer_packet(connection, packet_id)


def read_composer_packets(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    packet_type: str | None = None,
    source_date: str | None = None,
) -> list[dict[str, Any]]:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return list_composer_packets(
        connection,
        status=status,
        packet_type=packet_type,
        source_date=source_date,
    )


def read_composer_packet_count(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    packet_type: str | None = None,
    source_date: str | None = None,
) -> int:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return count_composer_packets(
        connection,
        status=status,
        packet_type=packet_type,
        source_date=source_date,
    )


def read_composer_output(
    connection: sqlite3.Connection,
    *,
    output_id: str,
) -> dict[str, Any] | None:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return get_composer_output(connection, output_id)


def read_composer_outputs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
) -> list[dict[str, Any]]:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return list_composer_outputs(
        connection,
        packet_id=packet_id,
        status=status,
        validation_status=validation_status,
    )


def read_composer_output_count(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
) -> int:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return count_composer_outputs(
        connection,
        packet_id=packet_id,
        status=status,
        validation_status=validation_status,
    )


def read_model_run(
    connection: sqlite3.Connection,
    *,
    model_run_id: str,
) -> dict[str, Any] | None:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return get_model_run(connection, model_run_id)


def read_model_runs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return list_model_runs(connection, packet_id=packet_id, status=status)


def read_model_run_count(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
) -> int:
    require_composer_module_permission(connection, category=COMPOSER_MODULE_READ_PERMISSION)
    return count_model_runs(connection, packet_id=packet_id, status=status)


def require_composer_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_composer_module_permission(connection, category=category)
    if not decision["allowed"]:
        raise ComposerModulePermissionDenied(decision["reason"])
    return decision


def evaluate_composer_module_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = _validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=None,
            reason=f"Missing Composer module permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid Composer module permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Composer module permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Composer module permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Composer module permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def stable_composer_id(prefix: str, material: str) -> str:
    prefix = rails.normalize_for_dedupe(_validate_required_text("prefix", prefix)).replace(" ", "-")
    material = _validate_required_text("material", material)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _validate_email_brief(item: Any, index: int) -> dict[str, Any]:
    item = _require_mapping(item, f"email_briefs[{index}]")
    _validate_exact_keys(
        f"email_briefs[{index}]",
        item,
        {"briefing_window", "subject", "body_markdown", "summary"},
    )
    return {
        "briefing_window": _validate_choice(
            "briefing_window",
            item["briefing_window"],
            BRIEFING_WINDOWS,
        ),
        "subject": _validate_required_text("subject", item["subject"]),
        "body_markdown": _validate_required_text("body_markdown", item["body_markdown"]),
        "summary": _validate_required_text("summary", item["summary"]),
    }


def _validate_todoist_candidate(item: Any, index: int) -> dict[str, Any]:
    item = _require_mapping(item, f"todoist_tasks[{index}]")
    _validate_exact_keys(
        f"todoist_tasks[{index}]",
        item,
        {
            "task_title",
            "description",
            "source_type",
            "source_id",
            "project",
            "labels",
            "due_date_or_due_string",
            "priority",
            "risk_level",
            "approval_mode",
            "dedupe_key",
            "status",
        },
    )
    if item["source_type"] != "composer_output":
        raise ComposerValidationError("Todoist candidate source_type must be composer_output.")
    if item["status"] != "proposed":
        raise ComposerValidationError("Todoist candidate status must be proposed.")
    priority = _normalize_todoist_priority(item["priority"])
    due_value = "" if item["due_date_or_due_string"] is None else item["due_date_or_due_string"]
    normalized = {
        "task_title": item["task_title"],
        "description": item["description"],
        "source_type": item["source_type"],
        "source_id": item["source_id"],
        "project": item["project"],
        "labels": item["labels"],
        "due_date_or_due_string": due_value,
        "priority": priority,
        "risk_level": item["risk_level"],
        "approval_mode": item["approval_mode"],
        "dedupe_key": item["dedupe_key"],
        "status": item["status"],
    }
    preview_todoist_task(**normalized)
    return {
        "task_title": _validate_required_text("task_title", item["task_title"]),
        "description": _validate_text("description", item["description"]),
        "source_type": item["source_type"],
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "project": _validate_required_text("project", item["project"]),
        "labels": rails.validate_labels(item["labels"]),
        "due_date_or_due_string": item["due_date_or_due_string"],
        "priority": priority,
        "risk_level": rails.validate_risk_level(item["risk_level"]),
        "approval_mode": rails.validate_approval_mode(
            item["approval_mode"],
            risk_level=item["risk_level"],
        ),
        "dedupe_key": rails.normalize_dedupe_key(item["dedupe_key"]),
        "status": item["status"],
    }


def _validate_calendar_candidate(item: Any, index: int) -> dict[str, Any]:
    item = _require_mapping(item, f"calendar_blocks[{index}]")
    _validate_exact_keys(
        f"calendar_blocks[{index}]",
        item,
        {
            "title",
            "description",
            "source_type",
            "source_id",
            "start_time",
            "end_time",
            "duration_minutes",
            "calendar_id",
            "timezone",
            "approval_mode",
            "risk_level",
            "dedupe_key",
            "status",
        },
    )
    if item["source_type"] != "composer_output":
        raise ComposerValidationError("Calendar candidate source_type must be composer_output.")
    if item["status"] != "proposed":
        raise ComposerValidationError("Calendar candidate status must be proposed.")
    if item["timezone"] != DEFAULT_TIMEZONE:
        raise ComposerValidationError(f"Calendar candidate timezone must be {DEFAULT_TIMEZONE}.")
    calendar_id = "" if item["calendar_id"] is None else item["calendar_id"]
    normalized = {
        "title": item["title"],
        "description": item["description"],
        "source_type": item["source_type"],
        "source_id": item["source_id"],
        "start_time": item["start_time"],
        "end_time": item["end_time"],
        "duration_minutes": item["duration_minutes"],
        "calendar_id": calendar_id,
        "timezone": item["timezone"],
        "risk_level": item["risk_level"],
        "approval_mode": item["approval_mode"],
        "dedupe_key": item["dedupe_key"],
        "status": item["status"],
    }
    preview_calendar_block(**normalized)
    return {
        "title": _validate_required_text("title", item["title"]),
        "description": _validate_text("description", item["description"]),
        "source_type": item["source_type"],
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "start_time": item["start_time"],
        "end_time": item["end_time"],
        "duration_minutes": item["duration_minutes"],
        "calendar_id": calendar_id,
        "timezone": item["timezone"],
        "approval_mode": rails.validate_approval_mode(
            item["approval_mode"],
            risk_level=item["risk_level"],
        ),
        "risk_level": rails.validate_risk_level(item["risk_level"]),
        "dedupe_key": rails.normalize_dedupe_key(item["dedupe_key"]),
        "status": item["status"],
    }


def _validate_followup_candidate(item: Any, index: int) -> dict[str, Any]:
    item = _require_mapping(item, f"followups[{index}]")
    _validate_exact_keys(
        f"followups[{index}]",
        item,
        {
            "title",
            "summary",
            "source_type",
            "source_id",
            "risk_level",
            "approval_mode",
            "dedupe_key",
            "status",
        },
    )
    if item["source_type"] != "composer_output":
        raise ComposerValidationError("Follow-up candidate source_type must be composer_output.")
    if item["status"] != "proposed":
        raise ComposerValidationError("Follow-up candidate status must be proposed.")
    risk_level = rails.validate_risk_level(item["risk_level"])
    approval_mode = rails.validate_approval_mode(item["approval_mode"], risk_level=risk_level)
    return {
        "title": _validate_required_text("title", item["title"]),
        "summary": _validate_required_text("summary", item["summary"]),
        "source_type": item["source_type"],
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "dedupe_key": rails.normalize_dedupe_key(item["dedupe_key"]),
        "status": item["status"],
    }


def _validate_warning(item: Any, index: int) -> dict[str, Any]:
    item = _require_mapping(item, f"warnings[{index}]")
    _validate_exact_keys(
        f"warnings[{index}]",
        item,
        {"code", "severity", "message", "item_ref"},
    )
    item_ref = item["item_ref"]
    if item_ref is not None:
        item_ref = _validate_required_text("item_ref", item_ref)
    return {
        "code": _validate_required_text("code", item["code"]),
        "severity": _validate_choice("severity", item["severity"], WARNING_SEVERITIES),
        "message": _validate_required_text("message", item["message"]),
        "item_ref": item_ref,
    }


def _route_candidate(
    report: dict[str, Any],
    *,
    candidate_type: str,
    candidate_index: int,
    candidate: Any,
    validator: Any,
) -> None:
    try:
        _reject_forbidden_content(candidate)
    except ComposerValidationError as error:
        report["rejected_candidates"].append(
            _routing_entry(
                candidate_type=candidate_type,
                candidate_index=candidate_index,
                status="rejected",
                reason=str(error),
            )
        )
        return

    if _candidate_has_auto_high_risk(candidate):
        report["blocked_candidates"].append(
            _routing_entry(
                candidate_type=candidate_type,
                candidate_index=candidate_index,
                status="blocked_high_risk",
                reason="Medium/high-risk candidates cannot be marked auto_allowed.",
                candidate=candidate,
            )
        )
        return

    try:
        validated = validator(candidate, candidate_index)
    except (ValueError, TypeError) as error:
        report["rejected_candidates"].append(
            _routing_entry(
                candidate_type=candidate_type,
                candidate_index=candidate_index,
                status="blocked_malformed",
                reason=str(error),
                candidate=candidate if isinstance(candidate, Mapping) else None,
            )
        )
        return

    approval = rails.build_approval_result(validated["risk_level"], validated["approval_mode"])
    if approval["requires_approval"] or approval["manual_only"]:
        report["accepted_candidates"].append(
            _routing_entry(
                candidate_type=candidate_type,
                candidate_index=candidate_index,
                status="blocked_review_required",
                reason="Candidate is valid but requires review before any later write path.",
                candidate=validated,
                approval=approval,
            )
        )
        return

    report["accepted_candidates"].append(
        _routing_entry(
            candidate_type=candidate_type,
            candidate_index=candidate_index,
            status="accepted",
            reason="Candidate is valid for preview only; no external write was executed.",
            candidate=validated,
            approval=approval,
        )
    )


def _routing_entry(
    *,
    candidate_type: str,
    candidate_index: int,
    status: str,
    reason: str,
    candidate: Mapping[str, Any] | None = None,
    approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_choice("status", status, ROUTING_STATUSES)
    entry: dict[str, Any] = {
        "candidate_type": candidate_type,
        "candidate_index": candidate_index,
        "status": status,
        "reason": reason,
        "database_write": False,
        "external_mutation": False,
    }
    if candidate is not None:
        entry["candidate"] = dict(candidate)
    if approval is not None:
        entry["approval"] = dict(approval)
    return entry


def _candidate_has_auto_high_risk(candidate: Any) -> bool:
    return (
        isinstance(candidate, Mapping)
        and candidate.get("approval_mode") == "auto_allowed"
        and candidate.get("risk_level") in {"medium", "high"}
    )


def _routine_state_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "routine_id": routine["routine_id"],
            "name": routine["name"],
            "status": routine["status"],
            "enabled": routine["enabled"],
        }
        for routine in list_routines(connection)
    ]


def _priority_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "priority_id": priority["priority_id"],
            "title": priority["title"],
            "status": priority["status"],
            "summary": "",
        }
        for priority in list_priorities(connection)
    ]


def _followup_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "followup_id": followup["followup_id"],
            "title": followup["title"],
            "status": followup["status"],
            "source": followup["source"],
            "summary": "",
        }
        for followup in list_followups(connection)
    ]


def _todoist_task_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "todoist_task_id": task["todoist_task_id"],
            "task_title": task["task_title"],
            "project": task["project"],
            "due_date_or_due_string": task["due_date_or_due_string"],
            "risk_level": task["risk_level"],
            "approval_mode": task["approval_mode"],
            "status": task["status"],
        }
        for task in list_todoist_tasks(connection)
    ]


def _calendar_block_summaries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "calendar_block_id": block["calendar_block_id"],
            "title": block["title"],
            "start_time": block["start_time"],
            "end_time": block["end_time"],
            "duration_minutes": block["duration_minutes"],
            "calendar_id": block["calendar_id"],
            "risk_level": block["risk_level"],
            "approval_mode": block["approval_mode"],
            "status": block["status"],
        }
        for block in list_calendar_blocks(connection)
    ]


def _today_schedule_summary(
    connection: sqlite3.Connection,
    source_date: str,
) -> list[dict[str, Any]]:
    return [
        block
        for block in _calendar_block_summaries(connection)
        if block["start_time"].startswith(source_date)
    ]


def _require_fake_adapter(adapter: ComposerAdapter) -> None:
    if getattr(adapter, "dev_test_fake_adapter", False) is not True:
        raise ValueError("Composer model runs require a fake dev/test adapter.")
    if getattr(adapter, "adapter_name", None) != FAKE_COMPOSER_ADAPTER_NAME:
        raise ValueError("Composer model runs are limited to fake_composer_adapter.")


def _blocked_result(
    *,
    reason: str,
    permission: Mapping[str, Any],
    dry_run: bool,
    would_write: Mapping[str, Any] | None,
    record_type: str,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": dry_run,
        "no_send": True,
        "database_write": False,
        "external_mutation": False,
        "adapter_called": False,
        "permission": dict(permission),
        record_type: None,
        "would_write": dict(would_write) if would_write is not None else None,
    }


def _permission_decision(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": category,
        "mode": mode,
        "reason": reason,
        "setting": setting,
    }


def _parse_output_json(output_json: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(output_json, Mapping):
        return dict(output_json)
    if not isinstance(output_json, str):
        raise ComposerValidationError("output_json must be a structured JSON object.")
    try:
        parsed = json.loads(output_json)
    except json.JSONDecodeError as error:
        raise ComposerValidationError("output_json must be valid JSON, not prose only.") from error
    if not isinstance(parsed, dict):
        raise ComposerValidationError("output_json must decode to a JSON object.")
    return parsed


def _reject_forbidden_content(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ComposerValidationError(f"Composer content key at {path} must be a string.")
            _reject_forbidden_text(key, f"{path}.{key}")
            _reject_forbidden_content(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_content(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        _reject_forbidden_text(value, path)


def _reject_forbidden_text(value: str, path: str) -> None:
    normalized = _normalize_for_forbidden_scan(value)
    for term in FORBIDDEN_COMPOSER_TERMS:
        if term in normalized:
            raise ComposerValidationError(f"Forbidden Composer content at {path}: {term}.")
    if "/users/coldstake/" in value.lower() and "/users/coldstake/dev/personal-os" not in value.lower():
        raise ComposerValidationError(f"Forbidden raw path outside repo at {path}.")


def _normalize_for_forbidden_scan(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "_")
    )


def _validate_exact_keys(
    label: str,
    value: Mapping[str, Any],
    expected_keys: set[str],
) -> None:
    actual_keys = set(value.keys())
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if missing:
        raise ComposerValidationError(f"{label} missing required keys: {sorted(missing)}")
    if extra:
        raise ComposerValidationError(f"{label} has unsupported keys: {sorted(extra)}")


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ComposerValidationError(f"{field_name} must be a JSON object.")
    return dict(value)


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ComposerValidationError(f"{field_name} must be a list.")
    return list(value)


def _validate_literal(field_name: str, value: Any, expected: str) -> str:
    if value != expected:
        raise ComposerValidationError(f"{field_name} must be {expected}.")
    return expected


def _validate_choice(field_name: str, value: Any, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(choices)
        raise ComposerValidationError(f"{field_name} must be one of: {allowed}")
    return value


def _validate_timezone(value: Any) -> str:
    if value != DEFAULT_TIMEZONE:
        raise ComposerValidationError(f"timezone must be {DEFAULT_TIMEZONE}.")
    return DEFAULT_TIMEZONE


def _validate_required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ComposerValidationError(f"{field_name} must be a string.")
    if not value.strip():
        raise ComposerValidationError(f"{field_name} must not be empty.")
    return value


def _validate_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ComposerValidationError(f"{field_name} must be a string.")
    return value


def _validate_iso_date(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ComposerValidationError(f"{field_name} must be an ISO date.") from error
    return value


def _validate_iso_datetime(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ComposerValidationError(f"{field_name} must be an ISO datetime.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ComposerValidationError(f"{field_name} must include a timezone offset.")
    return value


def _normalize_todoist_priority(value: Any) -> int:
    if isinstance(value, str):
        if not value.isdigit():
            raise ComposerValidationError("Todoist priority string must be a digit.")
        value = int(value)
    return rails.validate_todoist_priority(value)


def _json_copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _fake_token_count(value: Mapping[str, Any]) -> int:
    serialized = json.dumps(value, allow_nan=False, ensure_ascii=True, sort_keys=True)
    return max(1, len(serialized) // 4)


def _redacted_error_message(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    _reject_forbidden_content({"error_message": message})
    return message


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

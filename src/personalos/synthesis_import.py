"""Preview-only intake for ChatGPT-synthesized Personal OS material."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from personalos import execution_rails as rails
from personalos.calendar_blocks import preview_calendar_block
from personalos.permissions import evaluate_auto_write_gate
from personalos.state import (
    SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS,
    count_synthesis_import_previews,
    create_synthesis_import_preview as insert_synthesis_import_preview,
    get_synthesis_import_preview,
    list_synthesis_import_previews,
    validate_followup_status,
    validate_priority_status,
    validate_project_status,
)
from personalos.todoist import preview_todoist_task

SYNTHESIS_IMPORT_READ_PERMISSION = "synthesis_import_dev_test_read"
SYNTHESIS_IMPORT_WRITE_PERMISSION = "synthesis_import_dev_test_write"
SYNTHESIS_IMPORT_PREVIEW_PERMISSION = "synthesis_import_dev_test_preview"

SYNTHESIS_IMPORT_SCHEMA_VERSION = "synthesis_import.v1"
ALLOWED_SOURCE_TYPES = ("chatgpt_synthesis", "manual_structured_import", "fake_fixture")
REJECTED_SOURCE_TYPES = (
    "raw_notes",
    "raw_journal",
    "full_vault_dump",
    "legal_source_documents",
    "tax_source_documents",
    "credential_dump",
    "unrestricted_file_input",
)
INPUT_FORMATS = ("json", "markdown_fenced_json", "structured_markdown")
CANDIDATE_SECTIONS = (
    "priorities",
    "projects",
    "followups",
    "routine_changes",
    "todoist_tasks",
    "calendar_blocks",
    "clarity_notes",
    "review_questions",
)
ROUTINE_CHANGE_TYPES = ("create", "update", "disable", "review")
APPROVAL_MODES = ("auto_allowed", "approval_required", "manual_only")
REPORT_SAFETY_FLAGS = {
    "no_external_writes": True,
    "no_state_mutation": True,
    "no_personalos_writes": True,
    "no_todoist_writes": True,
    "no_calendar_writes": True,
    "no_gmail_send": True,
    "no_live_model_call": True,
}

_FENCED_JSON_RE = re.compile(r"```json\s*\n(?P<body>.*?)\n```", re.IGNORECASE | re.DOTALL)
_SENSITIVE_INPUT_MARKERS = (
    "credential",
    "credentials",
    "client" + "_" + "sec" + "ret",
    "token" + "." + "json",
    "api" + "_" + "key",
    "o" + "auth",
    "pass" + "word",
    "sec" + "ret",
    "aws_access_key_id",
    "begin private key",
    "/users/" + "coldstake/" + "personalos",
    "/users/" + "coldstake/" + ".openclaw",
)
_HIGH_STAKES_TERMS = (
    "tax",
    "legal",
    "estate",
    "portfolio",
    "crypto",
    "investment",
    "investments",
    "health",
    "medical",
    "relationship message",
    "family-sensitive",
    "family sensitive",
    "large financial commitment",
)
_FINANCIAL_EXECUTION_TERMS = (
    "buy",
    "sell",
    "rotate",
    "rebalance",
    "allocate",
    "exit",
    "enter",
    "long",
    "short",
)
_DIRECTIVE_TERMS = (
    "file",
    "submit",
    "sign",
    "send",
    "diagnose",
    "treat",
    "prescribe",
    "execute",
    "commit",
)
_RELATIONSHIP_TERMS = (
    "relationship message",
    "family-sensitive",
    "family sensitive",
    "message spouse",
    "message family",
    "text spouse",
    "text family",
)
_EXTERNAL_ATTENDEE_FIELDS = (
    "attendees",
    "external_attendees",
    "external_people",
    "recipient",
    "message_to",
)
_SECTION_HEADINGS = {
    "priorities": "priorities",
    "priority candidates": "priorities",
    "projects": "projects",
    "project candidates": "projects",
    "followups": "followups",
    "follow-ups": "followups",
    "follow up candidates": "followups",
    "routine changes": "routine_changes",
    "routine change candidates": "routine_changes",
    "todoist tasks": "todoist_tasks",
    "todoist task candidates": "todoist_tasks",
    "calendar blocks": "calendar_blocks",
    "calendar block candidates": "calendar_blocks",
    "clarity notes": "clarity_notes",
    "clarity note candidates": "clarity_notes",
    "review questions": "review_questions",
    "questions": "review_questions",
    "warnings": "warnings",
}
_TOP_LEVEL_KEYS = {
    "schema version": "schema_version",
    "source type": "source_type",
    "source timestamp": "source_timestamp",
    "source reference": "source_reference",
    "summary": "summary",
}


class SynthesisImportPermissionDenied(PermissionError):
    """Raised when synthesis import preview permissions do not allow the action."""


class SynthesisImportValidationError(ValueError):
    """Raised when synthesis import input cannot be parsed or validated safely."""


class SynthesisImportCandidateBlocked(ValueError):
    """Raised for schema-valid candidates blocked by safety policy."""


def parse_synthesis_import(raw_input: str) -> dict[str, Any]:
    text = _validate_raw_input(raw_input)
    _reject_sensitive_input(text)
    parsed, input_format = _parse_supported_input(text)
    normalized = _normalize_import_payload(parsed)
    return {
        "input_format": input_format,
        "parsed_import": normalized,
        "input_hash": stable_input_hash(text),
        "raw_excerpt": bounded_raw_excerpt(text),
    }


def build_synthesis_import_preview(raw_input: str) -> dict[str, Any]:
    parsed = parse_synthesis_import(raw_input)
    parsed_import = parsed["parsed_import"]
    report = _build_preview_report(
        parsed_import,
        input_format=parsed["input_format"],
        input_hash=parsed["input_hash"],
    )
    return {
        "input_format": parsed["input_format"],
        "input_hash": parsed["input_hash"],
        "raw_excerpt": parsed["raw_excerpt"],
        "parsed_import": parsed_import,
        "preview_report": report,
        **REPORT_SAFETY_FLAGS,
    }


def create_synthesis_import_preview_record(
    connection: sqlite3.Connection,
    raw_input: str,
    *,
    status: str = "validated",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    preview = build_synthesis_import_preview(raw_input)
    preview_permission = evaluate_synthesis_import_permission(
        connection,
        category=SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    )
    write_permission = evaluate_synthesis_import_permission(
        connection,
        category=SYNTHESIS_IMPORT_WRITE_PERMISSION,
    )
    denied = next(
        (
            permission
            for permission in (preview_permission, write_permission)
            if not permission["allowed"]
        ),
        None,
    )
    if denied is not None:
        return _blocked_result(
            reason=denied["reason"],
            permissions={"preview": preview_permission, "write": write_permission},
            preview=preview,
        )

    parsed_import = preview["parsed_import"]
    report = preview["preview_report"]
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)
    record = insert_synthesis_import_preview(
        connection,
        preview_id=report["preview_id"],
        source_type=parsed_import["source_type"],
        input_format=preview["input_format"],
        input_hash=preview["input_hash"],
        source_timestamp=parsed_import["source_timestamp"],
        source_reference=parsed_import["source_reference"],
        raw_excerpt=preview["raw_excerpt"],
        parsed_json=parsed_import,
        preview_report_json=report,
        status=status,
        created_at=created,
        updated_at=updated,
    )
    return {
        "status": "created",
        "reason": "Synthesis import preview was persisted in the dev/test SQLite database only.",
        "dry_run": False,
        "database_write": True,
        "external_mutation": False,
        "permission": {"preview": preview_permission, "write": write_permission},
        "preview_report": report,
        "record": record,
        "would_write": {
            "preview_id": report["preview_id"],
            "source_type": parsed_import["source_type"],
            "input_format": preview["input_format"],
            "input_hash": preview["input_hash"],
            "status": status,
        },
        **REPORT_SAFETY_FLAGS,
    }


def read_synthesis_import_preview(
    connection: sqlite3.Connection,
    *,
    preview_id: str,
) -> dict[str, Any] | None:
    require_synthesis_import_permission(
        connection,
        category=SYNTHESIS_IMPORT_READ_PERMISSION,
    )
    return get_synthesis_import_preview(connection, preview_id)


def read_synthesis_import_previews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    input_format: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_synthesis_import_permission(
        connection,
        category=SYNTHESIS_IMPORT_READ_PERMISSION,
    )
    return list_synthesis_import_previews(
        connection,
        source_type=source_type,
        input_format=input_format,
        status=status,
    )


def read_synthesis_import_preview_count(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    input_format: str | None = None,
    status: str | None = None,
) -> int:
    require_synthesis_import_permission(
        connection,
        category=SYNTHESIS_IMPORT_READ_PERMISSION,
    )
    return count_synthesis_import_previews(
        connection,
        source_type=source_type,
        input_format=input_format,
        status=status,
    )


def validate_synthesis_import_candidate_for_apply(
    section: str,
    candidate: Any,
    *,
    index: int,
) -> dict[str, Any]:
    """Validate a stored preview candidate again before any later apply step."""
    section = _validate_choice("section", section, CANDIDATE_SECTIONS)
    if section == "review_questions":
        raise SynthesisImportValidationError("Review questions are not apply candidates.")

    normalized = _validate_action_candidate(section, candidate, index=index)
    block_reason = _candidate_safety_block_reason(section, normalized)
    if block_reason is not None:
        raise SynthesisImportCandidateBlocked(block_reason)
    return normalized


def require_synthesis_import_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_synthesis_import_permission(connection, category=category)
    if not decision["allowed"]:
        raise SynthesisImportPermissionDenied(decision["reason"])
    return decision


def evaluate_synthesis_import_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = rails.validate_required_text("category", category)
    return evaluate_auto_write_gate(
        connection,
        category=category,
        missing_reason=lambda: f"Missing synthesis import permission setting: {category}",
        invalid_reason=lambda raw_mode: f"Invalid synthesis import permission mode: {raw_mode}",
        disabled_reason=lambda: f"Synthesis import permission is disabled: {category}",
        not_auto_write_reason=(
            lambda _mode_value: f"Synthesis import permission is not enabled for dev/test use: {category}"
        ),
        success_reason="Synthesis import permission is explicitly enabled for dev/test use.",
    )


def stable_input_hash(raw_input: str) -> str:
    return hashlib.sha256(_validate_raw_input(raw_input).encode("utf-8")).hexdigest()


def stable_synthesis_import_id(prefix: str, material: str) -> str:
    normalized_prefix = rails.normalize_for_dedupe(
        rails.validate_required_text("prefix", prefix)
    ).replace(" ", "-")
    material = rails.validate_required_text("material", material)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"{normalized_prefix}-{digest[:16]}"


def bounded_raw_excerpt(raw_input: str) -> str:
    text = _validate_raw_input(raw_input)
    return text[:SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS]


def _parse_supported_input(raw_input: str) -> tuple[dict[str, Any], str]:
    stripped = raw_input.strip()
    if stripped.startswith("{"):
        return _parse_json_object(stripped), "json"

    fenced = list(_FENCED_JSON_RE.finditer(stripped))
    if fenced:
        if len(fenced) > 1:
            raise SynthesisImportValidationError("Only one fenced JSON block is supported.")
        return _parse_json_object(fenced[0].group("body").strip()), "markdown_fenced_json"

    if _looks_like_structured_markdown(stripped):
        return _parse_structured_markdown(stripped), "structured_markdown"

    raise SynthesisImportValidationError(
        "Unsupported synthesis import format. Provide canonical JSON, Markdown with one "
        "fenced JSON block, or the documented structured Markdown subset."
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise SynthesisImportValidationError("Synthesis import JSON is malformed.") from error
    if not isinstance(parsed, dict):
        raise SynthesisImportValidationError("Synthesis import JSON must be an object.")
    return parsed


def _parse_structured_markdown(text: str) -> dict[str, Any]:
    top_level: dict[str, Any] = {}
    candidates: dict[str, list[Any]] = {section: [] for section in CANDIDATE_SECTIONS}
    warnings: list[Any] = []
    current_section: str | None = None
    current_item: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            current_section = _SECTION_HEADINGS.get(heading)
            current_item = None
            continue

        if current_section is None:
            key, value = _split_markdown_key_value(stripped)
            normalized_key = _TOP_LEVEL_KEYS.get(key.lower())
            if normalized_key is not None:
                top_level[normalized_key] = _parse_markdown_scalar(value)
            continue

        if current_section == "warnings":
            if not stripped.startswith("- "):
                raise SynthesisImportValidationError("Warnings must use Markdown bullet items.")
            warning_text = stripped[2:].strip()
            warnings.append(_parse_warning_markdown_value(warning_text))
            continue

        if stripped.startswith("- "):
            current_item = {}
            candidates[current_section].append(current_item)
            _assign_markdown_candidate_value(current_item, stripped[2:].strip())
            continue

        if current_item is None or not raw_line.startswith((" ", "\t")):
            raise SynthesisImportValidationError(
                "Structured Markdown candidates must use bullet items with "
                "indented key/value lines."
            )
        _assign_markdown_candidate_value(current_item, stripped)

    if not all(key in top_level for key in ("source_type", "summary")):
        raise SynthesisImportValidationError(
            "Structured Markdown must include Source Type and Summary fields."
        )

    top_level.setdefault("schema_version", SYNTHESIS_IMPORT_SCHEMA_VERSION)
    top_level.setdefault("source_timestamp", None)
    top_level.setdefault("source_reference", None)
    top_level["candidates"] = candidates
    top_level["warnings"] = warnings
    return top_level


def _normalize_import_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    _reject_forbidden_payload_source(payload)
    schema_version = _validate_literal(
        "schema_version",
        payload.get("schema_version"),
        SYNTHESIS_IMPORT_SCHEMA_VERSION,
    )
    source_type = _validate_source_type(payload.get("source_type"))
    source_timestamp = _validate_optional_iso_datetime(
        "source_timestamp",
        payload.get("source_timestamp"),
    )
    source_reference = _validate_optional_text("source_reference", payload.get("source_reference"))
    summary = _validate_required_text("summary", payload.get("summary"))
    candidates = _normalize_candidates(payload.get("candidates"))
    warnings = _normalize_warning_list(payload.get("warnings", []))

    return {
        "schema_version": schema_version,
        "source_type": source_type,
        "source_timestamp": source_timestamp,
        "source_reference": source_reference,
        "summary": summary,
        "candidates": candidates,
        "warnings": warnings,
    }


def _normalize_candidates(value: Any) -> dict[str, list[Any]]:
    if not isinstance(value, Mapping):
        raise SynthesisImportValidationError("candidates must be an object.")
    unknown = set(value) - set(CANDIDATE_SECTIONS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SynthesisImportValidationError(f"Unsupported candidate section(s): {names}")

    normalized: dict[str, list[Any]] = {}
    for section in CANDIDATE_SECTIONS:
        items = value.get(section, [])
        if not isinstance(items, list):
            raise SynthesisImportValidationError(f"candidates.{section} must be a list.")
        normalized[section] = [_json_copy(item) for item in items]
    return normalized


def _build_preview_report(
    parsed_import: Mapping[str, Any],
    *,
    input_format: str,
    input_hash: str,
) -> dict[str, Any]:
    preview_id = stable_synthesis_import_id("synthesis-import-preview", input_hash)
    report: dict[str, Any] = {
        "preview_id": preview_id,
        "source_type": parsed_import["source_type"],
        "input_format": _validate_choice("input_format", input_format, INPUT_FORMATS),
        "candidate_counts": _candidate_counts(parsed_import["candidates"]),
        "accepted_candidates": [],
        "rejected_candidates": [],
        "blocked_candidates": [],
        "review_required_candidates": [],
        "manual_only_candidates": [],
        "warnings": list(parsed_import["warnings"]),
        "questions_for_review": [],
        **REPORT_SAFETY_FLAGS,
    }

    for section in CANDIDATE_SECTIONS:
        for index, candidate in enumerate(parsed_import["candidates"][section]):
            _route_preview_candidate(report, section=section, index=index, candidate=candidate)

    return report


def _route_preview_candidate(
    report: dict[str, Any],
    *,
    section: str,
    index: int,
    candidate: Any,
) -> None:
    candidate_ref = f"{section}[{index}]"
    try:
        if section == "review_questions":
            question = _validate_review_question_candidate(candidate, index=index)
            report["questions_for_review"].append(question)
            return

        normalized = _validate_action_candidate(section, candidate, index=index)
        block_reason = _candidate_safety_block_reason(section, normalized)
        if block_reason is not None:
            raise SynthesisImportCandidateBlocked(block_reason)
    except SynthesisImportCandidateBlocked as error:
        report["blocked_candidates"].append(
            _candidate_report_entry(
                candidate_ref=candidate_ref,
                candidate_type=section,
                status="blocked",
                reason=str(error),
                candidate=candidate if isinstance(candidate, Mapping) else None,
            )
        )
        return
    except (SynthesisImportValidationError, ValueError, TypeError) as error:
        report["rejected_candidates"].append(
            _candidate_report_entry(
                candidate_ref=candidate_ref,
                candidate_type=section,
                status="rejected",
                reason=str(error),
                candidate=candidate if isinstance(candidate, Mapping) else None,
            )
        )
        return

    approval = rails.build_approval_result(normalized["risk_level"], normalized["approval_mode"])
    if approval["manual_only"]:
        report["manual_only_candidates"].append(
            _candidate_report_entry(
                candidate_ref=candidate_ref,
                candidate_type=section,
                status="manual_only",
                reason="Candidate is valid for preview and marked manual_only.",
                candidate=normalized,
                approval=approval,
            )
        )
        return
    if approval["requires_approval"]:
        report["review_required_candidates"].append(
            _candidate_report_entry(
                candidate_ref=candidate_ref,
                candidate_type=section,
                status="review_required",
                reason=(
                    "Candidate is valid for preview and requires approval before "
                    "any later write path."
                ),
                candidate=normalized,
                approval=approval,
            )
        )
        return

    report["accepted_candidates"].append(
        _candidate_report_entry(
            candidate_ref=candidate_ref,
            candidate_type=section,
            status="accepted",
            reason="Candidate is valid for preview only; no state or external write was executed.",
            candidate=normalized,
            approval=approval,
        )
    )


def _validate_action_candidate(section: str, candidate: Any, *, index: int) -> dict[str, Any]:
    if section == "priorities":
        return _validate_priority_candidate(candidate, index=index)
    if section == "projects":
        return _validate_project_candidate(candidate, index=index)
    if section == "followups":
        return _validate_followup_candidate(candidate, index=index)
    if section == "routine_changes":
        return _validate_routine_change_candidate(candidate, index=index)
    if section == "todoist_tasks":
        return _validate_todoist_candidate(candidate, index=index)
    if section == "calendar_blocks":
        return _validate_calendar_candidate(candidate, index=index)
    if section == "clarity_notes":
        return _validate_clarity_note_candidate(candidate, index=index)
    raise SynthesisImportValidationError(f"Unsupported candidate section: {section}")


def _validate_priority_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"priorities[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "title",
            "summary",
            "source_type",
            "source_id",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={"review_cadence", "review_note", "domain"},
        item_ref=f"priorities[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    normalized = {
        "title": _validate_required_text("title", item["title"]),
        "summary": _validate_required_text("summary", item["summary"]),
        "source_type": _validate_candidate_source_type(item["source_type"]),
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": validate_priority_status(item["status"]),
    }
    return _with_optional_fields(normalized, item, ("review_cadence", "review_note", "domain"))


def _validate_project_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"projects[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "title",
            "summary",
            "source_type",
            "source_id",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={"review_note", "domain"},
        item_ref=f"projects[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    normalized = {
        "title": _validate_required_text("title", item["title"]),
        "summary": _validate_required_text("summary", item["summary"]),
        "source_type": _validate_candidate_source_type(item["source_type"]),
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": validate_project_status(item["status"]),
    }
    return _with_optional_fields(normalized, item, ("review_note", "domain"))


def _validate_followup_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"followups[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "title",
            "summary",
            "source_type",
            "source_id",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={"due_date_or_review_note", "domain", "recipient", "message_to"},
        item_ref=f"followups[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    normalized = {
        "title": _validate_required_text("title", item["title"]),
        "summary": _validate_required_text("summary", item["summary"]),
        "source_type": _validate_candidate_source_type(item["source_type"]),
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": validate_followup_status(item["status"]),
    }
    return _with_optional_fields(
        normalized,
        item,
        ("due_date_or_review_note", "domain", "recipient", "message_to"),
    )


def _validate_routine_change_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"routine_changes[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "routine_name",
            "change_type",
            "summary",
            "proposed_fields",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={"domain"},
        item_ref=f"routine_changes[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    proposed_fields = item["proposed_fields"]
    if not isinstance(proposed_fields, Mapping):
        raise SynthesisImportValidationError("proposed_fields must be an object.")
    normalized = {
        "routine_name": _validate_required_text("routine_name", item["routine_name"]),
        "change_type": _validate_choice("change_type", item["change_type"], ROUTINE_CHANGE_TYPES),
        "summary": _validate_required_text("summary", item["summary"]),
        "proposed_fields": _json_copy(proposed_fields),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": _validate_required_text("status", item["status"]),
    }
    return _with_optional_fields(normalized, item, ("domain",))


def _validate_todoist_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"todoist_tasks[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "source_type",
            "source_id",
            "project",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={
            "task_title",
            "title",
            "description",
            "labels",
            "due_date_or_due_string",
            "priority",
            "dedupe_key",
            "domain",
            "recipient",
            "message_to",
        },
        item_ref=f"todoist_tasks[{index}]",
    )
    title = item.get("task_title", item.get("title"))
    risk_level, approval_mode = _validate_risk_and_approval(item)
    labels = _normalize_labels(item.get("labels", []))
    priority = _normalize_integer("priority", item.get("priority", 1))
    normalized = {
        "task_title": _validate_required_text("task_title", title),
        "description": _validate_text("description", item.get("description", "")),
        "source_type": _validate_candidate_source_type(item["source_type"]),
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "project": _validate_required_text("project", item["project"]),
        "labels": labels,
        "due_date_or_due_string": _validate_text(
            "due_date_or_due_string",
            item.get("due_date_or_due_string", ""),
        ),
        "priority": priority,
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": _validate_required_text("status", item["status"]),
    }
    if item.get("dedupe_key") is not None:
        normalized["dedupe_key"] = rails.normalize_dedupe_key(item["dedupe_key"])
    normalized = _with_optional_fields(normalized, item, ("domain", "recipient", "message_to"))
    preview_input = {
        key: value
        for key, value in normalized.items()
        if key not in {"domain", "recipient", "message_to"}
    }
    preview_todoist_task(**preview_input)
    return normalized


def _validate_calendar_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"calendar_blocks[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "title",
            "source_type",
            "source_id",
            "start_time",
            "end_time",
            "duration_minutes",
            "calendar_id",
            "timezone",
            "approval_mode",
            "risk_level",
            "status",
        },
        optional={
            "description",
            "dedupe_key",
            "domain",
            "attendees",
            "external_attendees",
            "external_people",
            "recipient",
            "message_to",
            "is_external_meeting",
        },
        item_ref=f"calendar_blocks[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    normalized = {
        "title": _validate_required_text("title", item["title"]),
        "description": _validate_text("description", item.get("description", "")),
        "source_type": _validate_candidate_source_type(item["source_type"]),
        "source_id": _validate_required_text("source_id", item["source_id"]),
        "start_time": _validate_required_text("start_time", item["start_time"]),
        "end_time": _validate_required_text("end_time", item["end_time"]),
        "duration_minutes": _normalize_integer("duration_minutes", item["duration_minutes"]),
        "calendar_id": _validate_required_text("calendar_id", item["calendar_id"]),
        "timezone": _validate_required_text("timezone", item["timezone"]),
        "approval_mode": approval_mode,
        "risk_level": risk_level,
        "status": _validate_required_text("status", item["status"]),
    }
    if item.get("dedupe_key") is not None:
        normalized["dedupe_key"] = rails.normalize_dedupe_key(item["dedupe_key"])
    normalized = _with_optional_fields(
        normalized,
        item,
        (
            "domain",
            "attendees",
            "external_attendees",
            "external_people",
            "recipient",
            "message_to",
            "is_external_meeting",
        ),
    )
    preview_input = {
        key: value
        for key, value in normalized.items()
        if key
        not in {
            "domain",
            "attendees",
            "external_attendees",
            "external_people",
            "recipient",
            "message_to",
            "is_external_meeting",
        }
    }
    preview_calendar_block(**preview_input)
    return normalized


def _validate_clarity_note_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"clarity_notes[{index}]")
    _validate_candidate_keys(
        item,
        required={
            "title",
            "summary",
            "category",
            "source_reference",
            "durable_insight",
            "risk_level",
            "approval_mode",
            "status",
        },
        optional={"domain"},
        item_ref=f"clarity_notes[{index}]",
    )
    risk_level, approval_mode = _validate_risk_and_approval(item)
    normalized = {
        "title": _validate_required_text("title", item["title"]),
        "summary": _validate_required_text("summary", item["summary"]),
        "category": _validate_required_text("category", item["category"]),
        "source_reference": _validate_required_text("source_reference", item["source_reference"]),
        "durable_insight": _validate_required_text("durable_insight", item["durable_insight"]),
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": _validate_required_text("status", item["status"]),
    }
    return _with_optional_fields(normalized, item, ("domain",))


def _validate_review_question_candidate(candidate: Any, *, index: int) -> dict[str, Any]:
    item = _require_mapping(candidate, f"review_questions[{index}]")
    _validate_candidate_keys(
        item,
        required={"question", "reason", "candidate_refs", "status"},
        optional=set(),
        item_ref=f"review_questions[{index}]",
    )
    return {
        "question": _validate_required_text("question", item["question"]),
        "reason": _validate_required_text("reason", item["reason"]),
        "candidate_refs": _validate_string_list("candidate_refs", item["candidate_refs"]),
        "status": _validate_required_text("status", item["status"]),
    }


def _validate_risk_and_approval(item: Mapping[str, Any]) -> tuple[str, str]:
    risk_level = rails.validate_risk_level(
        _validate_required_text("risk_level", item.get("risk_level"))
    )
    approval_mode_raw = _validate_required_text("approval_mode", item.get("approval_mode"))
    if approval_mode_raw not in APPROVAL_MODES:
        allowed = ", ".join(APPROVAL_MODES)
        raise SynthesisImportValidationError(f"approval_mode must be one of: {allowed}")
    if approval_mode_raw == "auto_allowed" and risk_level != "low":
        raise SynthesisImportCandidateBlocked(
            "Medium/high-risk candidates cannot be marked auto_allowed."
        )
    approval_mode = rails.validate_approval_mode(approval_mode_raw, risk_level=risk_level)
    return risk_level, approval_mode


def _candidate_safety_block_reason(section: str, candidate: Mapping[str, Any]) -> str | None:
    text = _candidate_text(candidate)
    risk_level = candidate["risk_level"]
    approval_mode = candidate["approval_mode"]
    has_high_stakes = _contains_any(text, _HIGH_STAKES_TERMS)

    if _is_external_calendar_candidate(section, candidate):
        if risk_level != "high" or approval_mode == "auto_allowed":
            return (
                "External meetings or other-person calendar events must be high risk "
                "and approval_required or manual_only."
            )

    if _is_relationship_message_candidate(candidate, text):
        if risk_level != "high" or approval_mode == "auto_allowed":
            return (
                "Relationship or family-sensitive messages must be high risk and "
                "approval_required or manual_only."
            )

    if _contains_financial_execution(text):
        if risk_level != "high" or approval_mode == "auto_allowed":
            return (
                "Portfolio, crypto, or investment execution language must be high risk "
                "and approval_required or manual_only."
            )

    if _contains_legal_tax_medical_directive(text):
        if risk_level != "high" or approval_mode == "auto_allowed":
            return (
                "Legal, tax, or medical directives must be high risk and "
                "approval_required or manual_only."
            )

    if has_high_stakes and (risk_level != "high" or approval_mode == "auto_allowed"):
        return "High-stakes domains must be high risk and approval_required or manual_only."

    return None


def _is_external_calendar_candidate(section: str, candidate: Mapping[str, Any]) -> bool:
    if section != "calendar_blocks":
        return False
    if candidate.get("is_external_meeting") is True:
        return True
    for field_name in _EXTERNAL_ATTENDEE_FIELDS:
        value = candidate.get(field_name)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, Sequence) and not isinstance(value, str) and len(value) > 0:
            return True
    calendar_id = str(candidate.get("calendar_id", "")).strip().lower()
    return calendar_id not in {"primary", "self", "personal"}


def _is_relationship_message_candidate(candidate: Mapping[str, Any], text: str) -> bool:
    if any(candidate.get(field) for field in ("recipient", "message_to")):
        return True
    return _contains_any(text, _RELATIONSHIP_TERMS)


def _contains_financial_execution(text: str) -> bool:
    financial = _contains_any(text, ("portfolio", "crypto", "investment", "investments"))
    execution = _contains_any(text, _FINANCIAL_EXECUTION_TERMS)
    return financial and execution


def _contains_legal_tax_medical_directive(text: str) -> bool:
    domain = _contains_any(text, ("legal", "tax", "medical", "health"))
    directive = _contains_any(text, _DIRECTIVE_TERMS)
    return domain and directive


def _candidate_counts(candidates: Mapping[str, Any]) -> dict[str, int]:
    counts = {section: len(candidates[section]) for section in CANDIDATE_SECTIONS}
    counts["total"] = sum(counts.values())
    return counts


def _candidate_report_entry(
    *,
    candidate_ref: str,
    candidate_type: str,
    status: str,
    reason: str,
    candidate: Mapping[str, Any] | None = None,
    approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "candidate_ref": candidate_ref,
        "candidate_type": candidate_type,
        "status": status,
        "reason": reason,
        "database_write": False,
        "external_mutation": False,
    }
    if candidate is not None:
        entry["candidate"] = _json_copy(candidate)
    if approval is not None:
        entry["approval"] = dict(approval)
    return entry


def _blocked_result(
    *,
    reason: str,
    permissions: Mapping[str, Any],
    preview: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": False,
        "database_write": False,
        "external_mutation": False,
        "permission": _json_copy(permissions),
        "preview_report": _json_copy(preview["preview_report"]),
        "record": None,
        "would_write": None,
        **REPORT_SAFETY_FLAGS,
    }


def _reject_sensitive_input(raw_input: str) -> None:
    lowered = raw_input.lower()
    for marker in _SENSITIVE_INPUT_MARKERS:
        if marker in lowered:
            raise SynthesisImportValidationError(
                "Synthesis import input appears to include credential-like or protected material."
            )


def _reject_forbidden_payload_source(payload: Mapping[str, Any]) -> None:
    source_type = payload.get("source_type")
    if source_type in REJECTED_SOURCE_TYPES:
        raise SynthesisImportValidationError(
            f"source_type {source_type} is rejected; provide structured ChatGPT synthesis instead."
        )


def _validate_source_type(value: Any) -> str:
    source_type = _validate_required_text("source_type", value)
    if source_type in REJECTED_SOURCE_TYPES:
        raise SynthesisImportValidationError(
            f"source_type {source_type} is rejected; provide structured ChatGPT synthesis instead."
        )
    return _validate_choice("source_type", source_type, ALLOWED_SOURCE_TYPES)


def _validate_candidate_source_type(value: Any) -> str:
    source_type = _validate_required_text("source_type", value)
    if source_type in REJECTED_SOURCE_TYPES:
        raise SynthesisImportValidationError(f"candidate source_type {source_type} is rejected.")
    return source_type


def _validate_candidate_keys(
    item: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str],
    item_ref: str,
) -> None:
    missing = required - set(item)
    if missing:
        names = ", ".join(sorted(missing))
        raise SynthesisImportValidationError(f"{item_ref} missing required field(s): {names}")
    unknown = set(item) - required - optional
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SynthesisImportValidationError(f"{item_ref} has unsupported field(s): {names}")


def _with_optional_fields(
    normalized: dict[str, Any],
    item: Mapping[str, Any],
    field_names: Sequence[str],
) -> dict[str, Any]:
    for field_name in field_names:
        if field_name not in item:
            continue
        value = item[field_name]
        if value is None:
            normalized[field_name] = None
        elif isinstance(value, (str, int, float, bool, list, dict)):
            normalized[field_name] = _json_copy(value)
        else:
            raise SynthesisImportValidationError(f"{field_name} must be JSON-safe.")
    return normalized


def _normalize_warning_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise SynthesisImportValidationError("warnings must be a list.")
    return [_json_copy(item) for item in value]


def _normalize_labels(value: Any) -> list[str]:
    if isinstance(value, str):
        labels = [part.strip() for part in value.split(",") if part.strip()]
        return rails.validate_labels(labels)
    return rails.validate_labels(value)


def _normalize_integer(field_name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise SynthesisImportValidationError(f"{field_name} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise SynthesisImportValidationError(f"{field_name} must be an integer.")


def _looks_like_structured_markdown(text: str) -> bool:
    lowered = text.lower()
    return "source type:" in lowered and "summary:" in lowered and any(
        f"## {heading}" in lowered for heading in _SECTION_HEADINGS
    )


def _assign_markdown_candidate_value(item: dict[str, Any], text: str) -> None:
    key, value = _split_markdown_key_value(text)
    item[key.lower().replace(" ", "_").replace("-", "_")] = _parse_markdown_scalar(value)


def _split_markdown_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise SynthesisImportValidationError("Structured Markdown values must use key: value.")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise SynthesisImportValidationError("Structured Markdown key must not be empty.")
    return key, value.strip()


def _parse_markdown_scalar(value: str) -> Any:
    if value.lower() == "null":
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith(("{", "[")):
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise SynthesisImportValidationError(
                "Structured Markdown JSON value is malformed."
            ) from error
    if value.isdigit():
        return int(value)
    return value


def _parse_warning_markdown_value(value: str) -> Any:
    if ":" not in value:
        return value
    key, parsed = _split_markdown_key_value(value)
    if key.lower() == "message":
        return parsed
    return {key.lower().replace(" ", "_"): _parse_markdown_scalar(parsed)}


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    return json.dumps(
        _json_copy(candidate),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).lower()


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    return any(term in text for term in terms)


def _validate_raw_input(raw_input: str) -> str:
    if not isinstance(raw_input, str):
        raise SynthesisImportValidationError("synthesis import input must be a string.")
    if not raw_input.strip():
        raise SynthesisImportValidationError("synthesis import input must not be empty.")
    return raw_input


def _validate_literal(field_name: str, value: Any, expected: str) -> str:
    if value != expected:
        raise SynthesisImportValidationError(f"{field_name} must be {expected}.")
    return expected


def _validate_choice(field_name: str, value: Any, choices: Sequence[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        allowed = ", ".join(choices)
        raise SynthesisImportValidationError(f"{field_name} must be one of: {allowed}")
    return value


def _validate_required_text(field_name: str, value: Any) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise SynthesisImportValidationError(f"{field_name} must not be empty.")
    return value


def _validate_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise SynthesisImportValidationError(f"{field_name} must be a string.")
    return value


def _validate_optional_text(field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _validate_text(field_name, value)


def _validate_optional_iso_datetime(field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _validate_iso_datetime(field_name, value)


def _validate_iso_datetime(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SynthesisImportValidationError(f"{field_name} must be an ISO datetime.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SynthesisImportValidationError(f"{field_name} must include a timezone offset.")
    return value


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SynthesisImportValidationError(f"{field_name} must be an object.")
    return dict(value)


def _validate_string_list(field_name: str, value: Any) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, Sequence):
        items = list(value)
    else:
        raise SynthesisImportValidationError(f"{field_name} must be a list of strings.")
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise SynthesisImportValidationError(f"{field_name} must contain non-empty strings.")
    return items


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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

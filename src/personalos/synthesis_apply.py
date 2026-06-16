"""Approval-gated apply flow for ChatGPT synthesis import previews."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from personalos import execution_rails as rails
from personalos.permissions import PermissionMode
from personalos.state import (
    create_followup,
    create_priority,
    create_project,
    get_followup,
    get_permission_setting,
    get_priority,
    get_project,
    get_synthesis_import_preview,
    update_synthesis_import_preview_status,
)
from personalos.synthesis_import import (
    CANDIDATE_SECTIONS,
    SynthesisImportCandidateBlocked,
    SynthesisImportValidationError,
    validate_synthesis_import_candidate_for_apply,
)

SYNTHESIS_APPLY_READ_PERMISSION = "synthesis_apply_dev_test_read"
SYNTHESIS_APPLY_WRITE_PERMISSION = "synthesis_apply_dev_test_write"
SYNTHESIS_APPLY_APPLY_PERMISSION = "synthesis_apply_dev_test_apply"

ALLOWED_APPLY_SECTIONS = ("priorities", "projects", "followups")
SUPPORTED_TARGET_TABLES = {
    "priorities": "priorities",
    "projects": "projects",
    "followups": "followups",
}
SYNTHESIS_APPLY_RUN_STATUSES = (
    "completed",
    "partially_completed",
    "blocked",
    "failed",
    "no_op",
)
SYNTHESIS_APPLY_APPROVAL_STATUSES = (
    "approved",
    "rejected",
    "blocked",
    "unsupported",
    "skipped",
    "review_required",
)
SYNTHESIS_APPLY_ITEM_STATUSES = (
    "applied",
    "not_applied",
    "blocked",
    "skipped_duplicate",
    "failed",
)
APPLY_SAFETY_FLAGS = {
    "no_external_writes": True,
    "no_send_mode": True,
    "live_write": False,
    "internal_state_mutation": True,
    "no_todoist_writes": True,
    "no_calendar_writes": True,
    "no_gmail_send": True,
    "no_personalos_writes": True,
    "no_live_model_call": True,
}

_CANDIDATE_TYPE_ALIASES = {
    "priority": "priorities",
    "priorities": "priorities",
    "project": "projects",
    "projects": "projects",
    "followup": "followups",
    "follow_up": "followups",
    "followups": "followups",
    "follow-up": "followups",
    "follow_ups": "followups",
    "routine_change": "routine_changes",
    "routine_changes": "routine_changes",
    "todoist_task": "todoist_tasks",
    "todoist_tasks": "todoist_tasks",
    "calendar_block": "calendar_blocks",
    "calendar_blocks": "calendar_blocks",
    "clarity_note": "clarity_notes",
    "clarity_notes": "clarity_notes",
    "review_question": "review_questions",
    "review_questions": "review_questions",
}
_HIGH_STAKES_APPLY_TERMS = (
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


class SynthesisApplyPermissionDenied(PermissionError):
    """Raised when synthesis apply permissions do not allow the action."""


class SynthesisApplyValidationError(ValueError):
    """Raised when an approval apply request is malformed or unsafe."""


def apply_synthesis_import_preview(
    connection: sqlite3.Connection,
    *,
    preview_id: str,
    approval: Mapping[str, Any],
    approval_source_type: str = "json_object",
    approval_source_hash: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    preview_id = rails.validate_required_text("preview_id", preview_id)
    approval_source_type = _validate_choice(
        "approval_source_type",
        approval_source_type,
        ("json_file", "json_object"),
    )
    normalized_approval = _normalize_approval_payload(approval, expected_preview_id=preview_id)
    source_hash = (
        rails.validate_required_text("approval_source_hash", approval_source_hash)
        if approval_source_hash is not None
        else stable_approval_source_hash(normalized_approval)
    )

    permissions = _evaluate_apply_permissions(connection)
    denied = next((permission for permission in permissions if not permission["allowed"]), None)
    if denied is not None:
        return _blocked_result(
            preview_id=preview_id,
            reason=denied["reason"],
            permissions=permissions,
            approval_source_hash=source_hash,
        )

    preview = get_synthesis_import_preview(connection, preview_id)
    if preview is None:
        raise SynthesisApplyValidationError(f"Synthesis import preview not found: {preview_id}")

    parsed_json = preview.get("parsed_json")
    if not isinstance(parsed_json, Mapping):
        raise SynthesisApplyValidationError("Stored synthesis import preview is malformed.")
    candidates = parsed_json.get("candidates")
    if not isinstance(candidates, Mapping):
        raise SynthesisApplyValidationError("Stored synthesis import preview has no candidates.")

    apply_run_id = f"synthesis-apply-run-{uuid4()}"
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    approved_refs = normalized_approval["approved_refs"]
    rejected_refs = normalized_approval["rejected_refs"]
    candidate_entries = _iter_preview_candidates(candidates)
    _reject_unknown_approval_refs(
        approved_refs,
        rejected_refs,
        {_candidate_key(section, index) for section, index, _candidate in candidate_entries},
    )
    items: list[dict[str, Any]] = []

    for section, index, candidate in candidate_entries:
        candidate_key = _candidate_key(section, index)
        candidate_hash = stable_candidate_hash(
            section=section,
            index=index,
            candidate=candidate,
        )
        approval_entry = approved_refs.get(candidate_key)
        rejected_entry = rejected_refs.get(candidate_key)
        if approval_entry is not None:
            _verify_optional_candidate_hash(approval_entry, candidate_hash)
        if rejected_entry is not None:
            _verify_optional_candidate_hash(rejected_entry, candidate_hash)
        item = _apply_candidate_item(
            connection,
            apply_run_id=apply_run_id,
            preview_id=preview_id,
            section=section,
            index=index,
            candidate=candidate,
            candidate_key=candidate_key,
            candidate_hash=candidate_hash,
            approval_entry=approval_entry,
            rejected_entry=rejected_entry,
            created_at=created,
        )
        items.append(item)

    counts = _item_counts(
        items,
        approved_candidate_count=len(approved_refs),
    )
    run_status = _run_status_from_counts(counts)
    completed = _utc_now()
    completion_report = _completion_report(
        apply_run_id=apply_run_id,
        preview_id=preview_id,
        approval_source_type=approval_source_type,
        approval_source_hash=source_hash,
        status=run_status,
        counts=counts,
        items=items,
    )

    with connection:
        connection.execute(
            """
            INSERT INTO synthesis_apply_runs (
                apply_run_id,
                preview_id,
                approval_source_type,
                approval_source_hash,
                status,
                approved_candidate_count,
                applied_candidate_count,
                blocked_candidate_count,
                skipped_candidate_count,
                failed_candidate_count,
                no_external_writes,
                no_send_mode,
                live_write,
                internal_state_mutation,
                created_at,
                completed_at,
                completion_report_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                apply_run_id,
                preview_id,
                approval_source_type,
                source_hash,
                run_status,
                counts["approved_candidate_count"],
                counts["applied_candidate_count"],
                counts["blocked_candidate_count"],
                counts["skipped_candidate_count"],
                counts["failed_candidate_count"],
                1,
                1,
                0,
                1,
                created,
                completed,
                _json_dumps(completion_report),
            ),
        )
        for item in items:
            _insert_apply_item(connection, item)
        update_synthesis_import_preview_status(
            connection,
            preview_id=preview_id,
            status=_preview_status_for_run(run_status),
            updated_at=completed,
        )

    run = get_synthesis_apply_run(connection, apply_run_id)
    return {
        "status": run_status,
        "reason": _reason_for_run_status(run_status),
        "apply_run_id": apply_run_id,
        "preview_id": preview_id,
        "approval_source_type": approval_source_type,
        "approval_source_hash": source_hash,
        "permissions": permissions,
        "database_write": True,
        "external_mutation": False,
        "simulated_or_dry_run": False,
        "run": run,
        "items": items,
        "completion_report": completion_report,
        **APPLY_SAFETY_FLAGS,
    }


def read_synthesis_apply_run(
    connection: sqlite3.Connection,
    *,
    apply_run_id: str,
) -> dict[str, Any] | None:
    require_synthesis_apply_permission(connection, category=SYNTHESIS_APPLY_READ_PERMISSION)
    return get_synthesis_apply_run(connection, apply_run_id)


def get_synthesis_apply_run(
    connection: sqlite3.Connection,
    apply_run_id: str,
) -> dict[str, Any] | None:
    apply_run_id = rails.validate_required_text("apply_run_id", apply_run_id)
    row = connection.execute(
        """
        SELECT
            apply_run_id,
            preview_id,
            approval_source_type,
            approval_source_hash,
            status,
            approved_candidate_count,
            applied_candidate_count,
            blocked_candidate_count,
            skipped_candidate_count,
            failed_candidate_count,
            no_external_writes,
            no_send_mode,
            live_write,
            internal_state_mutation,
            created_at,
            completed_at,
            completion_report_json
        FROM synthesis_apply_runs
        WHERE apply_run_id = ?
        """,
        (apply_run_id,),
    ).fetchone()
    return _run_row_to_dict(row) if row is not None else None


def list_synthesis_apply_runs(
    connection: sqlite3.Connection,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("limit must be a non-negative integer")
    sql = """
        SELECT
            apply_run_id,
            preview_id,
            approval_source_type,
            approval_source_hash,
            status,
            approved_candidate_count,
            applied_candidate_count,
            blocked_candidate_count,
            skipped_candidate_count,
            failed_candidate_count,
            no_external_writes,
            no_send_mode,
            live_write,
            internal_state_mutation,
            created_at,
            completed_at,
            completion_report_json
        FROM synthesis_apply_runs
        ORDER BY created_at DESC, apply_run_id
    """
    values: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        values = (limit,)
    rows = connection.execute(sql, values).fetchall()
    return [_run_row_to_dict(row) for row in rows]


def list_synthesis_apply_items(
    connection: sqlite3.Connection,
    *,
    apply_run_id: str | None = None,
) -> list[dict[str, Any]]:
    if apply_run_id is None:
        rows = connection.execute(
            """
            SELECT *
            FROM synthesis_apply_items
            ORDER BY created_at DESC, candidate_key
            """
        ).fetchall()
    else:
        apply_run_id = rails.validate_required_text("apply_run_id", apply_run_id)
        rows = connection.execute(
            """
            SELECT *
            FROM synthesis_apply_items
            WHERE apply_run_id = ?
            ORDER BY candidate_key
            """,
            (apply_run_id,),
        ).fetchall()
    return [_item_row_to_dict(row) for row in rows]


def count_synthesis_apply_runs(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "synthesis_apply_runs")


def count_synthesis_apply_items(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "synthesis_apply_items")


def summarize_synthesis_apply_runs(
    connection: sqlite3.Connection,
    *,
    recent_limit: int = 3,
) -> dict[str, Any]:
    require_synthesis_apply_permission(connection, category=SYNTHESIS_APPLY_READ_PERMISSION)
    runs = list_synthesis_apply_runs(connection, limit=recent_limit)
    latest = runs[0] if runs else None
    return {
        "available": True,
        "permission_required": SYNTHESIS_APPLY_READ_PERMISSION,
        "apply_run_count": count_synthesis_apply_runs(connection),
        "apply_item_count": count_synthesis_apply_items(connection),
        "counts_by_status": _grouped_counts(connection, "synthesis_apply_runs", "status"),
        "item_counts_by_apply_status": _grouped_counts(
            connection,
            "synthesis_apply_items",
            "apply_status",
        ),
        "latest_apply_run_id": latest["apply_run_id"] if latest is not None else None,
        "latest_preview_id": latest["preview_id"] if latest is not None else None,
        "latest_status": latest["status"] if latest is not None else None,
        "latest_applied_candidate_count": (
            latest["applied_candidate_count"] if latest is not None else 0
        ),
        "latest_blocked_candidate_count": (
            latest["blocked_candidate_count"] if latest is not None else 0
        ),
        "latest_skipped_candidate_count": (
            latest["skipped_candidate_count"] if latest is not None else 0
        ),
        "latest_failed_candidate_count": (
            latest["failed_candidate_count"] if latest is not None else 0
        ),
        "latest_no_external_writes": (
            latest["no_external_writes"] if latest is not None else True
        ),
        "latest_no_send_mode": latest["no_send_mode"] if latest is not None else True,
        "latest_live_write": latest["live_write"] if latest is not None else False,
        "recent_runs": runs,
        "no_external_writes": True,
        "no_send_mode": True,
        "live_write": False,
        "read_only": True,
    }


def require_synthesis_apply_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_synthesis_apply_permission(connection, category=category)
    if not decision["allowed"]:
        raise SynthesisApplyPermissionDenied(decision["reason"])
    return decision


def evaluate_synthesis_apply_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = rails.validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=None,
            reason=f"Missing synthesis apply permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid synthesis apply permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Synthesis apply permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Synthesis apply permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Synthesis apply permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def stable_approval_source_hash(approval: Mapping[str, Any] | bytes | str) -> str:
    if isinstance(approval, bytes):
        material = approval
    elif isinstance(approval, str):
        material = approval.encode("utf-8")
    else:
        material = _json_dumps(approval).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def stable_candidate_hash(
    *,
    section: str,
    index: int,
    candidate: Any,
) -> str:
    material = _json_dumps(
        {
            "section": section,
            "index": index,
            "candidate": candidate,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _apply_candidate_item(
    connection: sqlite3.Connection,
    *,
    apply_run_id: str,
    preview_id: str,
    section: str,
    index: int,
    candidate: Any,
    candidate_key: str,
    candidate_hash: str,
    approval_entry: Mapping[str, Any] | None,
    rejected_entry: Mapping[str, Any] | None,
    created_at: str,
) -> dict[str, Any]:
    base = {
        "apply_item_id": f"synthesis-apply-item-{uuid4()}",
        "apply_run_id": apply_run_id,
        "preview_id": preview_id,
        "candidate_type": section,
        "candidate_key": candidate_key,
        "candidate_index": index,
        "candidate_hash": candidate_hash,
        "approval_status": "skipped",
        "apply_status": "not_applied",
        "target_table": None,
        "target_id": None,
        "risk_level": None,
        "approval_mode": None,
        "high_stakes": False,
        "rollback_metadata": {},
        "validation_report": {
            "candidate_key": candidate_key,
            "candidate_hash": candidate_hash,
            "validated_at": created_at,
            "validation_reran": True,
        },
        "error_message": None,
        "created_at": created_at,
    }

    try:
        normalized = validate_synthesis_import_candidate_for_apply(
            section,
            candidate,
            index=index,
        )
    except SynthesisImportCandidateBlocked as error:
        return {
            **base,
            "approval_status": "blocked",
            "apply_status": "blocked",
            "high_stakes": True,
            "validation_report": {
                **base["validation_report"],
                "valid": False,
                "blocked": True,
                "reason": str(error),
            },
            "error_message": str(error),
        }
    except (SynthesisImportValidationError, ValueError, TypeError) as error:
        return {
            **base,
            "approval_status": "blocked" if approval_entry is not None else "skipped",
            "apply_status": "failed" if approval_entry is not None else "not_applied",
            "validation_report": {
                **base["validation_report"],
                "valid": False,
                "reason": str(error),
            },
            "error_message": str(error),
        }

    risk_level = normalized["risk_level"]
    approval_mode = normalized["approval_mode"]
    high_stakes = _is_high_stakes_apply_candidate(normalized)
    base = {
        **base,
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "high_stakes": high_stakes,
        "validation_report": {
            **base["validation_report"],
            "valid": True,
            "risk_level": risk_level,
            "approval_mode": approval_mode,
        },
    }

    if rejected_entry is not None:
        return {
            **base,
            "approval_status": "rejected",
            "apply_status": "not_applied",
            "error_message": _optional_reason(rejected_entry),
        }
    if section not in ALLOWED_APPLY_SECTIONS:
        return {
            **base,
            "approval_status": "unsupported",
            "apply_status": "not_applied",
            "error_message": f"Unsupported Phase 13A apply target: {section}",
        }
    if approval_entry is None:
        return {
            **base,
            "approval_status": "skipped",
            "apply_status": "not_applied",
            "target_table": SUPPORTED_TARGET_TABLES[section],
            "target_id": _target_id_for_candidate(
                section=section,
                preview_id=preview_id,
                candidate_key=candidate_key,
                candidate_hash=candidate_hash,
            ),
            "error_message": "Candidate was not explicitly approved.",
        }
    if approval_mode == "manual_only":
        return {
            **base,
            "approval_status": "review_required",
            "apply_status": "not_applied",
            "target_table": SUPPORTED_TARGET_TABLES[section],
            "target_id": _target_id_for_candidate(
                section=section,
                preview_id=preview_id,
                candidate_key=candidate_key,
                candidate_hash=candidate_hash,
            ),
            "error_message": "Manual-only candidates cannot be applied in Phase 13A.",
        }
    if high_stakes:
        return {
            **base,
            "approval_status": "blocked",
            "apply_status": "blocked",
            "target_table": SUPPORTED_TARGET_TABLES[section],
            "target_id": _target_id_for_candidate(
                section=section,
                preview_id=preview_id,
                candidate_key=candidate_key,
                candidate_hash=candidate_hash,
            ),
            "error_message": "High-stakes candidates are blocked from Phase 13A apply.",
        }

    try:
        return _apply_supported_candidate(
            connection,
            base=base,
            section=section,
            normalized=normalized,
            preview_id=preview_id,
            candidate_key=candidate_key,
            candidate_hash=candidate_hash,
            created_at=created_at,
        )
    except (sqlite3.Error, ValueError, TypeError) as error:
        return {
            **base,
            "approval_status": "approved",
            "apply_status": "failed",
            "target_table": SUPPORTED_TARGET_TABLES[section],
            "target_id": _target_id_for_candidate(
                section=section,
                preview_id=preview_id,
                candidate_key=candidate_key,
                candidate_hash=candidate_hash,
            ),
            "error_message": str(error),
        }


def _apply_supported_candidate(
    connection: sqlite3.Connection,
    *,
    base: Mapping[str, Any],
    section: str,
    normalized: Mapping[str, Any],
    preview_id: str,
    candidate_key: str,
    candidate_hash: str,
    created_at: str,
) -> dict[str, Any]:
    target_table = SUPPORTED_TARGET_TABLES[section]
    target_id = _target_id_for_candidate(
        section=section,
        preview_id=preview_id,
        candidate_key=candidate_key,
        candidate_hash=candidate_hash,
    )

    existing = _existing_target(connection, section=section, target_id=target_id)
    if existing is not None:
        return {
            **base,
            "approval_status": "approved",
            "apply_status": "skipped_duplicate",
            "target_table": target_table,
            "target_id": target_id,
            "rollback_metadata": {
                "operation": "none",
                "reason": "target already existed",
                "target_table": target_table,
                "target_id": target_id,
            },
        }

    metadata = _core_metadata(
        preview_id=preview_id,
        candidate_key=candidate_key,
        candidate_hash=candidate_hash,
        candidate=normalized,
    )
    notes = _notes_for_candidate(normalized)
    if section == "priorities":
        record = create_priority(
            connection,
            priority_id=target_id,
            title=normalized["title"],
            status=normalized["status"],
            metadata=metadata,
            notes=notes,
            created_at_utc=created_at,
            updated_at_utc=created_at,
        )
        id_column = "priority_id"
    elif section == "projects":
        record = create_project(
            connection,
            project_id=target_id,
            title=normalized["title"],
            status=normalized["status"],
            metadata=metadata,
            notes=notes,
            created_at_utc=created_at,
            updated_at_utc=created_at,
        )
        id_column = "project_id"
    elif section == "followups":
        record = create_followup(
            connection,
            followup_id=target_id,
            title=normalized["title"],
            status=normalized["status"],
            source="synthesis_import_apply",
            metadata=metadata,
            notes=notes,
            created_at_utc=created_at,
            updated_at_utc=created_at,
        )
        id_column = "followup_id"
    else:
        raise ValueError(f"Unsupported Phase 13A apply target: {section}")

    return {
        **base,
        "approval_status": "approved",
        "apply_status": "applied",
        "target_table": target_table,
        "target_id": target_id,
        "rollback_metadata": {
            "operation": "insert",
            "target_table": target_table,
            "target_id": target_id,
            "id_column": id_column,
            "created_record": record,
        },
    }


def _insert_apply_item(connection: sqlite3.Connection, item: Mapping[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO synthesis_apply_items (
            apply_item_id,
            apply_run_id,
            preview_id,
            candidate_type,
            candidate_key,
            candidate_index,
            candidate_hash,
            approval_status,
            apply_status,
            target_table,
            target_id,
            risk_level,
            approval_mode,
            high_stakes,
            rollback_metadata_json,
            validation_report_json,
            error_message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["apply_item_id"],
            item["apply_run_id"],
            item["preview_id"],
            item["candidate_type"],
            item["candidate_key"],
            item["candidate_index"],
            item["candidate_hash"],
            _validate_choice(
                "approval_status",
                item["approval_status"],
                SYNTHESIS_APPLY_APPROVAL_STATUSES,
            ),
            _validate_choice("apply_status", item["apply_status"], SYNTHESIS_APPLY_ITEM_STATUSES),
            item["target_table"],
            item["target_id"],
            item["risk_level"],
            item["approval_mode"],
            int(bool(item["high_stakes"])),
            _json_dumps(item["rollback_metadata"]),
            _json_dumps(item["validation_report"]),
            item["error_message"],
            item["created_at"],
        ),
    )


def _normalize_approval_payload(
    approval: Mapping[str, Any],
    *,
    expected_preview_id: str,
) -> dict[str, Any]:
    if not isinstance(approval, Mapping):
        raise SynthesisApplyValidationError("approval file JSON must decode to an object")
    approval_preview_id = rails.validate_required_text(
        "approval.preview_id",
        approval.get("preview_id"),
    )
    if approval_preview_id != expected_preview_id:
        raise SynthesisApplyValidationError(
            "approval file preview_id does not match requested preview_id"
        )

    approved_items = _approval_item_list(approval.get("approved_candidates", []))
    rejected_items = _approval_item_list(approval.get("rejected_candidates", []))
    approved_refs = _approval_refs(approved_items)
    rejected_refs = _approval_refs(rejected_items)
    overlap = set(approved_refs) & set(rejected_refs)
    if overlap:
        names = ", ".join(sorted(overlap))
        raise SynthesisApplyValidationError(
            f"candidate refs cannot be approved and rejected: {names}"
        )

    approval_note = approval.get("approval_note", "")
    if approval_note is not None and not isinstance(approval_note, str):
        raise SynthesisApplyValidationError("approval_note must be a string when provided")
    return {
        "preview_id": approval_preview_id,
        "approved_candidates": approved_items,
        "rejected_candidates": rejected_items,
        "approved_refs": approved_refs,
        "rejected_refs": rejected_refs,
        "approval_note": approval_note,
    }


def _approval_item_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SynthesisApplyValidationError(
            "approved_candidates and rejected_candidates must be lists"
        )
    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise SynthesisApplyValidationError(
                f"approval candidate at index {index} must be an object"
            )
        section = _normalize_candidate_type(item.get("candidate_type"))
        candidate_index = item.get("candidate_index")
        if type(candidate_index) is not int or candidate_index < 0:
            raise SynthesisApplyValidationError("candidate_index must be a non-negative integer")
        candidate_hash = item.get("candidate_hash")
        if candidate_hash is not None:
            candidate_hash = rails.validate_required_text("candidate_hash", candidate_hash)
        reason = item.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise SynthesisApplyValidationError("approval reason must be a string when provided")
        normalized.append(
            {
                "candidate_type": section,
                "candidate_index": candidate_index,
                "candidate_key": _candidate_key(section, candidate_index),
                "candidate_hash": candidate_hash,
                "reason": reason,
            }
        )
    return normalized


def _approval_refs(items: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    refs: dict[str, Mapping[str, Any]] = {}
    for item in items:
        candidate_key = str(item["candidate_key"])
        if candidate_key in refs:
            raise SynthesisApplyValidationError(
                f"duplicate approval candidate ref: {candidate_key}"
            )
        refs[candidate_key] = item
    return refs


def _normalize_candidate_type(value: Any) -> str:
    raw = rails.validate_required_text("candidate_type", value)
    normalized = raw.strip().lower().replace("-", "_")
    section = _CANDIDATE_TYPE_ALIASES.get(normalized)
    if section is None or section not in CANDIDATE_SECTIONS:
        raise SynthesisApplyValidationError(f"Unsupported approval candidate_type: {raw}")
    return section


def _iter_preview_candidates(candidates: Mapping[str, Any]) -> list[tuple[str, int, Any]]:
    flattened: list[tuple[str, int, Any]] = []
    for section in CANDIDATE_SECTIONS:
        items = candidates.get(section, [])
        if not isinstance(items, list):
            raise SynthesisApplyValidationError(f"Stored candidates.{section} must be a list")
        for index, candidate in enumerate(items):
            flattened.append((section, index, candidate))
    return flattened


def _reject_unknown_approval_refs(
    approved_refs: Mapping[str, Mapping[str, Any]],
    rejected_refs: Mapping[str, Mapping[str, Any]],
    known: set[str],
) -> None:
    unknown = (set(approved_refs) | set(rejected_refs)) - known
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SynthesisApplyValidationError(
            f"approval file references missing candidate(s): {names}"
        )


def _verify_optional_candidate_hash(
    approval_entry: Mapping[str, Any],
    candidate_hash: str,
) -> None:
    expected = approval_entry.get("candidate_hash")
    if expected is not None and expected != candidate_hash:
        raise SynthesisApplyValidationError(
            f"candidate_hash mismatch for {approval_entry['candidate_key']}"
        )


def _existing_target(
    connection: sqlite3.Connection,
    *,
    section: str,
    target_id: str,
) -> dict[str, Any] | None:
    if section == "priorities":
        return get_priority(connection, target_id)
    if section == "projects":
        return get_project(connection, target_id)
    if section == "followups":
        return get_followup(connection, target_id)
    raise ValueError(f"Unsupported Phase 13A apply target: {section}")


def _target_id_for_candidate(
    *,
    section: str,
    preview_id: str,
    candidate_key: str,
    candidate_hash: str,
) -> str:
    singular = {
        "priorities": "priority",
        "projects": "project",
        "followups": "followup",
    }[section]
    dedupe_key = ":".join(("synthesis_apply", preview_id, candidate_key, candidate_hash))
    return rails.stable_local_id(f"synthesis-apply-{singular}", dedupe_key)


def _core_metadata(
    *,
    preview_id: str,
    candidate_key: str,
    candidate_hash: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = {
        "created_by": "personalos.synthesis_apply",
        "preview_id": preview_id,
        "candidate_key": candidate_key,
        "candidate_hash": candidate_hash,
        "source_type": candidate.get("source_type", "chatgpt_synthesis"),
        "source_id": candidate.get("source_id", ""),
        "risk_level": candidate["risk_level"],
        "approval_mode": candidate["approval_mode"],
        "summary": candidate.get("summary", ""),
        "internal_state_only": True,
        "no_external_writes": True,
    }
    for optional_key in (
        "domain",
        "review_cadence",
        "review_note",
        "due_date_or_review_note",
    ):
        if optional_key in candidate:
            metadata[optional_key] = candidate[optional_key]
    return metadata


def _notes_for_candidate(candidate: Mapping[str, Any]) -> str:
    notes = [str(candidate.get("summary", "")).strip()]
    for optional_key in ("review_note", "due_date_or_review_note"):
        optional = str(candidate.get(optional_key, "")).strip()
        if optional:
            notes.append(optional)
    return "\n\n".join(item for item in notes if item)


def _is_high_stakes_apply_candidate(candidate: Mapping[str, Any]) -> bool:
    if candidate.get("risk_level") == "high":
        return True
    return any(term in _candidate_text(candidate) for term in _HIGH_STAKES_APPLY_TERMS)


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    return _json_dumps(candidate).lower()


def _item_counts(
    items: Sequence[Mapping[str, Any]],
    *,
    approved_candidate_count: int,
) -> dict[str, int]:
    applied = sum(1 for item in items if item["apply_status"] == "applied")
    blocked = sum(1 for item in items if item["apply_status"] == "blocked")
    failed = sum(1 for item in items if item["apply_status"] == "failed")
    skipped = sum(
        1
        for item in items
        if item["apply_status"] in {"not_applied", "skipped_duplicate"}
    )
    return {
        "approved_candidate_count": approved_candidate_count,
        "applied_candidate_count": applied,
        "blocked_candidate_count": blocked,
        "skipped_candidate_count": skipped,
        "failed_candidate_count": failed,
    }


def _run_status_from_counts(counts: Mapping[str, int]) -> str:
    if counts["applied_candidate_count"] > 0:
        if (
            counts["blocked_candidate_count"] > 0
            or counts["failed_candidate_count"] > 0
            or counts["skipped_candidate_count"] > 0
        ):
            return "partially_completed"
        return "completed"
    if counts["failed_candidate_count"] > 0:
        return "failed"
    if counts["blocked_candidate_count"] > 0:
        return "blocked"
    return "no_op"


def _preview_status_for_run(run_status: str) -> str:
    if run_status == "completed":
        return "apply_completed"
    if run_status in {"partially_completed", "no_op"}:
        return "apply_partially_completed"
    if run_status == "blocked":
        return "apply_blocked"
    return "apply_failed"


def _completion_report(
    *,
    apply_run_id: str,
    preview_id: str,
    approval_source_type: str,
    approval_source_hash: str,
    status: str,
    counts: Mapping[str, int],
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "apply_run_id": apply_run_id,
        "preview_id": preview_id,
        "approval_source_type": approval_source_type,
        "approval_source_hash": approval_source_hash,
        "status": status,
        "counts": dict(counts),
        "item_status_counts": _count_by_key(items, "apply_status"),
        "approval_status_counts": _count_by_key(items, "approval_status"),
        "supported_apply_targets": list(ALLOWED_APPLY_SECTIONS),
        "unsupported_targets": sorted(
            {
                item["candidate_type"]
                for item in items
                if item["approval_status"] == "unsupported"
            }
        ),
        **APPLY_SAFETY_FLAGS,
    }


def _blocked_result(
    *,
    preview_id: str,
    reason: str,
    permissions: Sequence[Mapping[str, Any]],
    approval_source_hash: str,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "apply_run_id": None,
        "preview_id": preview_id,
        "approval_source_hash": approval_source_hash,
        "permissions": list(permissions),
        "database_write": False,
        "external_mutation": False,
        "items": [],
        "completion_report": None,
        **APPLY_SAFETY_FLAGS,
    }


def _evaluate_apply_permissions(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        evaluate_synthesis_apply_permission(
            connection,
            category=SYNTHESIS_APPLY_READ_PERMISSION,
        ),
        evaluate_synthesis_apply_permission(
            connection,
            category=SYNTHESIS_APPLY_WRITE_PERMISSION,
        ),
        evaluate_synthesis_apply_permission(
            connection,
            category=SYNTHESIS_APPLY_APPLY_PERMISSION,
        ),
    ]


def _permission_decision(
    *,
    allowed: bool,
    category: str,
    mode: str | None,
    reason: str,
    setting: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "category": category,
        "mode": mode,
        "reason": reason,
        "setting": dict(setting) if setting is not None else None,
    }


def _run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "apply_run_id": row["apply_run_id"],
        "preview_id": row["preview_id"],
        "approval_source_type": row["approval_source_type"],
        "approval_source_hash": row["approval_source_hash"],
        "status": row["status"],
        "approved_candidate_count": int(row["approved_candidate_count"]),
        "applied_candidate_count": int(row["applied_candidate_count"]),
        "blocked_candidate_count": int(row["blocked_candidate_count"]),
        "skipped_candidate_count": int(row["skipped_candidate_count"]),
        "failed_candidate_count": int(row["failed_candidate_count"]),
        "no_external_writes": bool(row["no_external_writes"]),
        "no_send_mode": bool(row["no_send_mode"]),
        "live_write": bool(row["live_write"]),
        "internal_state_mutation": bool(row["internal_state_mutation"]),
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
        "completion_report_json": _json_loads_object(row["completion_report_json"]),
    }


def _item_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "apply_item_id": row["apply_item_id"],
        "apply_run_id": row["apply_run_id"],
        "preview_id": row["preview_id"],
        "candidate_type": row["candidate_type"],
        "candidate_key": row["candidate_key"],
        "candidate_index": int(row["candidate_index"]),
        "candidate_hash": row["candidate_hash"],
        "approval_status": row["approval_status"],
        "apply_status": row["apply_status"],
        "target_table": row["target_table"],
        "target_id": row["target_id"],
        "risk_level": row["risk_level"],
        "approval_mode": row["approval_mode"],
        "high_stakes": bool(row["high_stakes"]),
        "rollback_metadata": _json_loads_object(row["rollback_metadata_json"]),
        "validation_report": _json_loads_object(row["validation_report_json"]),
        "error_message": row["error_message"],
        "created_at": row["created_at"],
    }


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    if table_name not in {"synthesis_apply_runs", "synthesis_apply_items"}:
        raise ValueError(f"Unsupported synthesis apply table: {table_name}")
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _grouped_counts(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> dict[str, int]:
    if table_name not in {"synthesis_apply_runs", "synthesis_apply_items"}:
        raise ValueError(f"Unsupported synthesis apply summary table: {table_name}")
    if column_name not in {"status", "apply_status"}:
        raise ValueError(f"Unsupported synthesis apply summary column: {column_name}")
    rows = connection.execute(
        f"""
        SELECT {column_name} AS value, COUNT(*) AS value_count
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY {column_name}
        """
    ).fetchall()
    return {row["value"]: int(row["value_count"]) for row in rows}


def _count_by_key(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_key(section: str, index: int) -> str:
    return f"{section}[{index}]"


def _optional_reason(item: Mapping[str, Any]) -> str | None:
    reason = item.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason
    return None


def _reason_for_run_status(status: str) -> str:
    return {
        "completed": "Approved synthesis candidates were applied to internal SQLite state only.",
        "partially_completed": (
            "Some approved synthesis candidates were applied; skipped, unsupported, or "
            "blocked candidates were recorded."
        ),
        "blocked": "No candidates were applied because the approved candidate set was blocked.",
        "failed": (
            "No candidates were applied because the approved candidate set failed validation."
        ),
        "no_op": "No candidates were applied; item-level outcomes were recorded.",
    }[status]


def _validate_choice(field_name: str, value: Any, allowed: Sequence[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        names = ", ".join(allowed)
        raise SynthesisApplyValidationError(f"{field_name} must be one of: {names}")
    return value


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = rails.validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SynthesisApplyValidationError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SynthesisApplyValidationError(f"{field_name} must include a timezone offset")
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_loads_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("stored JSON must decode to an object")
    return parsed


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

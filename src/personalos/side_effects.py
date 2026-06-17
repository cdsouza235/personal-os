"""Side-effect intent and idempotency ledgers for dry-run write rails."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from personalos import execution_rails as rails
from personalos.idempotency import (
    generate_idempotency_key,
    payload_fingerprint,
    stable_json_dumps,
    stable_side_effect_id,
)
from personalos.permissions import PermissionMode
from personalos.state import get_permission_setting

SIDE_EFFECT_LEDGER_READ_PERMISSION = "side_effect_ledger_dev_test_read"
SIDE_EFFECT_LEDGER_WRITE_PERMISSION = "side_effect_ledger_dev_test_write"
SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION = "side_effect_ledger_dev_test_record_attempt"

TARGET_SYSTEMS = ("todoist", "calendar", "gmail", "personalos_markdown", "other")
OPERATION_TYPES = ("create", "update", "delete", "send", "export", "write_file")
INTENT_STATUSES = (
    "pending_review",
    "approved_for_dry_run",
    "dry_run_recorded",
    "blocked",
    "skipped_duplicate",
    "failed",
    "completed_simulated",
)
ATTEMPT_MODES = ("dry_run", "simulated", "live_blocked")
ATTEMPT_STATUSES = ("succeeded", "failed", "blocked", "skipped_duplicate")

REPORT_SAFETY_FLAGS = {
    "no_external_writes": True,
    "no_send_mode": True,
    "live_write": False,
    "simulated_or_dry_run": True,
    "no_live_model_call": True,
    "no_todoist_writes": True,
    "no_calendar_writes": True,
    "no_gmail_send": True,
    "no_gmail_draft": True,
    "no_personalos_writes": True,
}


class SideEffectLedgerPermissionDenied(PermissionError):
    """Raised when side-effect ledger permissions do not allow an action."""


class SideEffectLedgerValidationError(ValueError):
    """Raised when a side-effect intent or attempt is not Phase 12B safe."""


def build_external_write_intent(
    *,
    source_type: str,
    source_id: str,
    target_system: str,
    operation_type: str,
    payload: Mapping[str, Any],
    risk_level: str = "low",
    approval_mode: str | None = None,
    dedupe_key: str | None = None,
    intent_id: str | None = None,
    status: str | None = None,
    validation_report: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    source_type = rails.validate_required_text("source_type", source_type)
    source_id = rails.validate_required_text("source_id", source_id)
    target_system = validate_target_system(target_system)
    operation_type = validate_operation_type(operation_type)
    payload_object = _validate_mapping("payload", payload)
    payload_hash = payload_fingerprint(payload_object)
    risk_level = rails.validate_risk_level(risk_level)
    approval_mode = rails.validate_approval_mode(approval_mode, risk_level=risk_level)
    status = validate_intent_status(status or _default_intent_status(approval_mode))
    dedupe_key = (
        rails.normalize_dedupe_key(dedupe_key)
        if dedupe_key is not None
        else _generated_dedupe_key(
            target_system=target_system,
            operation_type=operation_type,
            source_type=source_type,
            source_id=source_id,
            payload_hash=payload_hash,
        )
    )
    idempotency_key = generate_idempotency_key(
        target_system=target_system,
        operation_type=operation_type,
        source_type=source_type,
        source_id=source_id,
        dedupe_key=dedupe_key,
        payload=payload_object,
    )
    intent_id = (
        rails.validate_required_text("intent_id", intent_id)
        if intent_id is not None
        else stable_side_effect_id("external-intent", idempotency_key)
    )
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)
    validation = _validation_report(
        validation_report,
        approval=rails.build_approval_result(risk_level, approval_mode),
        payload_hash=payload_hash,
    )
    return {
        "intent_id": intent_id,
        "source_type": source_type,
        "source_id": source_id,
        "target_system": target_system,
        "operation_type": operation_type,
        "risk_level": risk_level,
        "approval_mode": approval_mode,
        "status": status,
        "idempotency_key": idempotency_key,
        "dedupe_key": dedupe_key,
        "payload": payload_object,
        "payload_fingerprint": payload_hash,
        "validation_report": validation,
        "no_external_writes": True,
        "no_send_mode": True,
        "live_write": False,
        "created_at": created,
        "updated_at": updated,
    }


def create_external_write_intent_record(
    connection: sqlite3.Connection,
    **intent_input: Any,
) -> dict[str, Any]:
    intent = build_external_write_intent(**intent_input)
    permission = evaluate_side_effect_ledger_permission(
        connection,
        category=SIDE_EFFECT_LEDGER_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            would_write=intent,
        )

    existing = get_external_write_intent_by_idempotency_key(
        connection,
        intent["idempotency_key"],
    )
    if existing is None:
        existing = get_external_write_intent_by_dedupe_key(
            connection,
            target_system=intent["target_system"],
            operation_type=intent["operation_type"],
            dedupe_key=intent["dedupe_key"],
        )
    if existing is not None:
        idempotency_record = _mark_duplicate_seen(
            connection,
            idempotency_key=existing["idempotency_key"],
            seen_at=intent["updated_at"],
        )
        completion_report = build_side_effect_completion_report(
            status="skipped_duplicate",
            intents_considered=1,
            intents_skipped_duplicate=1,
            idempotency_key=intent["idempotency_key"],
        )
        return {
            "status": "skipped_duplicate",
            "reason": "External write intent idempotency_key already exists; no duplicate intent row was created.",
            "dry_run": True,
            "database_write": idempotency_record is not None,
            "external_mutation": False,
            "duplicate": True,
            "permission": permission,
            "completion_report": completion_report,
            "would_write": intent,
            "intent": existing,
            "idempotency_record": idempotency_record,
            **REPORT_SAFETY_FLAGS,
        }

    payload_json = stable_json_dumps(intent["payload"])
    validation_json = stable_json_dumps(intent["validation_report"])
    with connection:
        connection.execute(
            """
            INSERT INTO external_write_intents (
                intent_id,
                source_type,
                source_id,
                target_system,
                operation_type,
                risk_level,
                approval_mode,
                status,
                idempotency_key,
                dedupe_key,
                payload_json,
                validation_report_json,
                no_external_writes,
                no_send_mode,
                live_write,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent["intent_id"],
                intent["source_type"],
                intent["source_id"],
                intent["target_system"],
                intent["operation_type"],
                intent["risk_level"],
                intent["approval_mode"],
                intent["status"],
                intent["idempotency_key"],
                intent["dedupe_key"],
                payload_json,
                validation_json,
                1,
                1,
                0,
                intent["created_at"],
                intent["updated_at"],
            ),
        )
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent["idempotency_key"],
                intent["target_system"],
                intent["operation_type"],
                intent["source_type"],
                intent["source_id"],
                intent["dedupe_key"],
                intent["payload_fingerprint"],
                intent["created_at"],
                intent["updated_at"],
                intent["status"],
                intent["intent_id"],
                None,
            ),
        )

    persisted = get_external_write_intent(connection, intent["intent_id"])
    if persisted is None:
        raise RuntimeError(f"External write intent was not persisted: {intent['intent_id']}")
    completion_report = build_side_effect_completion_report(
        status="created",
        intents_considered=1,
        intents_created=1,
        idempotency_key=intent["idempotency_key"],
    )
    return {
        "status": "created",
        "reason": "External write intent was recorded in the dev/test SQLite ledger only.",
        "dry_run": True,
        "database_write": True,
        "external_mutation": False,
        "duplicate": False,
        "permission": permission,
        "completion_report": completion_report,
        "would_write": intent,
        "intent": persisted,
        "idempotency_record": get_idempotency_record(connection, intent["idempotency_key"]),
        **REPORT_SAFETY_FLAGS,
    }


def record_simulated_external_write_attempt(
    connection: sqlite3.Connection,
    *,
    intent_id: str,
    mode: str = "dry_run",
    adapter_name: str,
    status: str = "succeeded",
    response_summary: Mapping[str, Any] | None = None,
    error_message: str | None = None,
    live_write: bool = False,
    no_external_writes: bool = True,
    no_send_mode: bool = True,
    created_at: str | None = None,
) -> dict[str, Any]:
    _validate_safety_booleans(
        live_write=live_write,
        no_external_writes=no_external_writes,
        no_send_mode=no_send_mode,
    )
    intent_id = rails.validate_required_text("intent_id", intent_id)
    mode = validate_attempt_mode(mode)
    adapter_name = rails.validate_required_text("adapter_name", adapter_name)
    status = validate_attempt_status(status)
    validate_attempt_mode_status(mode=mode, status=status)
    response = _validate_mapping("response_summary", response_summary or {})
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    if error_message is not None:
        error_message = rails.validate_required_text("error_message", error_message)

    permission = evaluate_side_effect_ledger_permission(
        connection,
        category=SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(
            reason=permission["reason"],
            permission=permission,
            would_write={
                "intent_id": intent_id,
                "mode": mode,
                "adapter_name": adapter_name,
                "status": status,
                "response_summary": response,
                "error_message": error_message,
            },
        )

    intent = get_external_write_intent(connection, intent_id)
    if intent is None:
        raise ValueError(f"External write intent does not exist: {intent_id}")

    attempt_number = _next_attempt_number(connection, intent_id)
    request_fingerprint = _request_fingerprint(
        intent=intent,
        mode=mode,
        adapter_name=adapter_name,
    )
    attempt_id = stable_side_effect_id(
        "external-attempt",
        f"{intent_id}|{attempt_number}|{request_fingerprint}",
    )
    next_intent_status = _intent_status_after_attempt(mode=mode, attempt_status=status)
    completion_report = build_side_effect_completion_report(
        status=status,
        intents_considered=1,
        attempts_recorded=1,
        idempotency_key=intent["idempotency_key"],
    )

    with connection:
        connection.execute(
            """
            INSERT INTO external_write_attempts (
                attempt_id,
                intent_id,
                attempt_number,
                mode,
                adapter_name,
                status,
                request_fingerprint,
                response_summary_json,
                error_message,
                no_external_writes,
                no_send_mode,
                live_write,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                intent_id,
                attempt_number,
                mode,
                adapter_name,
                status,
                request_fingerprint,
                stable_json_dumps({**response, **REPORT_SAFETY_FLAGS}),
                error_message,
                1,
                1,
                0,
                created,
            ),
        )
        connection.execute(
            """
            UPDATE external_write_intents
            SET status = ?,
                updated_at = ?
            WHERE intent_id = ?
            """,
            (next_intent_status, created, intent_id),
        )
        connection.execute(
            """
            UPDATE idempotency_records
            SET status = ?,
                last_seen_at = ?,
                linked_attempt_id = ?
            WHERE idempotency_key = ?
            """,
            (next_intent_status, created, attempt_id, intent["idempotency_key"]),
        )

    attempt = get_external_write_attempt(connection, attempt_id)
    if attempt is None:
        raise RuntimeError(f"External write attempt was not persisted: {attempt_id}")
    return {
        "status": "recorded",
        "reason": "External write attempt was recorded as dry-run/simulated ledger state only.",
        "dry_run": mode == "dry_run",
        "database_write": True,
        "external_mutation": False,
        "permission": permission,
        "intent_before": intent,
        "intent_after": get_external_write_intent(connection, intent_id),
        "attempt": attempt,
        "completion_report": completion_report,
        **REPORT_SAFETY_FLAGS,
    }


def create_external_write_intent_and_record_dry_run(
    connection: sqlite3.Connection,
    *,
    intent: Mapping[str, Any],
    attempt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    attempt_permission = evaluate_side_effect_ledger_permission(
        connection,
        category=SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    )
    if not attempt_permission["allowed"]:
        return _blocked_result(
            reason=attempt_permission["reason"],
            permission=attempt_permission,
            would_write={"intent": intent, "attempt": attempt or {}},
        )

    intent_result = create_external_write_intent_record(connection, **dict(intent))
    if intent_result["status"] not in {"created", "skipped_duplicate"}:
        return intent_result
    if intent_result["status"] == "skipped_duplicate":
        return intent_result

    attempt_input = dict(attempt or {})
    attempt_result = record_simulated_external_write_attempt(
        connection,
        intent_id=intent_result["intent"]["intent_id"],
        mode=str(attempt_input.get("mode", "dry_run")),
        adapter_name=str(attempt_input.get("adapter_name", "phase_12b_fake_adapter")),
        status=str(attempt_input.get("status", "succeeded")),
        response_summary=_validate_mapping(
            "response_summary",
            attempt_input.get(
                "response_summary",
                {"phase": "12b", "external_mutation": False},
            ),
        ),
        error_message=attempt_input.get("error_message"),
        live_write=bool(attempt_input.get("live_write", False)),
        no_external_writes=bool(attempt_input.get("no_external_writes", True)),
        no_send_mode=bool(attempt_input.get("no_send_mode", True)),
        created_at=attempt_input.get("created_at"),
    )
    return {
        "status": attempt_result["status"],
        "reason": attempt_result["reason"],
        "intent_result": intent_result,
        "attempt_result": attempt_result,
        "completion_report": attempt_result["completion_report"],
        "database_write": True,
        "external_mutation": False,
        **REPORT_SAFETY_FLAGS,
    }


def get_external_write_intent(
    connection: sqlite3.Connection,
    intent_id: str,
) -> dict[str, Any] | None:
    intent_id = rails.validate_required_text("intent_id", intent_id)
    row = connection.execute(
        """
        SELECT
            intent_id,
            source_type,
            source_id,
            target_system,
            operation_type,
            risk_level,
            approval_mode,
            status,
            idempotency_key,
            dedupe_key,
            payload_json,
            validation_report_json,
            no_external_writes,
            no_send_mode,
            live_write,
            created_at,
            updated_at
        FROM external_write_intents
        WHERE intent_id = ?
        """,
        (intent_id,),
    ).fetchone()
    return _intent_row_to_dict(row) if row is not None else None


def get_external_write_intent_by_idempotency_key(
    connection: sqlite3.Connection,
    idempotency_key: str,
) -> dict[str, Any] | None:
    idempotency_key = rails.validate_required_text("idempotency_key", idempotency_key)
    row = connection.execute(
        """
        SELECT
            intent_id,
            source_type,
            source_id,
            target_system,
            operation_type,
            risk_level,
            approval_mode,
            status,
            idempotency_key,
            dedupe_key,
            payload_json,
            validation_report_json,
            no_external_writes,
            no_send_mode,
            live_write,
            created_at,
            updated_at
        FROM external_write_intents
        WHERE idempotency_key = ?
        """,
        (idempotency_key,),
    ).fetchone()
    return _intent_row_to_dict(row) if row is not None else None


def get_external_write_intent_by_dedupe_key(
    connection: sqlite3.Connection,
    *,
    target_system: str,
    operation_type: str,
    dedupe_key: str,
) -> dict[str, Any] | None:
    target_system = validate_target_system(target_system)
    operation_type = validate_operation_type(operation_type)
    dedupe_key = rails.normalize_dedupe_key(dedupe_key)
    row = connection.execute(
        """
        SELECT
            intent_id,
            source_type,
            source_id,
            target_system,
            operation_type,
            risk_level,
            approval_mode,
            status,
            idempotency_key,
            dedupe_key,
            payload_json,
            validation_report_json,
            no_external_writes,
            no_send_mode,
            live_write,
            created_at,
            updated_at
        FROM external_write_intents
        WHERE target_system = ?
          AND operation_type = ?
          AND dedupe_key = ?
        """,
        (target_system, operation_type, dedupe_key),
    ).fetchone()
    return _intent_row_to_dict(row) if row is not None else None


def list_external_write_intents(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    target_system: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[str] = []
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_intent_status(status))
    if target_system is not None:
        clauses.append("target_system = ?")
        values.append(validate_target_system(target_system))
    where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = connection.execute(
        f"""
        SELECT
            intent_id,
            source_type,
            source_id,
            target_system,
            operation_type,
            risk_level,
            approval_mode,
            status,
            idempotency_key,
            dedupe_key,
            payload_json,
            validation_report_json,
            no_external_writes,
            no_send_mode,
            live_write,
            created_at,
            updated_at
        FROM external_write_intents
        {where_clause}
        ORDER BY created_at DESC, intent_id
        """,
        values,
    ).fetchall()
    return [_intent_row_to_dict(row) for row in rows]


def get_external_write_attempt(
    connection: sqlite3.Connection,
    attempt_id: str,
) -> dict[str, Any] | None:
    attempt_id = rails.validate_required_text("attempt_id", attempt_id)
    row = connection.execute(
        """
        SELECT
            attempt_id,
            intent_id,
            attempt_number,
            mode,
            adapter_name,
            status,
            request_fingerprint,
            response_summary_json,
            error_message,
            no_external_writes,
            no_send_mode,
            live_write,
            created_at
        FROM external_write_attempts
        WHERE attempt_id = ?
        """,
        (attempt_id,),
    ).fetchone()
    return _attempt_row_to_dict(row) if row is not None else None


def get_idempotency_record(
    connection: sqlite3.Connection,
    idempotency_key: str,
) -> dict[str, Any] | None:
    idempotency_key = rails.validate_required_text("idempotency_key", idempotency_key)
    row = connection.execute(
        """
        SELECT
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
        FROM idempotency_records
        WHERE idempotency_key = ?
        """,
        (idempotency_key,),
    ).fetchone()
    return _idempotency_row_to_dict(row) if row is not None else None


def count_external_write_intents(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "external_write_intents")


def count_external_write_attempts(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "external_write_attempts")


def count_idempotency_records(connection: sqlite3.Connection) -> int:
    return _count_rows(connection, "idempotency_records")


def summarize_side_effect_ledgers(connection: sqlite3.Connection) -> dict[str, Any]:
    require_side_effect_ledger_permission(
        connection,
        category=SIDE_EFFECT_LEDGER_READ_PERMISSION,
    )
    return summarize_side_effect_ledgers_unchecked(connection)


def summarize_side_effect_ledgers_unchecked(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "intent_count": count_external_write_intents(connection),
        "attempt_count": count_external_write_attempts(connection),
        "idempotency_record_count": count_idempotency_records(connection),
        "intent_counts_by_status": _grouped_counts(
            connection,
            table_name="external_write_intents",
            column_name="status",
        ),
        "intent_counts_by_target_system": _grouped_counts(
            connection,
            table_name="external_write_intents",
            column_name="target_system",
        ),
        "attempt_counts_by_status": _grouped_counts(
            connection,
            table_name="external_write_attempts",
            column_name="status",
        ),
        "attempt_counts_by_mode": _grouped_counts(
            connection,
            table_name="external_write_attempts",
            column_name="mode",
        ),
        "safety_flags": dict(REPORT_SAFETY_FLAGS),
        **REPORT_SAFETY_FLAGS,
    }


def build_side_effect_completion_report(
    *,
    status: str,
    intents_considered: int = 0,
    intents_created: int = 0,
    intents_skipped_duplicate: int = 0,
    attempts_recorded: int = 0,
    idempotency_key: str | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "generated_at_utc": _utc_now(),
        "intents_considered": intents_considered,
        "intents_created": intents_created,
        "intents_skipped_duplicate": intents_skipped_duplicate,
        "attempts_recorded": attempts_recorded,
        "idempotency_key": idempotency_key,
        "warnings": warnings or [],
        "errors": errors or [],
        **REPORT_SAFETY_FLAGS,
    }


def require_side_effect_ledger_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_side_effect_ledger_permission(connection, category=category)
    if not decision["allowed"]:
        raise SideEffectLedgerPermissionDenied(decision["reason"])
    return decision


def evaluate_side_effect_ledger_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    category = rails.validate_required_text("category", category)
    setting = get_permission_setting(connection, category)
    if setting is None:
        return _permission_decision(
            category=category,
            allowed=False,
            reason=f"Missing side-effect ledger permission setting: {category}",
        )
    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            category=category,
            allowed=False,
            reason=f"Invalid side-effect ledger permission mode: {setting['mode']}",
        )
    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            category=category,
            allowed=False,
            reason=f"Side-effect ledger permission is disabled: {category}",
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            category=category,
            allowed=False,
            reason=f"Side-effect ledger permission is not enabled for dev/test use: {category}",
        )
    return _permission_decision(
        category=category,
        allowed=True,
        reason="Side-effect ledger permission is explicitly enabled for dev/test use.",
    )


def validate_target_system(target_system: str) -> str:
    target_system = rails.validate_required_text("target_system", target_system)
    if target_system not in TARGET_SYSTEMS:
        allowed = ", ".join(TARGET_SYSTEMS)
        raise ValueError(f"target_system must be one of: {allowed}")
    return target_system


def validate_operation_type(operation_type: str) -> str:
    operation_type = rails.validate_required_text("operation_type", operation_type)
    if operation_type not in OPERATION_TYPES:
        allowed = ", ".join(OPERATION_TYPES)
        raise ValueError(f"operation_type must be one of: {allowed}")
    return operation_type


def validate_intent_status(status: str) -> str:
    status = rails.validate_required_text("status", status)
    if status not in INTENT_STATUSES:
        allowed = ", ".join(INTENT_STATUSES)
        raise ValueError(f"intent status must be one of: {allowed}")
    return status


def validate_attempt_mode(mode: str) -> str:
    mode = rails.validate_required_text("mode", mode)
    if mode not in ATTEMPT_MODES:
        allowed = ", ".join(ATTEMPT_MODES)
        raise ValueError(f"attempt mode must be one of: {allowed}")
    return mode


def validate_attempt_status(status: str) -> str:
    status = rails.validate_required_text("status", status)
    if status not in ATTEMPT_STATUSES:
        allowed = ", ".join(ATTEMPT_STATUSES)
        raise ValueError(f"attempt status must be one of: {allowed}")
    return status


def validate_attempt_mode_status(*, mode: str, status: str) -> None:
    if mode == "live_blocked" and status != "blocked":
        raise ValueError("live_blocked attempts must use blocked status")


def _default_intent_status(approval_mode: str) -> str:
    if approval_mode == rails.ApprovalMode.AUTO_ALLOWED.value:
        return "approved_for_dry_run"
    return "pending_review"


def _generated_dedupe_key(
    *,
    target_system: str,
    operation_type: str,
    source_type: str,
    source_id: str,
    payload_hash: str,
) -> str:
    material = "|".join(
        (
            target_system,
            operation_type,
            rails.normalize_for_dedupe(source_type),
            rails.normalize_for_dedupe(source_id),
            payload_hash,
        )
    )
    return f"{target_system}:{operation_type}:{stable_side_effect_id('dedupe', material)}"


def _validation_report(
    validation_report: Mapping[str, Any] | None,
    *,
    approval: Mapping[str, Any],
    payload_hash: str,
) -> dict[str, Any]:
    provided = _validate_mapping("validation_report", validation_report or {})
    return {
        **provided,
        "approval": dict(approval),
        "payload_fingerprint": payload_hash,
        "phase": "12b",
        **REPORT_SAFETY_FLAGS,
    }


def _intent_status_after_attempt(*, mode: str, attempt_status: str) -> str:
    if attempt_status == "skipped_duplicate":
        return "skipped_duplicate"
    if attempt_status == "failed":
        return "failed"
    if attempt_status == "blocked":
        return "blocked"
    if mode == "simulated":
        return "completed_simulated"
    return "dry_run_recorded"


def _request_fingerprint(
    *,
    intent: Mapping[str, Any],
    mode: str,
    adapter_name: str,
) -> str:
    return payload_fingerprint(
        {
            "intent_id": intent["intent_id"],
            "idempotency_key": intent["idempotency_key"],
            "target_system": intent["target_system"],
            "operation_type": intent["operation_type"],
            "mode": mode,
            "adapter_name": adapter_name,
            "payload": intent["payload"],
        }
    )


def _next_attempt_number(connection: sqlite3.Connection, intent_id: str) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt_number
        FROM external_write_attempts
        WHERE intent_id = ?
        """,
        (intent_id,),
    ).fetchone()
    return int(row["next_attempt_number"])


def _mark_duplicate_seen(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    seen_at: str,
) -> dict[str, Any] | None:
    with connection:
        connection.execute(
            """
            UPDATE idempotency_records
            SET status = ?,
                last_seen_at = ?
            WHERE idempotency_key = ?
            """,
            ("skipped_duplicate", seen_at, idempotency_key),
        )
    return get_idempotency_record(connection, idempotency_key)


def _blocked_result(
    *,
    reason: str,
    permission: Mapping[str, Any],
    would_write: Mapping[str, Any] | None,
) -> dict[str, Any]:
    completion_report = build_side_effect_completion_report(
        status="blocked",
        intents_considered=1 if would_write is not None else 0,
        errors=[reason],
    )
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": True,
        "database_write": False,
        "external_mutation": False,
        "permission": dict(permission),
        "completion_report": completion_report,
        "would_write": dict(would_write) if would_write is not None else None,
        "intent": None,
        **REPORT_SAFETY_FLAGS,
    }


def _validate_safety_booleans(
    *,
    live_write: bool,
    no_external_writes: bool,
    no_send_mode: bool,
) -> None:
    if type(live_write) is not bool:
        raise ValueError("live_write must be a boolean")
    if type(no_external_writes) is not bool:
        raise ValueError("no_external_writes must be a boolean")
    if type(no_send_mode) is not bool:
        raise ValueError("no_send_mode must be a boolean")
    if live_write:
        raise SideEffectLedgerValidationError("Phase 12B cannot record live_write=true")
    if not no_external_writes:
        raise SideEffectLedgerValidationError("Phase 12B requires no_external_writes=true")
    if not no_send_mode:
        raise SideEffectLedgerValidationError("Phase 12B requires no_send_mode=true")


def _validate_mapping(field_name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON-safe object")
    copied = dict(value)
    stable_json_dumps(copied)
    return copied


def _validate_iso_datetime(field_name: str, value: str) -> str:
    value = rails.validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


def _intent_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "intent_id": row["intent_id"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "target_system": row["target_system"],
        "operation_type": row["operation_type"],
        "risk_level": row["risk_level"],
        "approval_mode": row["approval_mode"],
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "dedupe_key": row["dedupe_key"],
        "payload": _deserialize_mapping(row["payload_json"]),
        "validation_report": _deserialize_mapping(row["validation_report_json"]),
        "payload_fingerprint": payload_fingerprint(_deserialize_mapping(row["payload_json"])),
        "no_external_writes": bool(row["no_external_writes"]),
        "no_send_mode": bool(row["no_send_mode"]),
        "live_write": bool(row["live_write"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _attempt_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "attempt_id": row["attempt_id"],
        "intent_id": row["intent_id"],
        "attempt_number": int(row["attempt_number"]),
        "mode": row["mode"],
        "adapter_name": row["adapter_name"],
        "status": row["status"],
        "request_fingerprint": row["request_fingerprint"],
        "response_summary": _deserialize_mapping(row["response_summary_json"]),
        "error_message": row["error_message"],
        "no_external_writes": bool(row["no_external_writes"]),
        "no_send_mode": bool(row["no_send_mode"]),
        "live_write": bool(row["live_write"]),
        "created_at": row["created_at"],
    }


def _idempotency_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "idempotency_key": row["idempotency_key"],
        "target_system": row["target_system"],
        "operation_type": row["operation_type"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "dedupe_key": row["dedupe_key"],
        "payload_fingerprint": row["payload_fingerprint"],
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "status": row["status"],
        "linked_intent_id": row["linked_intent_id"],
        "linked_attempt_id": row["linked_attempt_id"],
    }


def _deserialize_mapping(value_json: str) -> dict[str, Any]:
    value = json.loads(value_json)
    if not isinstance(value, dict):
        raise ValueError("JSON value must decode to an object")
    return value


def _grouped_counts(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    column_name: str,
) -> dict[str, int]:
    allowed = {
        "external_write_intents": {"status", "target_system"},
        "external_write_attempts": {"status", "mode"},
    }
    if table_name not in allowed or column_name not in allowed[table_name]:
        raise ValueError(f"Unsupported side-effect summary group: {table_name}.{column_name}")
    rows = connection.execute(
        f"""
        SELECT {column_name} AS value, COUNT(*) AS value_count
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY {column_name}
        """
    ).fetchall()
    return {row["value"]: int(row["value_count"]) for row in rows}


def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    return int(row[0])


def _permission_decision(
    *,
    category: str,
    allowed: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "allowed": allowed,
        "reason": reason,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

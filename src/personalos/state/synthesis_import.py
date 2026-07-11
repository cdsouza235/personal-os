"""Synthesis-import preview state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.state._shared import (
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_required_text,
    _validate_text,
)

SYNTHESIS_IMPORT_PREVIEW_TABLES = ("synthesis_import_previews",)


SYNTHESIS_IMPORT_SOURCE_TYPES = (
    "chatgpt_synthesis",
    "manual_structured_import",
    "fake_fixture",
)


SYNTHESIS_IMPORT_INPUT_FORMATS = ("json", "markdown_fenced_json", "structured_markdown")


SYNTHESIS_IMPORT_PREVIEW_STATUSES = (
    "draft",
    "validated",
    "rejected",
    "failed",
    "apply_completed",
    "apply_partially_completed",
    "apply_blocked",
    "apply_failed",
)


SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS = 2000


def validate_synthesis_import_source_type(source_type: str) -> str:
    if not isinstance(source_type, str) or source_type not in SYNTHESIS_IMPORT_SOURCE_TYPES:
        allowed = ", ".join(SYNTHESIS_IMPORT_SOURCE_TYPES)
        raise ValueError(f"synthesis import source_type must be one of: {allowed}")
    return source_type


def validate_synthesis_import_input_format(input_format: str) -> str:
    if not isinstance(input_format, str) or input_format not in SYNTHESIS_IMPORT_INPUT_FORMATS:
        allowed = ", ".join(SYNTHESIS_IMPORT_INPUT_FORMATS)
        raise ValueError(f"synthesis import input_format must be one of: {allowed}")
    return input_format


def validate_synthesis_import_preview_status(status: str) -> str:
    if not isinstance(status, str) or status not in SYNTHESIS_IMPORT_PREVIEW_STATUSES:
        allowed = ", ".join(SYNTHESIS_IMPORT_PREVIEW_STATUSES)
        raise ValueError(f"synthesis import preview status must be one of: {allowed}")
    return status


def create_synthesis_import_preview(
    connection: sqlite3.Connection,
    *,
    preview_id: str,
    source_type: str,
    input_format: str,
    input_hash: str,
    raw_excerpt: str,
    parsed_json: Mapping[str, Any],
    preview_report_json: Mapping[str, Any],
    status: str = "validated",
    source_timestamp: str | None = None,
    source_reference: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    preview_id = _validate_required_text("preview_id", preview_id)
    source_type = validate_synthesis_import_source_type(source_type)
    input_format = validate_synthesis_import_input_format(input_format)
    input_hash = _validate_required_text("input_hash", input_hash)
    raw_excerpt = _validate_required_text("raw_excerpt", raw_excerpt)
    if len(raw_excerpt) > SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS:
        raise ValueError(
            "raw_excerpt must be at most "
            f"{SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS} characters"
        )
    parsed_json_text = _serialize_metadata(_validate_metadata("parsed_json", parsed_json))
    preview_report_text = _serialize_metadata(
        _validate_metadata("preview_report_json", preview_report_json)
    )
    status = validate_synthesis_import_preview_status(status)
    if source_timestamp is not None:
        source_timestamp = _validate_iso_datetime("source_timestamp", source_timestamp)
    if source_reference is not None:
        source_reference = _validate_text("source_reference", source_reference)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO synthesis_import_previews (
                id,
                source_type,
                input_format,
                input_hash,
                source_timestamp,
                source_reference,
                raw_excerpt,
                parsed_json,
                preview_report_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preview_id,
                source_type,
                input_format,
                input_hash,
                source_timestamp,
                source_reference,
                raw_excerpt,
                parsed_json_text,
                preview_report_text,
                status,
                created,
                updated,
            ),
        )

    preview = get_synthesis_import_preview(connection, preview_id)
    if preview is None:
        raise RuntimeError(f"Synthesis import preview was not persisted: {preview_id}")
    return preview


def get_synthesis_import_preview(
    connection: sqlite3.Connection,
    preview_id: str,
) -> dict[str, Any] | None:
    preview_id = _validate_required_text("preview_id", preview_id)
    row = connection.execute(
        """
        SELECT
            id,
            source_type,
            input_format,
            input_hash,
            source_timestamp,
            source_reference,
            raw_excerpt,
            parsed_json,
            preview_report_json,
            status,
            created_at,
            updated_at
        FROM synthesis_import_previews
        WHERE id = ?
        """,
        (preview_id,),
    ).fetchone()
    return _synthesis_import_preview_row_to_dict(row) if row is not None else None


def list_synthesis_import_previews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    input_format: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _synthesis_import_preview_filter_clause(
        source_type=source_type,
        input_format=input_format,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            source_type,
            input_format,
            input_hash,
            source_timestamp,
            source_reference,
            raw_excerpt,
            parsed_json,
            preview_report_json,
            status,
            created_at,
            updated_at
        FROM synthesis_import_previews
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_synthesis_import_preview_row_to_dict(row) for row in rows]


def count_synthesis_import_previews(
    connection: sqlite3.Connection,
    *,
    source_type: str | None = None,
    input_format: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _synthesis_import_preview_filter_clause(
        source_type=source_type,
        input_format=input_format,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM synthesis_import_previews {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def update_synthesis_import_preview_status(
    connection: sqlite3.Connection,
    *,
    preview_id: str,
    status: str,
    updated_at: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    preview_id = _validate_required_text("preview_id", preview_id)
    status = validate_synthesis_import_preview_status(status)
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())
    current = get_synthesis_import_preview(connection, preview_id)
    if current is None:
        raise ValueError(f"Synthesis import preview does not exist: {preview_id}")

    if commit:
        with connection:
            connection.execute(
                """
                UPDATE synthesis_import_previews
                SET status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, updated, preview_id),
            )
    else:
        connection.execute(
            """
            UPDATE synthesis_import_previews
            SET status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, updated, preview_id),
        )

    preview = get_synthesis_import_preview(connection, preview_id)
    if preview is None:
        raise RuntimeError(f"Synthesis import preview was not found after update: {preview_id}")
    return preview


def _synthesis_import_preview_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_type": row["source_type"],
        "input_format": row["input_format"],
        "input_hash": row["input_hash"],
        "source_timestamp": row["source_timestamp"],
        "source_reference": row["source_reference"],
        "raw_excerpt": row["raw_excerpt"],
        "parsed_json": _deserialize_metadata(row["parsed_json"]),
        "preview_report_json": _deserialize_metadata(row["preview_report_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _synthesis_import_preview_filter_clause(
    *,
    source_type: str | None,
    input_format: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if source_type is not None:
        clauses.append("source_type = ?")
        values.append(validate_synthesis_import_source_type(source_type))
    if input_format is not None:
        clauses.append("input_format = ?")
        values.append(validate_synthesis_import_input_format(input_format))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_synthesis_import_preview_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


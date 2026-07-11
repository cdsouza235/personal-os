"""Composer packet/output and model-run state helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any

from personalos.state._shared import (
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_bool,
    _validate_iso_date,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_optional_nonnegative_int,
    _validate_required_text,
    _validate_text,
)

COMPOSER_STATE_TABLES = ("composer_packets", "composer_outputs", "model_runs")


COMPOSER_PACKET_TYPES = ("daily_brief", "window_brief", "ad_hoc_preview")


COMPOSER_BRIEFING_WINDOWS = ("morning", "midday", "afternoon", "evening", "none")


COMPOSER_PACKET_STATUSES = (
    "draft",
    "validated",
    "sent_to_fake_model",
    "completed",
    "failed",
    "rejected",
)


COMPOSER_OUTPUT_VALIDATION_STATUSES = ("received", "validated", "rejected", "failed")


COMPOSER_OUTPUT_STATUSES = ("received", "validated", "routed", "rejected", "failed")


MODEL_RUN_ROLES = ("composer_model",)


MODEL_RUN_ADAPTERS = ("fake_composer_adapter",)


MODEL_RUN_STATUSES = ("dry_run", "completed", "failed")


def validate_composer_packet_type(packet_type: str) -> str:
    if not isinstance(packet_type, str) or packet_type not in COMPOSER_PACKET_TYPES:
        allowed = ", ".join(COMPOSER_PACKET_TYPES)
        raise ValueError(f"composer packet_type must be one of: {allowed}")
    return packet_type


def validate_composer_briefing_window(briefing_window: str | None) -> str | None:
    if briefing_window is None:
        return None
    if not isinstance(briefing_window, str) or briefing_window not in COMPOSER_BRIEFING_WINDOWS:
        allowed = ", ".join(COMPOSER_BRIEFING_WINDOWS)
        raise ValueError(f"composer briefing_window must be one of: {allowed}")
    return briefing_window


def validate_composer_packet_status(status: str) -> str:
    if not isinstance(status, str) or status not in COMPOSER_PACKET_STATUSES:
        allowed = ", ".join(COMPOSER_PACKET_STATUSES)
        raise ValueError(f"composer packet status must be one of: {allowed}")
    return status


def validate_composer_output_validation_status(validation_status: str) -> str:
    if (
        not isinstance(validation_status, str)
        or validation_status not in COMPOSER_OUTPUT_VALIDATION_STATUSES
    ):
        allowed = ", ".join(COMPOSER_OUTPUT_VALIDATION_STATUSES)
        raise ValueError(f"composer output validation_status must be one of: {allowed}")
    return validation_status


def validate_composer_output_status(status: str) -> str:
    if not isinstance(status, str) or status not in COMPOSER_OUTPUT_STATUSES:
        allowed = ", ".join(COMPOSER_OUTPUT_STATUSES)
        raise ValueError(f"composer output status must be one of: {allowed}")
    return status


def validate_model_run_role(model_role: str) -> str:
    if not isinstance(model_role, str) or model_role not in MODEL_RUN_ROLES:
        allowed = ", ".join(MODEL_RUN_ROLES)
        raise ValueError(f"model_role must be one of: {allowed}")
    return model_role


def validate_model_run_adapter(adapter_name: str) -> str:
    if not isinstance(adapter_name, str) or adapter_name not in MODEL_RUN_ADAPTERS:
        allowed = ", ".join(MODEL_RUN_ADAPTERS)
        raise ValueError(f"adapter_name must be one of: {allowed}")
    return adapter_name


def validate_model_run_status(status: str) -> str:
    if not isinstance(status, str) or status not in MODEL_RUN_STATUSES:
        allowed = ", ".join(MODEL_RUN_STATUSES)
        raise ValueError(f"model run status must be one of: {allowed}")
    return status


def create_composer_packet(
    connection: sqlite3.Connection,
    *,
    packet_id: str,
    packet_type: str,
    source_date: str,
    timezone: str,
    packet_json: Mapping[str, Any],
    briefing_window: str | None = None,
    status: str = "validated",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    packet_id = _validate_required_text("packet_id", packet_id)
    packet_type = validate_composer_packet_type(packet_type)
    briefing_window = validate_composer_briefing_window(briefing_window)
    source_date = _validate_iso_date("source_date", source_date)
    timezone = _validate_required_text("timezone", timezone)
    packet_json_text = _serialize_metadata(_validate_metadata("packet_json", packet_json))
    status = validate_composer_packet_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO composer_packets (
                id,
                packet_type,
                briefing_window,
                source_date,
                timezone,
                packet_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet_id,
                packet_type,
                briefing_window,
                source_date,
                timezone,
                packet_json_text,
                status,
                created,
                updated,
            ),
        )

    packet = get_composer_packet(connection, packet_id)
    if packet is None:
        raise RuntimeError(f"Composer packet was not persisted: {packet_id}")
    return packet


def get_composer_packet(
    connection: sqlite3.Connection,
    packet_id: str,
) -> dict[str, Any] | None:
    packet_id = _validate_required_text("packet_id", packet_id)
    row = connection.execute(
        """
        SELECT
            id,
            packet_type,
            briefing_window,
            source_date,
            timezone,
            packet_json,
            status,
            created_at,
            updated_at
        FROM composer_packets
        WHERE id = ?
        """,
        (packet_id,),
    ).fetchone()
    return _composer_packet_row_to_dict(row) if row is not None else None


def update_composer_packet_status(
    connection: sqlite3.Connection,
    *,
    packet_id: str,
    status: str,
    updated_at: str | None = None,
) -> dict[str, Any]:
    packet_id = _validate_required_text("packet_id", packet_id)
    status = validate_composer_packet_status(status)
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())
    current = get_composer_packet(connection, packet_id)
    if current is None:
        raise ValueError(f"Composer packet does not exist: {packet_id}")

    with connection:
        connection.execute(
            """
            UPDATE composer_packets
            SET status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (status, updated, packet_id),
        )

    packet = get_composer_packet(connection, packet_id)
    if packet is None:
        raise RuntimeError(f"Composer packet was not found after update: {packet_id}")
    return packet


def list_composer_packets(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    packet_type: str | None = None,
    source_date: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _composer_packet_filter_clause(
        status=status,
        packet_type=packet_type,
        source_date=source_date,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            packet_type,
            briefing_window,
            source_date,
            timezone,
            packet_json,
            status,
            created_at,
            updated_at
        FROM composer_packets
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_composer_packet_row_to_dict(row) for row in rows]


def count_composer_packets(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    packet_type: str | None = None,
    source_date: str | None = None,
) -> int:
    where_clause, values = _composer_packet_filter_clause(
        status=status,
        packet_type=packet_type,
        source_date=source_date,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM composer_packets {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_composer_output(
    connection: sqlite3.Connection,
    *,
    output_id: str,
    packet_id: str,
    output_json: Mapping[str, Any],
    readable_text: str,
    validation_status: str = "validated",
    route_report: Mapping[str, Any] | None = None,
    status: str = "routed",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    output_id = _validate_required_text("output_id", output_id)
    packet_id = _validate_required_text("packet_id", packet_id)
    output_json_text = _serialize_metadata(_validate_metadata("output_json", output_json))
    readable_text = _validate_required_text("readable_text", readable_text)
    validation_status = validate_composer_output_validation_status(validation_status)
    route_report_json = (
        None
        if route_report is None
        else _serialize_metadata(_validate_metadata("route_report", route_report))
    )
    status = validate_composer_output_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO composer_outputs (
                id,
                packet_id,
                output_json,
                readable_text,
                validation_status,
                route_report_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                output_id,
                packet_id,
                output_json_text,
                readable_text,
                validation_status,
                route_report_json,
                status,
                created,
                updated,
            ),
        )

    output = get_composer_output(connection, output_id)
    if output is None:
        raise RuntimeError(f"Composer output was not persisted: {output_id}")
    return output


def get_composer_output(
    connection: sqlite3.Connection,
    output_id: str,
) -> dict[str, Any] | None:
    output_id = _validate_required_text("output_id", output_id)
    row = connection.execute(
        """
        SELECT
            id,
            packet_id,
            output_json,
            readable_text,
            validation_status,
            route_report_json,
            status,
            created_at,
            updated_at
        FROM composer_outputs
        WHERE id = ?
        """,
        (output_id,),
    ).fetchone()
    return _composer_output_row_to_dict(row) if row is not None else None


def list_composer_outputs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _composer_output_filter_clause(
        packet_id=packet_id,
        status=status,
        validation_status=validation_status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            packet_id,
            output_json,
            readable_text,
            validation_status,
            route_report_json,
            status,
            created_at,
            updated_at
        FROM composer_outputs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_composer_output_row_to_dict(row) for row in rows]


def count_composer_outputs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
) -> int:
    where_clause, values = _composer_output_filter_clause(
        packet_id=packet_id,
        status=status,
        validation_status=validation_status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM composer_outputs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_model_run(
    connection: sqlite3.Connection,
    *,
    model_run_id: str,
    packet_id: str,
    model_name: str,
    output_id: str | None = None,
    model_role: str = "composer_model",
    adapter_name: str = "fake_composer_adapter",
    dry_run: bool = True,
    status: str = "completed",
    input_token_count: int | None = None,
    output_token_count: int | None = None,
    error_message: str | None = None,
    created_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    model_run_id = _validate_required_text("model_run_id", model_run_id)
    packet_id = _validate_required_text("packet_id", packet_id)
    if output_id is not None:
        output_id = _validate_required_text("output_id", output_id)
    model_role = validate_model_run_role(model_role)
    model_name = _validate_required_text("model_name", model_name)
    adapter_name = validate_model_run_adapter(adapter_name)
    dry_run = _validate_bool("dry_run", dry_run)
    status = validate_model_run_status(status)
    input_token_count = _validate_optional_nonnegative_int(
        "input_token_count",
        input_token_count,
    )
    output_token_count = _validate_optional_nonnegative_int(
        "output_token_count",
        output_token_count,
    )
    if error_message is not None:
        error_message = _validate_text("error_message", error_message)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    completed = (
        None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at)
    )

    with connection:
        connection.execute(
            """
            INSERT INTO model_runs (
                id,
                packet_id,
                output_id,
                model_role,
                model_name,
                adapter_name,
                dry_run,
                status,
                input_token_count,
                output_token_count,
                error_message,
                created_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model_run_id,
                packet_id,
                output_id,
                model_role,
                model_name,
                adapter_name,
                int(dry_run),
                status,
                input_token_count,
                output_token_count,
                error_message,
                created,
                completed,
            ),
        )

    run = get_model_run(connection, model_run_id)
    if run is None:
        raise RuntimeError(f"Model run was not persisted: {model_run_id}")
    return run


def get_model_run(
    connection: sqlite3.Connection,
    model_run_id: str,
) -> dict[str, Any] | None:
    model_run_id = _validate_required_text("model_run_id", model_run_id)
    row = connection.execute(
        """
        SELECT
            id,
            packet_id,
            output_id,
            model_role,
            model_name,
            adapter_name,
            dry_run,
            status,
            input_token_count,
            output_token_count,
            error_message,
            created_at,
            completed_at
        FROM model_runs
        WHERE id = ?
        """,
        (model_run_id,),
    ).fetchone()
    return _model_run_row_to_dict(row) if row is not None else None


def list_model_runs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _model_run_filter_clause(packet_id=packet_id, status=status)
    rows = connection.execute(
        f"""
        SELECT
            id,
            packet_id,
            output_id,
            model_role,
            model_name,
            adapter_name,
            dry_run,
            status,
            input_token_count,
            output_token_count,
            error_message,
            created_at,
            completed_at
        FROM model_runs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_model_run_row_to_dict(row) for row in rows]


def count_model_runs(
    connection: sqlite3.Connection,
    *,
    packet_id: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _model_run_filter_clause(packet_id=packet_id, status=status)
    row = connection.execute(
        f"SELECT COUNT(*) FROM model_runs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def _composer_packet_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "packet_type": row["packet_type"],
        "briefing_window": row["briefing_window"],
        "source_date": row["source_date"],
        "timezone": row["timezone"],
        "packet_json": _deserialize_metadata(row["packet_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _composer_output_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "packet_id": row["packet_id"],
        "output_json": _deserialize_metadata(row["output_json"]),
        "readable_text": row["readable_text"],
        "validation_status": row["validation_status"],
        "route_report": (
            None
            if row["route_report_json"] is None
            else _deserialize_metadata(row["route_report_json"])
        ),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _model_run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "packet_id": row["packet_id"],
        "output_id": row["output_id"],
        "model_role": row["model_role"],
        "model_name": row["model_name"],
        "adapter_name": row["adapter_name"],
        "dry_run": bool(row["dry_run"]),
        "status": row["status"],
        "input_token_count": row["input_token_count"],
        "output_token_count": row["output_token_count"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _composer_packet_filter_clause(
    *,
    status: str | None,
    packet_type: str | None,
    source_date: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if status is not None:
        clauses.append("status = ?")
        values.append(validate_composer_packet_status(status))
    if packet_type is not None:
        clauses.append("packet_type = ?")
        values.append(validate_composer_packet_type(packet_type))
    if source_date is not None:
        clauses.append("source_date = ?")
        values.append(_validate_iso_date("source_date", source_date))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _composer_output_filter_clause(
    *,
    packet_id: str | None,
    status: str | None,
    validation_status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if packet_id is not None:
        clauses.append("packet_id = ?")
        values.append(_validate_required_text("packet_id", packet_id))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_composer_output_status(status))
    if validation_status is not None:
        clauses.append("validation_status = ?")
        values.append(validate_composer_output_validation_status(validation_status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _model_run_filter_clause(
    *,
    packet_id: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if packet_id is not None:
        clauses.append("packet_id = ?")
        values.append(_validate_required_text("packet_id", packet_id))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_model_run_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


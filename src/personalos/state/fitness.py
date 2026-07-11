"""Fitness integration/validation/file-contract state helpers."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any

from personalos.state._shared import (
    _deserialize_metadata,
    _serialize_metadata,
    _utc_now,
    _validate_bool,
    _validate_iso_datetime,
    _validate_metadata,
    _validate_required_text,
    _validate_text,
)

FITNESS_STATE_TABLES = (
    "fitness_integration_state",
    "fitness_validation_runs",
    "fitness_file_contracts",
)


FITNESS_INTEGRATION_TYPES = ("local_csv_tracker",)


FITNESS_INTEGRATION_STATUSES = ("draft", "configured", "validated", "warning", "disabled")


FITNESS_VALIDATION_RUN_TYPES = ("fixture_validation", "schema_preview", "dry_run")


FITNESS_VALIDATION_RUN_STATUSES = ("started", "completed", "failed")


FITNESS_FILE_ROLES = (
    "workout_sessions",
    "workout_exercises",
    "weekly_recovery",
    "exercise_library",
)


FITNESS_FILE_CONTRACT_STATUSES = ("draft", "active", "deprecated")


def validate_fitness_integration_type(integration_type: str) -> str:
    if not isinstance(integration_type, str) or integration_type not in FITNESS_INTEGRATION_TYPES:
        allowed = ", ".join(FITNESS_INTEGRATION_TYPES)
        raise ValueError(f"fitness integration_type must be one of: {allowed}")
    return integration_type


def validate_fitness_integration_status(status: str) -> str:
    if not isinstance(status, str) or status not in FITNESS_INTEGRATION_STATUSES:
        allowed = ", ".join(FITNESS_INTEGRATION_STATUSES)
        raise ValueError(f"fitness integration status must be one of: {allowed}")
    return status


def validate_fitness_validation_run_type(run_type: str) -> str:
    if not isinstance(run_type, str) or run_type not in FITNESS_VALIDATION_RUN_TYPES:
        allowed = ", ".join(FITNESS_VALIDATION_RUN_TYPES)
        raise ValueError(f"fitness validation run_type must be one of: {allowed}")
    return run_type


def validate_fitness_validation_run_status(status: str) -> str:
    if not isinstance(status, str) or status not in FITNESS_VALIDATION_RUN_STATUSES:
        allowed = ", ".join(FITNESS_VALIDATION_RUN_STATUSES)
        raise ValueError(f"fitness validation run status must be one of: {allowed}")
    return status


def validate_fitness_file_role(file_role: str) -> str:
    if not isinstance(file_role, str) or file_role not in FITNESS_FILE_ROLES:
        allowed = ", ".join(FITNESS_FILE_ROLES)
        raise ValueError(f"fitness file_role must be one of: {allowed}")
    return file_role


def validate_fitness_file_contract_status(status: str) -> str:
    if not isinstance(status, str) or status not in FITNESS_FILE_CONTRACT_STATUSES:
        allowed = ", ".join(FITNESS_FILE_CONTRACT_STATUSES)
        raise ValueError(f"fitness file contract status must be one of: {allowed}")
    return status


def create_fitness_integration_state(
    connection: sqlite3.Connection,
    *,
    state_id: str,
    integration_name: str,
    integration_type: str,
    status: str,
    data_root_label: str,
    expected_files_json: Sequence[str],
    last_validation_at: str | None = None,
    last_summary_json: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    state_id = _validate_required_text("state_id", state_id)
    integration_name = _validate_required_text("integration_name", integration_name)
    integration_type = validate_fitness_integration_type(integration_type)
    status = validate_fitness_integration_status(status)
    data_root_label = _validate_required_text("data_root_label", data_root_label)
    expected_files_json_text = _serialize_string_list(
        "expected_files_json",
        expected_files_json,
    )
    if last_validation_at is not None:
        last_validation_at = _validate_iso_datetime("last_validation_at", last_validation_at)
    last_summary_json_text = (
        None
        if last_summary_json is None
        else _serialize_metadata(_validate_metadata("last_summary_json", last_summary_json))
    )
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO fitness_integration_state (
                id,
                integration_name,
                integration_type,
                status,
                data_root_label,
                expected_files_json,
                last_validation_at,
                last_summary_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state_id,
                integration_name,
                integration_type,
                status,
                data_root_label,
                expected_files_json_text,
                last_validation_at,
                last_summary_json_text,
                created,
                updated,
            ),
        )

    state = get_fitness_integration_state(connection, state_id)
    if state is None:
        raise RuntimeError(f"Fitness integration state was not persisted: {state_id}")
    return state


def update_fitness_integration_state(
    connection: sqlite3.Connection,
    *,
    state_id: str,
    integration_name: str | None = None,
    status: str | None = None,
    expected_files_json: Sequence[str] | None = None,
    last_validation_at: str | None = None,
    last_summary_json: Mapping[str, Any] | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    state_id = _validate_required_text("state_id", state_id)
    if (
        integration_name is None
        and status is None
        and expected_files_json is None
        and last_validation_at is None
        and last_summary_json is None
    ):
        raise ValueError("at least one fitness integration state field must be provided")

    current = get_fitness_integration_state(connection, state_id)
    if current is None:
        raise ValueError(f"Fitness integration state does not exist: {state_id}")

    next_name = (
        current["integration_name"]
        if integration_name is None
        else _validate_required_text("integration_name", integration_name)
    )
    next_status = (
        current["status"] if status is None else validate_fitness_integration_status(status)
    )
    next_expected_files = (
        current["expected_files_json"]
        if expected_files_json is None
        else _validate_string_list("expected_files_json", expected_files_json)
    )
    next_last_validation_at = current["last_validation_at"]
    if last_validation_at is not None:
        next_last_validation_at = _validate_iso_datetime("last_validation_at", last_validation_at)
    next_summary = (
        current["last_summary_json"]
        if last_summary_json is None
        else _validate_metadata("last_summary_json", last_summary_json)
    )
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())

    with connection:
        connection.execute(
            """
            UPDATE fitness_integration_state
            SET integration_name = ?,
                status = ?,
                expected_files_json = ?,
                last_validation_at = ?,
                last_summary_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                next_name,
                next_status,
                _serialize_string_list("expected_files_json", next_expected_files),
                next_last_validation_at,
                None if next_summary is None else _serialize_metadata(next_summary),
                updated,
                state_id,
            ),
        )

    state = get_fitness_integration_state(connection, state_id)
    if state is None:
        raise RuntimeError(f"Fitness integration state was not found after update: {state_id}")
    return state


def get_fitness_integration_state(
    connection: sqlite3.Connection,
    state_id: str,
) -> dict[str, Any] | None:
    state_id = _validate_required_text("state_id", state_id)
    row = connection.execute(
        """
        SELECT
            id,
            integration_name,
            integration_type,
            status,
            data_root_label,
            expected_files_json,
            last_validation_at,
            last_summary_json,
            created_at,
            updated_at
        FROM fitness_integration_state
        WHERE id = ?
        """,
        (state_id,),
    ).fetchone()
    return _fitness_integration_state_row_to_dict(row) if row is not None else None


def list_fitness_integration_states(
    connection: sqlite3.Connection,
    *,
    integration_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _fitness_integration_state_filter_clause(
        integration_type=integration_type,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            integration_name,
            integration_type,
            status,
            data_root_label,
            expected_files_json,
            last_validation_at,
            last_summary_json,
            created_at,
            updated_at
        FROM fitness_integration_state
        {where_clause}
        ORDER BY integration_name, id
        """,
        values,
    ).fetchall()
    return [_fitness_integration_state_row_to_dict(row) for row in rows]


def count_fitness_integration_states(
    connection: sqlite3.Connection,
    *,
    integration_type: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _fitness_integration_state_filter_clause(
        integration_type=integration_type,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM fitness_integration_state {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_fitness_validation_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    integration_state_id: str,
    run_type: str,
    dry_run: bool,
    status: str,
    input_json: Mapping[str, Any],
    output_json: Mapping[str, Any],
    error_message: str | None = None,
    created_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    run_id = _validate_required_text("run_id", run_id)
    integration_state_id = _validate_required_text("integration_state_id", integration_state_id)
    run_type = validate_fitness_validation_run_type(run_type)
    dry_run = _validate_bool("dry_run", dry_run)
    status = validate_fitness_validation_run_status(status)
    input_json_text = _serialize_metadata(_validate_metadata("input_json", input_json))
    output_json_text = _serialize_metadata(_validate_metadata("output_json", output_json))
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
            INSERT INTO fitness_validation_runs (
                id,
                integration_state_id,
                run_type,
                dry_run,
                status,
                input_json,
                output_json,
                error_message,
                created_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                integration_state_id,
                run_type,
                int(dry_run),
                status,
                input_json_text,
                output_json_text,
                error_message,
                created,
                completed,
            ),
        )

    run = get_fitness_validation_run(connection, run_id)
    if run is None:
        raise RuntimeError(f"Fitness validation run was not persisted: {run_id}")
    return run


def update_fitness_validation_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    output_json: Mapping[str, Any] | None = None,
    error_message: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    run_id = _validate_required_text("run_id", run_id)
    current = get_fitness_validation_run(connection, run_id)
    if current is None:
        raise ValueError(f"Fitness validation run does not exist: {run_id}")

    status = validate_fitness_validation_run_status(status)
    next_output = current["output_json"] if output_json is None else output_json
    output_json_text = _serialize_metadata(_validate_metadata("output_json", next_output))
    if error_message is not None:
        error_message = _validate_text("error_message", error_message)
    completed = (
        None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at)
    )

    with connection:
        connection.execute(
            """
            UPDATE fitness_validation_runs
            SET status = ?,
                output_json = ?,
                error_message = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (status, output_json_text, error_message, completed, run_id),
        )

    run = get_fitness_validation_run(connection, run_id)
    if run is None:
        raise RuntimeError(f"Fitness validation run was not found after update: {run_id}")
    return run


def get_fitness_validation_run(
    connection: sqlite3.Connection,
    run_id: str,
) -> dict[str, Any] | None:
    run_id = _validate_required_text("run_id", run_id)
    row = connection.execute(
        """
        SELECT
            id,
            integration_state_id,
            run_type,
            dry_run,
            status,
            input_json,
            output_json,
            error_message,
            created_at,
            completed_at
        FROM fitness_validation_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    return _fitness_validation_run_row_to_dict(row) if row is not None else None


def list_fitness_validation_runs(
    connection: sqlite3.Connection,
    *,
    integration_state_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _fitness_validation_run_filter_clause(
        integration_state_id=integration_state_id,
        run_type=run_type,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            integration_state_id,
            run_type,
            dry_run,
            status,
            input_json,
            output_json,
            error_message,
            created_at,
            completed_at
        FROM fitness_validation_runs
        {where_clause}
        ORDER BY created_at DESC, id
        """,
        values,
    ).fetchall()
    return [_fitness_validation_run_row_to_dict(row) for row in rows]


def count_fitness_validation_runs(
    connection: sqlite3.Connection,
    *,
    integration_state_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _fitness_validation_run_filter_clause(
        integration_state_id=integration_state_id,
        run_type=run_type,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM fitness_validation_runs {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def create_fitness_file_contract(
    connection: sqlite3.Connection,
    *,
    contract_id: str,
    file_name: str,
    file_role: str,
    required_columns_json: Sequence[str],
    optional_columns_json: Sequence[str],
    status: str = "draft",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    contract_id = _validate_required_text("contract_id", contract_id)
    file_name = _validate_required_text("file_name", file_name)
    file_role = validate_fitness_file_role(file_role)
    required_columns_json_text = _serialize_string_list(
        "required_columns_json",
        required_columns_json,
    )
    optional_columns_json_text = _serialize_string_list(
        "optional_columns_json",
        optional_columns_json,
    )
    status = validate_fitness_file_contract_status(status)
    created = _validate_iso_datetime("created_at", created_at or _utc_now())
    updated = _validate_iso_datetime("updated_at", updated_at or created)

    with connection:
        connection.execute(
            """
            INSERT INTO fitness_file_contracts (
                id,
                file_name,
                file_role,
                required_columns_json,
                optional_columns_json,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contract_id,
                file_name,
                file_role,
                required_columns_json_text,
                optional_columns_json_text,
                status,
                created,
                updated,
            ),
        )

    contract = get_fitness_file_contract(connection, contract_id)
    if contract is None:
        raise RuntimeError(f"Fitness file contract was not persisted: {contract_id}")
    return contract


def update_fitness_file_contract(
    connection: sqlite3.Connection,
    *,
    contract_id: str,
    required_columns_json: Sequence[str] | None = None,
    optional_columns_json: Sequence[str] | None = None,
    status: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    contract_id = _validate_required_text("contract_id", contract_id)
    if required_columns_json is None and optional_columns_json is None and status is None:
        raise ValueError("at least one fitness file contract field must be provided")

    current = get_fitness_file_contract(connection, contract_id)
    if current is None:
        raise ValueError(f"Fitness file contract does not exist: {contract_id}")

    next_required = (
        current["required_columns_json"]
        if required_columns_json is None
        else _validate_string_list("required_columns_json", required_columns_json)
    )
    next_optional = (
        current["optional_columns_json"]
        if optional_columns_json is None
        else _validate_string_list("optional_columns_json", optional_columns_json)
    )
    next_status = (
        current["status"] if status is None else validate_fitness_file_contract_status(status)
    )
    updated = _validate_iso_datetime("updated_at", updated_at or _utc_now())

    with connection:
        connection.execute(
            """
            UPDATE fitness_file_contracts
            SET required_columns_json = ?,
                optional_columns_json = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                _serialize_string_list("required_columns_json", next_required),
                _serialize_string_list("optional_columns_json", next_optional),
                next_status,
                updated,
                contract_id,
            ),
        )

    contract = get_fitness_file_contract(connection, contract_id)
    if contract is None:
        raise RuntimeError(f"Fitness file contract was not found after update: {contract_id}")
    return contract


def get_fitness_file_contract(
    connection: sqlite3.Connection,
    contract_id: str,
) -> dict[str, Any] | None:
    contract_id = _validate_required_text("contract_id", contract_id)
    row = connection.execute(
        """
        SELECT
            id,
            file_name,
            file_role,
            required_columns_json,
            optional_columns_json,
            status,
            created_at,
            updated_at
        FROM fitness_file_contracts
        WHERE id = ?
        """,
        (contract_id,),
    ).fetchone()
    return _fitness_file_contract_row_to_dict(row) if row is not None else None


def list_fitness_file_contracts(
    connection: sqlite3.Connection,
    *,
    file_role: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, values = _fitness_file_contract_filter_clause(
        file_role=file_role,
        status=status,
    )
    rows = connection.execute(
        f"""
        SELECT
            id,
            file_name,
            file_role,
            required_columns_json,
            optional_columns_json,
            status,
            created_at,
            updated_at
        FROM fitness_file_contracts
        {where_clause}
        ORDER BY file_role, file_name, id
        """,
        values,
    ).fetchall()
    return [_fitness_file_contract_row_to_dict(row) for row in rows]


def count_fitness_file_contracts(
    connection: sqlite3.Connection,
    *,
    file_role: str | None = None,
    status: str | None = None,
) -> int:
    where_clause, values = _fitness_file_contract_filter_clause(
        file_role=file_role,
        status=status,
    )
    row = connection.execute(
        f"SELECT COUNT(*) FROM fitness_file_contracts {where_clause}",
        values,
    ).fetchone()
    return int(row[0])


def _fitness_integration_state_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "integration_name": row["integration_name"],
        "integration_type": row["integration_type"],
        "status": row["status"],
        "data_root_label": row["data_root_label"],
        "expected_files_json": _deserialize_string_list(row["expected_files_json"]),
        "last_validation_at": row["last_validation_at"],
        "last_summary_json": (
            None
            if row["last_summary_json"] is None
            else _deserialize_metadata(row["last_summary_json"])
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _fitness_validation_run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "integration_state_id": row["integration_state_id"],
        "run_type": row["run_type"],
        "dry_run": bool(row["dry_run"]),
        "status": row["status"],
        "input_json": _deserialize_metadata(row["input_json"]),
        "output_json": _deserialize_metadata(row["output_json"]),
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _fitness_file_contract_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "file_name": row["file_name"],
        "file_role": row["file_role"],
        "required_columns_json": _deserialize_string_list(row["required_columns_json"]),
        "optional_columns_json": _deserialize_string_list(row["optional_columns_json"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _fitness_integration_state_filter_clause(
    *,
    integration_type: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if integration_type is not None:
        clauses.append("integration_type = ?")
        values.append(validate_fitness_integration_type(integration_type))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_fitness_integration_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _fitness_validation_run_filter_clause(
    *,
    integration_state_id: str | None,
    run_type: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if integration_state_id is not None:
        clauses.append("integration_state_id = ?")
        values.append(_validate_required_text("integration_state_id", integration_state_id))
    if run_type is not None:
        clauses.append("run_type = ?")
        values.append(validate_fitness_validation_run_type(run_type))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_fitness_validation_run_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _fitness_file_contract_filter_clause(
    *,
    file_role: str | None,
    status: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    values: list[Any] = []

    if file_role is not None:
        clauses.append("file_role = ?")
        values.append(validate_fitness_file_role(file_role))
    if status is not None:
        clauses.append("status = ?")
        values.append(validate_fitness_file_contract_status(status))

    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(values)


def _serialize_string_list(field_name: str, value: Sequence[str]) -> str:
    return json.dumps(
        _validate_string_list(field_name, value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deserialize_string_list(value_json: str) -> list[str]:
    value = json.loads(value_json)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("JSON value must decode to a list of strings")
    return value


def _validate_string_list(field_name: str, value: Sequence[str]) -> list[str]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"{field_name} must be a list of strings")
    items = list(value)
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return items


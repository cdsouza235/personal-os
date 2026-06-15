"""Dev/test-only fitness integration contract and validation foundation."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from personalos.permissions import PermissionMode
from personalos.state import (
    FITNESS_FILE_CONTRACT_STATUSES,
    FITNESS_FILE_ROLES,
    FITNESS_INTEGRATION_STATUSES,
    FITNESS_INTEGRATION_TYPES,
    FITNESS_VALIDATION_RUN_STATUSES,
    FITNESS_VALIDATION_RUN_TYPES,
    count_fitness_file_contracts,
    count_fitness_integration_states,
    count_fitness_validation_runs,
    create_fitness_file_contract,
    create_fitness_integration_state,
    create_fitness_validation_run,
    get_fitness_file_contract,
    get_fitness_integration_state,
    get_fitness_validation_run,
    get_permission_setting,
    list_fitness_file_contracts,
    list_fitness_integration_states,
    list_fitness_validation_runs,
    update_fitness_file_contract,
    update_fitness_integration_state,
    validate_fitness_file_contract_status,
    validate_fitness_file_role,
    validate_fitness_integration_status,
    validate_fitness_integration_type,
    validate_fitness_validation_run_status,
    validate_fitness_validation_run_type,
)

FITNESS_INTEGRATION_READ_PERMISSION = "fitness_integration_dev_test_read"
FITNESS_INTEGRATION_WRITE_PERMISSION = "fitness_integration_dev_test_write"
FITNESS_INTEGRATION_VALIDATE_PERMISSION = "fitness_integration_dev_test_validate"

FITNESS_INTEGRATION_STATE_SCHEMA_VERSION = "fitness_integration_state.v1"
FITNESS_FILE_CONTRACT_SCHEMA_VERSION = "fitness_file_contract.v1"
FITNESS_VALIDATION_RUN_SCHEMA_VERSION = "fitness_validation_run.v1"
FITNESS_VALIDATION_REPORT_SCHEMA_VERSION = "fitness_validation_report.v1"

FITNESS_DATA_ROOT_LABEL = "personal_os_fitness_csvs"

WORKOUT_SESSIONS_FILE = "workout_sessions.csv"
WORKOUT_EXERCISES_FILE = "workout_exercises.csv"
WEEKLY_RECOVERY_FILE = "weekly_recovery.csv"
EXERCISE_LIBRARY_FILE = "exercise_library.csv"

EXPECTED_FITNESS_CSV_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "file_name": WORKOUT_SESSIONS_FILE,
        "file_role": "workout_sessions",
        "required_columns_json": (
            "session_id",
            "date",
            "session_name",
            "duration_minutes",
            "active_calories",
            "total_calories",
            "avg_hr",
            "data_source",
            "parse_confidence",
        ),
        "optional_columns_json": (),
    },
    {
        "file_name": WORKOUT_EXERCISES_FILE,
        "file_role": "workout_exercises",
        "required_columns_json": (
            "session_id",
            "exercise_id",
            "exercise_name",
            "sets",
            "total_reps",
            "max_load_lbs",
            "hold_seconds",
            "progression_note",
        ),
        "optional_columns_json": (),
    },
    {
        "file_name": WEEKLY_RECOVERY_FILE,
        "file_role": "weekly_recovery",
        "required_columns_json": (
            "week_start",
            "resting_hr",
            "sleep_hr_min",
            "sleep_hr_max",
            "time_asleep_hours",
            "awake_time_minutes",
            "rem_hours",
            "core_hours",
            "deep_hours",
        ),
        "optional_columns_json": (),
    },
    {
        "file_name": EXERCISE_LIBRARY_FILE,
        "file_role": "exercise_library",
        "required_columns_json": (
            "exercise_id",
            "canonical_name",
            "aliases",
            "category",
            "status",
        ),
        "optional_columns_json": (),
    },
)
EXPECTED_FITNESS_FILE_NAMES = tuple(
    contract["file_name"] for contract in EXPECTED_FITNESS_CSV_CONTRACTS
)


class FitnessIntegrationPermissionDenied(PermissionError):
    """Raised when fitness integration permission settings do not allow the action."""


class FitnessValidationError(ValueError):
    """Raised when a fitness integration contract or validation run is invalid."""


def build_expected_fitness_file_contract_records(
    *,
    created_at: str,
    status: str = "active",
) -> list[dict[str, Any]]:
    created_at = _validate_iso_datetime("created_at", created_at)
    status = validate_fitness_file_contract_status(status)
    return [
        {
            "schema_version": FITNESS_FILE_CONTRACT_SCHEMA_VERSION,
            "id": stable_fitness_id("fitness-contract", contract["file_role"]),
            "file_name": contract["file_name"],
            "file_role": contract["file_role"],
            "required_columns_json": list(contract["required_columns_json"]),
            "optional_columns_json": list(contract["optional_columns_json"]),
            "status": status,
            "created_at": created_at,
            "updated_at": created_at,
        }
        for contract in EXPECTED_FITNESS_CSV_CONTRACTS
    ]


def build_default_fitness_integration_state(
    *,
    state_id: str = "fitness-local-csv-tracker",
    created_at: str,
    status: str = "draft",
) -> dict[str, Any]:
    created_at = _validate_iso_datetime("created_at", created_at)
    return {
        "schema_version": FITNESS_INTEGRATION_STATE_SCHEMA_VERSION,
        "id": _validate_required_text("state_id", state_id),
        "integration_name": "Local CSV fitness tracker",
        "integration_type": "local_csv_tracker",
        "status": validate_fitness_integration_status(status),
        "data_root_label": FITNESS_DATA_ROOT_LABEL,
        "expected_files_json": list(EXPECTED_FITNESS_FILE_NAMES),
        "last_validation_at": None,
        "last_summary_json": None,
        "created_at": created_at,
        "updated_at": created_at,
    }


def validate_fitness_integration_state(state: Mapping[str, Any]) -> dict[str, Any]:
    state = _require_mapping(state, "fitness_integration_state")
    _require_keys(
        "fitness_integration_state",
        state,
        {
            "id",
            "integration_name",
            "integration_type",
            "status",
            "data_root_label",
            "expected_files_json",
            "created_at",
            "updated_at",
        },
    )

    data_root_label = _validate_label("data_root_label", state["data_root_label"])
    expected_files = _validate_expected_files(state["expected_files_json"])
    last_validation_at = state.get("last_validation_at")
    last_summary_json = state.get("last_summary_json")
    return {
        "schema_version": str(
            state.get("schema_version", FITNESS_INTEGRATION_STATE_SCHEMA_VERSION)
        ),
        "id": _validate_required_text("id", state["id"]),
        "integration_name": _validate_required_text(
            "integration_name",
            state["integration_name"],
        ),
        "integration_type": validate_fitness_integration_type(str(state["integration_type"])),
        "status": validate_fitness_integration_status(str(state["status"])),
        "data_root_label": data_root_label,
        "expected_files_json": expected_files,
        "last_validation_at": None
        if last_validation_at is None
        else _validate_iso_datetime("last_validation_at", last_validation_at),
        "last_summary_json": None
        if last_summary_json is None
        else _validate_metadata("last_summary_json", last_summary_json),
        "created_at": _validate_iso_datetime("created_at", state["created_at"]),
        "updated_at": _validate_iso_datetime("updated_at", state["updated_at"]),
    }


def validate_fitness_file_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    contract = _require_mapping(contract, "fitness_file_contract")
    _require_keys(
        "fitness_file_contract",
        contract,
        {
            "id",
            "file_name",
            "file_role",
            "required_columns_json",
            "optional_columns_json",
            "status",
            "created_at",
            "updated_at",
        },
    )

    file_name = _validate_file_name("file_name", contract["file_name"])
    file_role = validate_fitness_file_role(str(contract["file_role"]))
    required_columns = _validate_column_list(
        "required_columns_json",
        contract["required_columns_json"],
    )
    optional_columns = _validate_column_list(
        "optional_columns_json",
        contract["optional_columns_json"],
    )
    minimal_columns = _required_columns_for_role(file_role)
    missing = sorted(set(minimal_columns) - set(required_columns))
    if missing:
        raise FitnessValidationError(
            "fitness file contract missing required columns: " + ", ".join(missing)
        )

    return {
        "schema_version": str(
            contract.get("schema_version", FITNESS_FILE_CONTRACT_SCHEMA_VERSION)
        ),
        "id": _validate_required_text("id", contract["id"]),
        "file_name": file_name,
        "file_role": file_role,
        "required_columns_json": required_columns,
        "optional_columns_json": optional_columns,
        "status": validate_fitness_file_contract_status(str(contract["status"])),
        "created_at": _validate_iso_datetime("created_at", contract["created_at"]),
        "updated_at": _validate_iso_datetime("updated_at", contract["updated_at"]),
    }


def validate_expected_fitness_file_contracts(
    contracts: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    selected_contracts = (
        build_expected_fitness_file_contract_records(created_at=_utc_now())
        if contracts is None
        else contracts
    )
    validated = [validate_fitness_file_contract(contract) for contract in selected_contracts]
    roles = {contract["file_role"] for contract in validated}
    missing_roles = sorted(set(FITNESS_FILE_ROLES) - roles)
    if missing_roles:
        raise FitnessValidationError(
            "fitness file contracts missing required roles: " + ", ".join(missing_roles)
        )
    return validated


def validate_fitness_validation_run(run: Mapping[str, Any]) -> dict[str, Any]:
    run = _require_mapping(run, "fitness_validation_run")
    _require_keys(
        "fitness_validation_run",
        run,
        {
            "id",
            "integration_state_id",
            "run_type",
            "dry_run",
            "status",
            "input_json",
            "output_json",
            "created_at",
        },
    )

    output_json = _validate_metadata("output_json", run["output_json"])
    _validate_validation_output_safety(output_json)
    error_message = run.get("error_message")
    completed_at = run.get("completed_at")
    return {
        "schema_version": str(
            run.get("schema_version", FITNESS_VALIDATION_RUN_SCHEMA_VERSION)
        ),
        "id": _validate_required_text("id", run["id"]),
        "integration_state_id": _validate_required_text(
            "integration_state_id",
            run["integration_state_id"],
        ),
        "run_type": validate_fitness_validation_run_type(str(run["run_type"])),
        "dry_run": _validate_bool("dry_run", run["dry_run"]),
        "status": validate_fitness_validation_run_status(str(run["status"])),
        "input_json": _validate_metadata("input_json", run["input_json"]),
        "output_json": output_json,
        "error_message": None
        if error_message is None
        else _validate_text("error_message", error_message),
        "created_at": _validate_iso_datetime("created_at", run["created_at"]),
        "completed_at": None
        if completed_at is None
        else _validate_iso_datetime("completed_at", completed_at),
    }


def validate_fixture_csv_headers(
    fixture_headers: Mapping[str, Sequence[str] | str],
    *,
    contracts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    fixture_headers = _require_mapping(fixture_headers, "fixture_headers")
    validated_contracts = validate_expected_fitness_file_contracts(contracts)
    checked_files: list[dict[str, Any]] = []
    missing_required_columns: dict[str, list[str]] = {}
    extra_columns: dict[str, list[str]] = {}
    warnings: list[str] = []

    for contract in validated_contracts:
        file_name = contract["file_name"]
        required_columns = set(contract["required_columns_json"])
        optional_columns = set(contract["optional_columns_json"])
        raw_headers = fixture_headers.get(file_name)

        if raw_headers is None:
            missing = sorted(required_columns)
            missing_required_columns[file_name] = missing
            warnings.append(f"{file_name} fixture headers were not supplied.")
            checked_files.append(
                {
                    "file_name": file_name,
                    "file_role": contract["file_role"],
                    "headers_present": False,
                    "status": "missing_fixture",
                }
            )
            continue

        headers = _parse_header_input(file_name, raw_headers)
        missing = sorted(required_columns - set(headers))
        extras = sorted(set(headers) - required_columns - optional_columns)
        if missing:
            missing_required_columns[file_name] = missing
        if extras:
            extra_columns[file_name] = extras
            warnings.append(f"{file_name} has extra fixture columns: {', '.join(extras)}.")

        checked_files.append(
            {
                "file_name": file_name,
                "file_role": contract["file_role"],
                "headers_present": True,
                "status": "missing_required_columns" if missing else "valid",
                "columns_checked": headers,
            }
        )

    return {
        "checked_files": checked_files,
        "missing_required_columns": missing_required_columns,
        "extra_columns": extra_columns,
        "warnings": warnings,
    }


def build_fitness_validation_report(
    *,
    integration_state: Mapping[str, Any],
    fixture_headers: Mapping[str, Sequence[str] | str],
    run_type: str = "fixture_validation",
    generated_at: str | None = None,
    contracts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    validated_state = validate_fitness_integration_state(integration_state)
    run_type = validate_fitness_validation_run_type(run_type)
    generated_at = _validate_iso_datetime("generated_at", generated_at or _utc_now())
    header_result = validate_fixture_csv_headers(fixture_headers, contracts=contracts)
    status = "failed" if header_result["missing_required_columns"] else "completed"
    return {
        "schema_version": FITNESS_VALIDATION_REPORT_SCHEMA_VERSION,
        "integration_state_id": validated_state["id"],
        "run_type": run_type,
        "status": status,
        "generated_at": generated_at,
        "data_root_label": validated_state["data_root_label"],
        "checked_files": header_result["checked_files"],
        "missing_required_columns": header_result["missing_required_columns"],
        "extra_columns": header_result["extra_columns"],
        "warnings": header_result["warnings"],
        "no_external_writes": True,
        "no_live_personalos_access": True,
    }


def build_fitness_schema_preview_report(
    *,
    integration_state: Mapping[str, Any],
    generated_at: str | None = None,
    contracts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    validated_state = validate_fitness_integration_state(integration_state)
    generated_at = _validate_iso_datetime("generated_at", generated_at or _utc_now())
    validated_contracts = validate_expected_fitness_file_contracts(contracts)
    checked_files = [
        {
            "file_name": contract["file_name"],
            "file_role": contract["file_role"],
            "headers_present": False,
            "status": "contract_preview",
            "required_columns": contract["required_columns_json"],
            "optional_columns": contract["optional_columns_json"],
        }
        for contract in validated_contracts
    ]
    return {
        "schema_version": FITNESS_VALIDATION_REPORT_SCHEMA_VERSION,
        "integration_state_id": validated_state["id"],
        "run_type": "schema_preview",
        "status": "completed",
        "generated_at": generated_at,
        "data_root_label": validated_state["data_root_label"],
        "checked_files": checked_files,
        "missing_required_columns": {},
        "extra_columns": {},
        "warnings": [],
        "no_external_writes": True,
        "no_live_personalos_access": True,
    }


def create_fitness_integration_state_record(
    connection: sqlite3.Connection,
    *,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_fitness_integration_state(state)
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    created = create_fitness_integration_state(
        connection,
        state_id=validated["id"],
        integration_name=validated["integration_name"],
        integration_type=validated["integration_type"],
        status=validated["status"],
        data_root_label=validated["data_root_label"],
        expected_files_json=validated["expected_files_json"],
        last_validation_at=validated["last_validation_at"],
        last_summary_json=validated["last_summary_json"],
        created_at=validated["created_at"],
        updated_at=validated["updated_at"],
    )
    return {
        "status": "created",
        "reason": "Fitness integration state was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "fitness_integration_state": created,
    }


def update_fitness_integration_state_record(
    connection: sqlite3.Connection,
    *,
    state_id: str,
    status: str | None = None,
    last_validation_at: str | None = None,
    last_summary_json: Mapping[str, Any] | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    updated = update_fitness_integration_state(
        connection,
        state_id=state_id,
        status=status,
        last_validation_at=last_validation_at,
        last_summary_json=last_summary_json,
        updated_at=updated_at,
    )
    return {
        "status": "updated",
        "reason": "Fitness integration state was updated in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "fitness_integration_state": updated,
    }


def create_fitness_file_contract_record(
    connection: sqlite3.Connection,
    *,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_fitness_file_contract(contract)
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    created = create_fitness_file_contract(
        connection,
        contract_id=validated["id"],
        file_name=validated["file_name"],
        file_role=validated["file_role"],
        required_columns_json=validated["required_columns_json"],
        optional_columns_json=validated["optional_columns_json"],
        status=validated["status"],
        created_at=validated["created_at"],
        updated_at=validated["updated_at"],
    )
    return {
        "status": "created",
        "reason": "Fitness file contract was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "fitness_file_contract": created,
    }


def update_fitness_file_contract_record(
    connection: sqlite3.Connection,
    *,
    contract_id: str,
    required_columns_json: Sequence[str] | None = None,
    optional_columns_json: Sequence[str] | None = None,
    status: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    updated = update_fitness_file_contract(
        connection,
        contract_id=contract_id,
        required_columns_json=required_columns_json,
        optional_columns_json=optional_columns_json,
        status=status,
        updated_at=updated_at,
    )
    return {
        "status": "updated",
        "reason": "Fitness file contract was updated in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "fitness_file_contract": updated,
    }


def create_fitness_validation_run_record(
    connection: sqlite3.Connection,
    *,
    run: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_fitness_validation_run(run)
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    created = create_fitness_validation_run(
        connection,
        run_id=validated["id"],
        integration_state_id=validated["integration_state_id"],
        run_type=validated["run_type"],
        dry_run=validated["dry_run"],
        status=validated["status"],
        input_json=validated["input_json"],
        output_json=validated["output_json"],
        error_message=validated["error_message"],
        created_at=validated["created_at"],
        completed_at=validated["completed_at"],
    )
    return {
        "status": "created",
        "reason": "Fitness validation run was stored in the dev/test SQLite database only.",
        "database_write": True,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "fitness_validation_run": created,
    }


def validate_fitness_fixture_headers_with_permission(
    connection: sqlite3.Connection,
    *,
    integration_state: Mapping[str, Any],
    fixture_headers: Mapping[str, Sequence[str] | str],
    run_type: str = "fixture_validation",
    persist_run: bool = False,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    validate_permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_VALIDATE_PERMISSION,
    )
    if not validate_permission["allowed"]:
        return _blocked_result(reason=validate_permission["reason"], permission=validate_permission)

    report = build_fitness_validation_report(
        integration_state=integration_state,
        fixture_headers=fixture_headers,
        run_type=run_type,
        generated_at=generated_at,
    )
    result = {
        "status": report["status"],
        "reason": "Fixture CSV headers were validated from caller-supplied data only.",
        "dry_run": True,
        "database_write": False,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": {"validate": validate_permission},
        "output_json": report,
        "fitness_validation_run": None,
    }
    if not persist_run:
        return result

    write_permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_WRITE_PERMISSION,
    )
    result["permission"] = {
        "validate": validate_permission,
        "write": write_permission,
    }
    if not write_permission["allowed"]:
        result["status"] = "blocked"
        result["reason"] = write_permission["reason"]
        return result

    run_time = report["generated_at"]
    selected_run_id = run_id or stable_fitness_id(
        "fitness-validation-run",
        f"{report['integration_state_id']}|{run_type}|{run_time}|"
        f"{_stable_json_digest({'fixture_files': sorted(fixture_headers.keys())})}",
    )
    run = create_fitness_validation_run(
        connection,
        run_id=selected_run_id,
        integration_state_id=report["integration_state_id"],
        run_type=run_type,
        dry_run=True,
        status=report["status"],
        input_json={"fixture_files": sorted(fixture_headers.keys())},
        output_json=report,
        created_at=run_time,
        completed_at=run_time,
    )
    result["database_write"] = True
    result["fitness_validation_run"] = run
    return result


def preview_fitness_schema_validation(
    connection: sqlite3.Connection,
    *,
    integration_state: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    permission = evaluate_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_VALIDATE_PERMISSION,
    )
    if not permission["allowed"]:
        return _blocked_result(reason=permission["reason"], permission=permission)

    report = build_fitness_schema_preview_report(
        integration_state=integration_state,
        generated_at=generated_at,
    )
    return {
        "status": "completed",
        "reason": "Fitness schema preview used repository contracts only.",
        "dry_run": True,
        "database_write": False,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": permission,
        "output_json": report,
    }


def read_fitness_integration_state(
    connection: sqlite3.Connection,
    *,
    state_id: str,
) -> dict[str, Any] | None:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return get_fitness_integration_state(connection, state_id)


def read_fitness_integration_states(
    connection: sqlite3.Connection,
    *,
    integration_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return list_fitness_integration_states(
        connection,
        integration_type=integration_type,
        status=status,
    )


def read_fitness_integration_state_count(
    connection: sqlite3.Connection,
    *,
    integration_type: str | None = None,
    status: str | None = None,
) -> int:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return count_fitness_integration_states(
        connection,
        integration_type=integration_type,
        status=status,
    )


def read_fitness_validation_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
) -> dict[str, Any] | None:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return get_fitness_validation_run(connection, run_id)


def read_fitness_validation_runs(
    connection: sqlite3.Connection,
    *,
    integration_state_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return list_fitness_validation_runs(
        connection,
        integration_state_id=integration_state_id,
        run_type=run_type,
        status=status,
    )


def read_fitness_validation_run_count(
    connection: sqlite3.Connection,
    *,
    integration_state_id: str | None = None,
    run_type: str | None = None,
    status: str | None = None,
) -> int:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return count_fitness_validation_runs(
        connection,
        integration_state_id=integration_state_id,
        run_type=run_type,
        status=status,
    )


def read_fitness_file_contract(
    connection: sqlite3.Connection,
    *,
    contract_id: str,
) -> dict[str, Any] | None:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return get_fitness_file_contract(connection, contract_id)


def read_fitness_file_contracts(
    connection: sqlite3.Connection,
    *,
    file_role: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return list_fitness_file_contracts(connection, file_role=file_role, status=status)


def read_fitness_file_contract_count(
    connection: sqlite3.Connection,
    *,
    file_role: str | None = None,
    status: str | None = None,
) -> int:
    require_fitness_integration_permission(
        connection,
        category=FITNESS_INTEGRATION_READ_PERMISSION,
    )
    return count_fitness_file_contracts(connection, file_role=file_role, status=status)


def require_fitness_integration_permission(
    connection: sqlite3.Connection,
    *,
    category: str,
) -> dict[str, Any]:
    decision = evaluate_fitness_integration_permission(connection, category=category)
    if not decision["allowed"]:
        raise FitnessIntegrationPermissionDenied(decision["reason"])
    return decision


def evaluate_fitness_integration_permission(
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
            reason=f"Missing fitness integration permission setting: {category}",
            setting=None,
        )

    try:
        mode = PermissionMode(setting["mode"])
    except ValueError:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=setting["mode"],
            reason=f"Invalid fitness integration permission mode: {setting['mode']}",
            setting=setting,
        )

    if mode is PermissionMode.DISABLED:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Fitness integration permission is disabled: {category}",
            setting=setting,
        )
    if mode is not PermissionMode.AUTO_WRITE:
        return _permission_decision(
            allowed=False,
            category=category,
            mode=mode.value,
            reason=f"Fitness integration permission is not enabled for dev/test use: {category}",
            setting=setting,
        )

    return _permission_decision(
        allowed=True,
        category=category,
        mode=mode.value,
        reason="Fitness integration permission is explicitly enabled for dev/test use.",
        setting=setting,
    )


def stable_fitness_id(prefix: str, material: str) -> str:
    prefix = _normalize_for_id(_validate_required_text("prefix", prefix))
    material = _validate_required_text("material", material)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _validate_expected_files(value: Any) -> list[str]:
    expected_files = _validate_file_name_list("expected_files_json", value)
    missing = sorted(set(EXPECTED_FITNESS_FILE_NAMES) - set(expected_files))
    if missing:
        raise FitnessValidationError(
            "fitness integration state missing expected files: " + ", ".join(missing)
        )
    return expected_files


def _required_columns_for_role(file_role: str) -> tuple[str, ...]:
    for contract in EXPECTED_FITNESS_CSV_CONTRACTS:
        if contract["file_role"] == file_role:
            return tuple(contract["required_columns_json"])
    raise FitnessValidationError(f"unknown fitness file role: {file_role}")


def _parse_header_input(file_name: str, raw_headers: Sequence[str] | str) -> list[str]:
    if isinstance(raw_headers, str):
        rows = csv.reader(raw_headers.splitlines())
        try:
            headers = next(rows)
        except StopIteration as error:
            raise FitnessValidationError(
                f"{file_name} fixture headers must not be empty"
            ) from error
    elif isinstance(raw_headers, Sequence):
        headers = list(raw_headers)
    else:
        raise FitnessValidationError(f"{file_name} fixture headers must be a sequence or CSV text")
    return _validate_column_list(f"{file_name} fixture headers", headers)


def _validate_validation_output_safety(output_json: Mapping[str, Any]) -> None:
    if output_json.get("no_external_writes") is not True:
        raise FitnessValidationError(
            "fitness validation output_json must include no_external_writes: true"
        )
    if output_json.get("no_live_personalos_access") is not True:
        raise FitnessValidationError(
            "fitness validation output_json must include no_live_personalos_access: true"
        )
    for field_name in ("network_called", "external_mutation", "model_called"):
        if output_json.get(field_name) is True:
            raise FitnessValidationError(
                f"fitness validation output_json must not set {field_name}: true"
            )
    _assert_json_safe("output_json", output_json)


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
        "setting": None if setting is None else dict(setting),
    }


def _blocked_result(
    *,
    reason: str,
    permission: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "dry_run": True,
        "database_write": False,
        "external_mutation": False,
        "no_external_writes": True,
        "no_live_personalos_access": True,
        "permission": dict(permission),
        "output_json": None,
    }


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FitnessValidationError(f"{field_name} must be a JSON object")
    return value


def _require_keys(field_name: str, value: Mapping[str, Any], required_keys: set[str]) -> None:
    missing = sorted(required_keys - set(value.keys()))
    if missing:
        raise FitnessValidationError(f"{field_name} missing required fields: {', '.join(missing)}")


def _validate_metadata(field_name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FitnessValidationError(f"{field_name} must be a JSON object")
    metadata = dict(value)
    _assert_json_safe(field_name, metadata)
    return metadata


def _assert_json_safe(field_name: str, value: Any) -> None:
    try:
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise FitnessValidationError(f"{field_name} must be JSON-safe") from error


def _validate_required_text(field_name: str, value: Any) -> str:
    value = _validate_text(field_name, value)
    if not value.strip():
        raise FitnessValidationError(f"{field_name} must not be empty")
    return value


def _validate_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise FitnessValidationError(f"{field_name} must be a string")
    return value


def _validate_label(field_name: str, value: Any) -> str:
    label = _validate_required_text(field_name, value)
    if _looks_like_path(label):
        raise FitnessValidationError(f"{field_name} must be a label, not a filesystem path")
    return label


def _validate_file_name(field_name: str, value: Any) -> str:
    file_name = _validate_required_text(field_name, value)
    if _looks_like_path(file_name) or "/" in file_name or "\\" in file_name:
        raise FitnessValidationError(f"{field_name} must be a filename, not a path")
    if not file_name.endswith(".csv"):
        raise FitnessValidationError(f"{field_name} must be a CSV filename")
    return file_name


def _validate_file_name_list(field_name: str, value: Any) -> list[str]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise FitnessValidationError(f"{field_name} must be a list of filenames")
    return [_validate_file_name(field_name, item) for item in value]


def _validate_column_list(field_name: str, value: Any) -> list[str]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise FitnessValidationError(f"{field_name} must be a list of column names")
    columns = [_validate_required_text(field_name, item).strip() for item in value]
    if len(set(columns)) != len(columns):
        raise FitnessValidationError(f"{field_name} must not contain duplicate columns")
    return columns


def _looks_like_path(value: str) -> bool:
    return value.startswith(("/", "~/", "./", "../")) or ":\\" in value


def _validate_iso_datetime(field_name: str, value: Any) -> str:
    value = _validate_required_text(field_name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise FitnessValidationError(f"{field_name} must be an ISO datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FitnessValidationError(f"{field_name} must include a timezone offset")
    return value


def _validate_bool(field_name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise FitnessValidationError(f"{field_name} must be a boolean")
    return value


def _stable_json_digest(value: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        dict(value),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _normalize_for_id(value: str) -> str:
    normalized = "-".join(value.strip().lower().replace("_", "-").split())
    return "".join(character for character in normalized if character.isalnum() or character == "-")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "EXPECTED_FITNESS_CSV_CONTRACTS",
    "EXPECTED_FITNESS_FILE_NAMES",
    "EXERCISE_LIBRARY_FILE",
    "FITNESS_DATA_ROOT_LABEL",
    "FITNESS_FILE_CONTRACT_SCHEMA_VERSION",
    "FITNESS_FILE_CONTRACT_STATUSES",
    "FITNESS_FILE_ROLES",
    "FITNESS_INTEGRATION_READ_PERMISSION",
    "FITNESS_INTEGRATION_STATE_SCHEMA_VERSION",
    "FITNESS_INTEGRATION_STATUSES",
    "FITNESS_INTEGRATION_TYPES",
    "FITNESS_INTEGRATION_VALIDATE_PERMISSION",
    "FITNESS_INTEGRATION_WRITE_PERMISSION",
    "FITNESS_VALIDATION_REPORT_SCHEMA_VERSION",
    "FITNESS_VALIDATION_RUN_SCHEMA_VERSION",
    "FITNESS_VALIDATION_RUN_STATUSES",
    "FITNESS_VALIDATION_RUN_TYPES",
    "FitnessIntegrationPermissionDenied",
    "FitnessValidationError",
    "WEEKLY_RECOVERY_FILE",
    "WORKOUT_EXERCISES_FILE",
    "WORKOUT_SESSIONS_FILE",
    "build_default_fitness_integration_state",
    "build_expected_fitness_file_contract_records",
    "build_fitness_schema_preview_report",
    "build_fitness_validation_report",
    "create_fitness_file_contract_record",
    "create_fitness_integration_state_record",
    "create_fitness_validation_run_record",
    "evaluate_fitness_integration_permission",
    "preview_fitness_schema_validation",
    "read_fitness_file_contract",
    "read_fitness_file_contract_count",
    "read_fitness_file_contracts",
    "read_fitness_integration_state",
    "read_fitness_integration_state_count",
    "read_fitness_integration_states",
    "read_fitness_validation_run",
    "read_fitness_validation_run_count",
    "read_fitness_validation_runs",
    "require_fitness_integration_permission",
    "stable_fitness_id",
    "update_fitness_file_contract_record",
    "update_fitness_integration_state_record",
    "validate_expected_fitness_file_contracts",
    "validate_fitness_file_contract",
    "validate_fitness_fixture_headers_with_permission",
    "validate_fitness_integration_state",
    "validate_fitness_validation_run",
    "validate_fixture_csv_headers",
]

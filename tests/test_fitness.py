import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.fitness import (
    EXPECTED_FITNESS_CSV_CONTRACTS,
    EXPECTED_FITNESS_FILE_NAMES,
    FITNESS_INTEGRATION_READ_PERMISSION,
    FITNESS_INTEGRATION_VALIDATE_PERMISSION,
    FITNESS_INTEGRATION_WRITE_PERMISSION,
    FitnessIntegrationPermissionDenied,
    FitnessValidationError,
    build_default_fitness_integration_state,
    build_expected_fitness_file_contract_records,
    build_fitness_validation_report,
    create_fitness_integration_state_record,
    preview_fitness_schema_validation,
    read_fitness_file_contracts,
    read_fitness_integration_state_count,
    read_fitness_integration_states,
    validate_expected_fitness_file_contracts,
    validate_fitness_file_contract,
    validate_fitness_fixture_headers_with_permission,
    validate_fitness_integration_state,
    validate_fitness_validation_run,
    validate_fixture_csv_headers,
)
from personalos.permissions import PermissionMode
from personalos.state import (
    count_fitness_file_contracts,
    count_fitness_integration_states,
    count_fitness_validation_runs,
    create_fitness_file_contract,
    create_fitness_integration_state,
    create_fitness_validation_run,
    get_fitness_file_contract,
    get_fitness_integration_state,
    get_fitness_validation_run,
    list_fitness_file_contracts,
    list_fitness_integration_states,
    list_fitness_validation_runs,
    update_fitness_file_contract,
    update_fitness_integration_state,
    update_fitness_validation_run,
    upsert_permission_setting,
)

TIMESTAMP = "2026-06-15T10:00:00+00:00"


class FitnessValidationTest(unittest.TestCase):
    def test_fitness_integration_state_validation_accepts_valid_object(self) -> None:
        for label in (
            "personal_os_fitness_csvs",
            "fitness_csv_contract",
            "local_csv_tracker",
        ):
            with self.subTest(label=label):
                state = validate_fitness_integration_state(_valid_state(data_root_label=label))

                self.assertEqual(state["schema_version"], "fitness_integration_state.v1")
                self.assertEqual(state["integration_type"], "local_csv_tracker")
                self.assertEqual(state["data_root_label"], label)
                self.assertEqual(tuple(state["expected_files_json"]), EXPECTED_FITNESS_FILE_NAMES)

    def test_fitness_integration_state_validation_rejects_path_like_data_root_labels(
        self,
    ) -> None:
        invalid_labels = (
            "/Users/example/PersonalOS/Fitness",
            "PersonalOS/60_Fitness/data",
            "60_Fitness/data",
            "fitness\\data",
        )

        for label in invalid_labels:
            with self.subTest(label=label):
                state = _valid_state(data_root_label=label)

                with self.assertRaises(FitnessValidationError):
                    validate_fitness_integration_state(state)

    def test_fitness_integration_state_validation_rejects_missing_expected_files(
        self,
    ) -> None:
        state = _valid_state(expected_files_json=["workout_sessions.csv"])

        with self.assertRaises(FitnessValidationError):
            validate_fitness_integration_state(state)

    def test_file_contract_validation_accepts_expected_contracts(self) -> None:
        contracts = validate_expected_fitness_file_contracts(_valid_contracts())

        self.assertEqual(len(contracts), 4)
        self.assertEqual(
            {contract["file_name"] for contract in contracts},
            set(EXPECTED_FITNESS_FILE_NAMES),
        )

    def test_file_contract_validation_rejects_missing_required_columns(self) -> None:
        contract = _valid_contracts()[0]
        contract["required_columns_json"] = ["session_id"]

        with self.assertRaises(FitnessValidationError):
            validate_fitness_file_contract(contract)

    def test_fixture_csv_header_validation_accepts_valid_fixture_headers(self) -> None:
        result = validate_fixture_csv_headers(_valid_fixture_headers())

        self.assertEqual(result["missing_required_columns"], {})
        self.assertEqual(result["extra_columns"], {})
        self.assertEqual({item["status"] for item in result["checked_files"]}, {"valid"})

    def test_fixture_csv_header_validation_reports_missing_required_columns(self) -> None:
        headers = _valid_fixture_headers()
        headers["workout_sessions.csv"] = ["session_id", "date"]

        result = validate_fixture_csv_headers(headers)

        self.assertIn("workout_sessions.csv", result["missing_required_columns"])
        self.assertIn("session_name", result["missing_required_columns"]["workout_sessions.csv"])

    def test_fixture_csv_header_validation_tolerates_extra_columns_with_warning(self) -> None:
        headers = _valid_fixture_headers()
        headers["exercise_library.csv"] = headers["exercise_library.csv"] + ["trainer_note"]

        result = validate_fixture_csv_headers(headers)

        self.assertEqual(result["missing_required_columns"], {})
        self.assertEqual(result["extra_columns"], {"exercise_library.csv": ["trainer_note"]})
        self.assertTrue(result["warnings"])

    def test_fixture_csv_header_validation_accepts_csv_text_header_rows(self) -> None:
        headers = _valid_fixture_headers()
        headers["weekly_recovery.csv"] = ",".join(headers["weekly_recovery.csv"]) + "\n"

        result = validate_fixture_csv_headers(headers)

        self.assertEqual(result["missing_required_columns"], {})

    def test_validation_report_includes_required_safety_flags(self) -> None:
        report = build_fitness_validation_report(
            integration_state=_valid_state(),
            fixture_headers=_valid_fixture_headers(),
            generated_at=TIMESTAMP,
        )

        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["no_external_writes"])
        self.assertTrue(report["no_live_personalos_access"])

    def test_validation_run_validation_requires_safety_flags(self) -> None:
        report = build_fitness_validation_report(
            integration_state=_valid_state(),
            fixture_headers=_valid_fixture_headers(),
            generated_at=TIMESTAMP,
        )
        run = _valid_run(output_json=report)

        validated = validate_fitness_validation_run(run)
        self.assertTrue(validated["output_json"]["no_external_writes"])

        run["output_json"] = {"no_external_writes": True}
        with self.assertRaises(FitnessValidationError):
            validate_fitness_validation_run(run)


class FitnessPermissionAndStateTest(unittest.TestCase):
    def test_permission_defaults_fail_closed_for_read_write_and_validate(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(FitnessIntegrationPermissionDenied):
                read_fitness_integration_states(connection)

            write_result = create_fitness_integration_state_record(
                connection,
                state=_valid_state(),
            )
            validate_result = validate_fitness_fixture_headers_with_permission(
                connection,
                integration_state=_valid_state(),
                fixture_headers=_valid_fixture_headers(),
            )

            self.assertEqual(write_result["status"], "blocked")
            self.assertEqual(validate_result["status"], "blocked")
            self.assertEqual(count_fitness_integration_states(connection), 0)

    def test_permission_gated_read_write_and_validate_helpers(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, FITNESS_INTEGRATION_WRITE_PERMISSION)
            _set_permission(connection, FITNESS_INTEGRATION_READ_PERMISSION)
            _set_permission(connection, FITNESS_INTEGRATION_VALIDATE_PERMISSION)

            write_result = create_fitness_integration_state_record(
                connection,
                state=_valid_state(),
            )
            validate_result = validate_fitness_fixture_headers_with_permission(
                connection,
                integration_state=write_result["fitness_integration_state"],
                fixture_headers=_valid_fixture_headers(),
                generated_at=TIMESTAMP,
            )

            self.assertEqual(write_result["status"], "created")
            self.assertEqual(validate_result["status"], "completed")
            self.assertEqual(read_fitness_integration_state_count(connection), 1)
            self.assertEqual(read_fitness_integration_states(connection)[0]["id"], "fitness-state")

    def test_schema_validation_preview_requires_validate_permission(self) -> None:
        with _migrated_test_connection() as connection:
            blocked = preview_fitness_schema_validation(
                connection,
                integration_state=_valid_state(),
                generated_at=TIMESTAMP,
            )
            _set_permission(connection, FITNESS_INTEGRATION_VALIDATE_PERMISSION)
            allowed = preview_fitness_schema_validation(
                connection,
                integration_state=_valid_state(),
                generated_at=TIMESTAMP,
            )

            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(allowed["status"], "completed")
            self.assertTrue(allowed["output_json"]["no_live_personalos_access"])

    def test_state_helpers_create_list_count_read_and_update_behavior(self) -> None:
        report = build_fitness_validation_report(
            integration_state=_valid_state(),
            fixture_headers=_valid_fixture_headers(),
            generated_at=TIMESTAMP,
        )

        with _migrated_test_connection() as connection:
            created_state = create_fitness_integration_state(
                connection,
                state_id="fitness-state",
                integration_name="Local CSV fitness tracker",
                integration_type="local_csv_tracker",
                status="draft",
                data_root_label="personal_os_fitness_csvs",
                expected_files_json=list(EXPECTED_FITNESS_FILE_NAMES),
                created_at=TIMESTAMP,
                updated_at=TIMESTAMP,
            )
            created_contract = create_fitness_file_contract(
                connection,
                contract_id="fitness-contract",
                file_name="workout_sessions.csv",
                file_role="workout_sessions",
                required_columns_json=_required_columns("workout_sessions.csv"),
                optional_columns_json=[],
                status="draft",
                created_at=TIMESTAMP,
                updated_at=TIMESTAMP,
            )
            created_run = create_fitness_validation_run(
                connection,
                run_id="fitness-run",
                integration_state_id="fitness-state",
                run_type="fixture_validation",
                dry_run=True,
                status="completed",
                input_json={"fixture_files": list(EXPECTED_FITNESS_FILE_NAMES)},
                output_json=report,
                created_at=TIMESTAMP,
                completed_at=TIMESTAMP,
            )

            updated_state = update_fitness_integration_state(
                connection,
                state_id="fitness-state",
                status="validated",
                last_validation_at=TIMESTAMP,
                last_summary_json=report,
                updated_at=TIMESTAMP,
            )
            updated_contract = update_fitness_file_contract(
                connection,
                contract_id="fitness-contract",
                status="active",
                updated_at=TIMESTAMP,
            )
            updated_run = update_fitness_validation_run(
                connection,
                run_id="fitness-run",
                status="completed",
                output_json=report,
                completed_at=TIMESTAMP,
            )

            self.assertEqual(
                get_fitness_integration_state(connection, "fitness-state"),
                updated_state,
            )
            self.assertEqual(
                get_fitness_file_contract(connection, "fitness-contract"),
                updated_contract,
            )
            self.assertEqual(get_fitness_validation_run(connection, "fitness-run"), updated_run)
            self.assertEqual(list_fitness_integration_states(connection), [updated_state])
            self.assertEqual(list_fitness_file_contracts(connection), [updated_contract])
            self.assertEqual(list_fitness_validation_runs(connection), [updated_run])
            self.assertEqual(count_fitness_integration_states(connection), 1)
            self.assertEqual(count_fitness_file_contracts(connection), 1)
            self.assertEqual(count_fitness_validation_runs(connection), 1)

        self.assertEqual(created_state["status"], "draft")
        self.assertEqual(created_contract["status"], "draft")
        self.assertEqual(created_run["status"], "completed")

    def test_read_helpers_cover_file_contracts(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, FITNESS_INTEGRATION_READ_PERMISSION)
            for contract in _valid_contracts():
                create_fitness_file_contract(
                    connection,
                    contract_id=contract["id"],
                    file_name=contract["file_name"],
                    file_role=contract["file_role"],
                    required_columns_json=contract["required_columns_json"],
                    optional_columns_json=contract["optional_columns_json"],
                    status=contract["status"],
                    created_at=contract["created_at"],
                    updated_at=contract["updated_at"],
                )

            contracts = read_fitness_file_contracts(connection, status="active")

        self.assertEqual(len(contracts), 4)


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        try:
            yield connection
        finally:
            connection.close()


def _valid_state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = build_default_fitness_integration_state(
        state_id="fitness-state",
        created_at=TIMESTAMP,
    )
    state.update(overrides)
    return state


def _valid_contracts() -> list[dict[str, object]]:
    return [
        dict(contract)
        for contract in build_expected_fitness_file_contract_records(created_at=TIMESTAMP)
    ]


def _valid_fixture_headers() -> dict[str, list[str]]:
    return {
        contract["file_name"]: list(contract["required_columns_json"])
        for contract in EXPECTED_FITNESS_CSV_CONTRACTS
    }


def _valid_run(**overrides: object) -> dict[str, object]:
    run: dict[str, object] = {
        "schema_version": "fitness_validation_run.v1",
        "id": "fitness-run",
        "integration_state_id": "fitness-state",
        "run_type": "fixture_validation",
        "dry_run": True,
        "status": "completed",
        "input_json": {"fixture_files": list(EXPECTED_FITNESS_FILE_NAMES)},
        "output_json": build_fitness_validation_report(
            integration_state=_valid_state(),
            fixture_headers=_valid_fixture_headers(),
            generated_at=TIMESTAMP,
        ),
        "error_message": None,
        "created_at": TIMESTAMP,
        "completed_at": TIMESTAMP,
    }
    run.update(overrides)
    return run


def _required_columns(file_name: str) -> list[str]:
    for contract in EXPECTED_FITNESS_CSV_CONTRACTS:
        if contract["file_name"] == file_name:
            return list(contract["required_columns_json"])
    raise AssertionError(f"unknown expected fitness file: {file_name}")


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "8", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc=TIMESTAMP,
    )

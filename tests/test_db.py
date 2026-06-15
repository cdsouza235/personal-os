import sqlite3
import tempfile
import unittest
from pathlib import Path

from personalos.config import (
    DEFAULT_TIMEZONE,
    Environment,
    PersonalOSConfig,
    ProductionConfigUnavailable,
    RUNTIME_DIR,
    load_config,
)
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import (
    MIGRATION_METADATA_TABLE,
    MigrationChecksumMismatch,
    apply_migrations,
    discover_migrations,
)


class SQLiteFoundationTest(unittest.TestCase):
    expected_phase_2_tables = {
        "routines": {
            "routine_id",
            "name",
            "status",
            "enabled",
            "settings_json",
            "notes",
            "created_at_utc",
            "updated_at_utc",
        },
        "routine_completions": {
            "completion_id",
            "routine_id",
            "completed_for_date",
            "completed_at_utc",
            "source",
            "metadata_json",
            "created_at_utc",
        },
        "priorities": {
            "priority_id",
            "title",
            "status",
            "metadata_json",
            "notes",
            "created_at_utc",
            "updated_at_utc",
        },
        "projects": {
            "project_id",
            "title",
            "status",
            "metadata_json",
            "notes",
            "created_at_utc",
            "updated_at_utc",
        },
        "followups": {
            "followup_id",
            "title",
            "status",
            "source",
            "metadata_json",
            "notes",
            "created_at_utc",
            "updated_at_utc",
        },
        "permission_settings": {
            "category",
            "mode",
            "metadata_json",
            "updated_at_utc",
            "updated_by",
        },
    }
    expected_phase_5_tables = {
        "todoist_tasks": {
            "todoist_task_id",
            "task_title",
            "description",
            "source_type",
            "source_id",
            "project",
            "labels_json",
            "due_date_or_due_string",
            "priority",
            "risk_level",
            "approval_mode",
            "dedupe_key",
            "status",
            "external_task_id",
            "created_at_utc",
            "updated_at_utc",
        },
        "calendar_blocks": {
            "calendar_block_id",
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
            "external_event_id",
            "created_at_utc",
            "updated_at_utc",
        },
    }
    expected_phase_6_tables = {
        "composer_packets": {
            "id",
            "packet_type",
            "briefing_window",
            "source_date",
            "timezone",
            "packet_json",
            "status",
            "created_at",
            "updated_at",
        },
        "composer_outputs": {
            "id",
            "packet_id",
            "output_json",
            "readable_text",
            "validation_status",
            "route_report_json",
            "status",
            "created_at",
            "updated_at",
        },
        "model_runs": {
            "id",
            "packet_id",
            "output_id",
            "model_role",
            "model_name",
            "adapter_name",
            "dry_run",
            "status",
            "input_token_count",
            "output_token_count",
            "error_message",
            "created_at",
            "completed_at",
        },
    }
    expected_phase_7_tables = {
        "report_jobs": {
            "id",
            "job_type",
            "name",
            "description",
            "cadence",
            "config_json",
            "status",
            "last_run_at",
            "next_due_at",
            "created_at",
            "updated_at",
        },
        "report_runs": {
            "id",
            "job_id",
            "run_type",
            "dry_run",
            "status",
            "input_json",
            "output_json",
            "error_message",
            "created_at",
            "completed_at",
        },
        "chart_pack_reviews": {
            "id",
            "review_date",
            "week_start",
            "week_end",
            "source_type",
            "source_id",
            "title",
            "thesis_context",
            "chart_pack_json",
            "tradingview_alerts_json",
            "synthesis_markdown",
            "structured_summary_json",
            "status",
            "created_at",
            "updated_at",
        },
    }
    expected_phase_8_tables = {
        "fitness_integration_state": {
            "id",
            "integration_name",
            "integration_type",
            "status",
            "data_root_label",
            "expected_files_json",
            "last_validation_at",
            "last_summary_json",
            "created_at",
            "updated_at",
        },
        "fitness_validation_runs": {
            "id",
            "integration_state_id",
            "run_type",
            "dry_run",
            "status",
            "input_json",
            "output_json",
            "error_message",
            "created_at",
            "completed_at",
        },
        "fitness_file_contracts": {
            "id",
            "file_name",
            "file_role",
            "required_columns_json",
            "optional_columns_json",
            "status",
            "created_at",
            "updated_at",
        },
    }

    def test_dev_and_test_connections_open_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"

            for environment in (Environment.DEVELOPMENT, Environment.TEST):
                with self.subTest(environment=environment):
                    config = _config_for(runtime_dir, environment)

                    with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                        result = connection.execute("SELECT 1").fetchone()[0]
                        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]

                    self.assertEqual(result, 1)
                    self.assertEqual(foreign_keys, 1)

    def test_default_config_loading_does_not_create_repo_runtime_artifacts(self) -> None:
        runtime_dir_existed_before = RUNTIME_DIR.exists()

        config = load_config(Environment.DEVELOPMENT)

        self.assertFalse(config.database_path.exists())
        if not runtime_dir_existed_before:
            self.assertFalse(RUNTIME_DIR.exists())

    def test_parent_directories_are_created_only_for_dev_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            dev_config = _config_for(runtime_dir, Environment.DEVELOPMENT)
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            self.assertFalse(dev_config.database_path.parent.exists())
            with connect_sqlite(dev_config, runtime_dir=runtime_dir) as connection:
                connection.execute("SELECT 1")
            self.assertTrue(dev_config.database_path.parent.exists())

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)
            self.assertFalse(production_config.database_path.parent.exists())

    def test_database_paths_outside_runtime_area_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "runtime"
            outside_config = PersonalOSConfig(
                environment=Environment.TEST,
                timezone=DEFAULT_TIMEZONE,
                database_path=temp_path / "outside.sqlite3",
            )

            with self.assertRaises(ValueError):
                connect_sqlite(outside_config, runtime_dir=runtime_dir)

            self.assertFalse(outside_config.database_path.exists())

    def test_production_database_access_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            production_config = PersonalOSConfig(
                environment=Environment.PRODUCTION,
                timezone=DEFAULT_TIMEZONE,
                database_path=runtime_dir / "production" / "blocked.sqlite3",
            )

            with self.assertRaises(ProductionConfigUnavailable):
                connect_sqlite(production_config, runtime_dir=runtime_dir)

    def test_migration_application_is_idempotent_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection)
                second_applied = apply_migrations(connection)

                rows = connection.execute(
                    f"SELECT version, name, checksum FROM {MIGRATION_METADATA_TABLE}"
                ).fetchall()

            self.assertEqual(
                [migration.version for migration in first_applied],
                ["0001", "0002", "0003", "0004", "0005", "0006", "0007"],
            )
            self.assertEqual(second_applied, [])
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[0]["version"], "0001")
            self.assertEqual(rows[0]["name"], "bootstrap")
            self.assertTrue(rows[0]["checksum"])

    def test_foreign_key_constraints_reject_orphan_records(self) -> None:
        orphan_inserts = (
            (
                "routine_completions",
                """
                INSERT INTO routine_completions (
                    completion_id,
                    routine_id,
                    completed_for_date,
                    completed_at_utc,
                    source,
                    metadata_json,
                    created_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "orphan-completion",
                    "missing-routine",
                    "2026-06-15",
                    "2026-06-15T10:00:00+00:00",
                    "test",
                    "{}",
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
            (
                "composer_outputs",
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
                    "orphan-output",
                    "missing-packet",
                    "{}",
                    "Readable output.",
                    "validated",
                    "{}",
                    "routed",
                    "2026-06-15T10:00:00+00:00",
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
            (
                "report_runs",
                """
                INSERT INTO report_runs (
                    id,
                    job_id,
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
                    "orphan-report-run",
                    "missing-job",
                    "dry_run",
                    1,
                    "completed",
                    "{}",
                    '{"no_external_writes":true}',
                    None,
                    "2026-06-15T10:00:00+00:00",
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
            (
                "fitness_validation_runs",
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
                    "orphan-fitness-run",
                    "missing-integration-state",
                    "fixture_validation",
                    1,
                    "completed",
                    "{}",
                    '{"no_external_writes":true,"no_live_personalos_access":true}',
                    None,
                    "2026-06-15T10:00:00+00:00",
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for table_name, sql, values in orphan_inserts:
                    with self.subTest(table_name=table_name):
                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(sql, values)

    def test_phase_2_state_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_2_tables
                }

        self.assertTrue(self.expected_phase_2_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_2_tables)

    def test_phase_5_todoist_calendar_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_5_tables
                }

        self.assertTrue(self.expected_phase_5_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_5_tables)

    def test_phase_6_composer_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_6_tables
                }

        self.assertTrue(self.expected_phase_6_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_6_tables)

    def test_phase_6_composer_packet_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("packet_type", "invalid_type"),
            ("briefing_window", "overnight"),
            ("status", "live_sent"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"packet-check-{index}",
                            "packet_type": "daily_brief",
                            "briefing_window": "morning",
                            "source_date": "2026-06-15",
                            "timezone": DEFAULT_TIMEZONE,
                            "packet_json": "{}",
                            "status": "validated",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["packet_type"],
                                    values["briefing_window"],
                                    values["source_date"],
                                    values["timezone"],
                                    values["packet_json"],
                                    values["status"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_6_composer_output_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("validation_status", "unchecked"),
            ("status", "sent"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"output-check-{index}",
                            "packet_id": "packet-check",
                            "output_json": "{}",
                            "readable_text": "Readable output.",
                            "validation_status": "validated",
                            "route_report_json": "{}",
                            "status": "routed",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["packet_id"],
                                    values["output_json"],
                                    values["readable_text"],
                                    values["validation_status"],
                                    values["route_report_json"],
                                    values["status"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_6_model_run_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("model_role", "operator_model"),
            ("adapter_name", "live_model_adapter"),
            ("status", "sent"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"model-run-check-{index}",
                            "packet_id": "packet-check",
                            "output_id": None,
                            "model_role": "composer_model",
                            "model_name": "fake-composer-v1",
                            "adapter_name": "fake_composer_adapter",
                            "dry_run": 1,
                            "status": "completed",
                            "input_token_count": 1,
                            "output_token_count": 1,
                            "error_message": None,
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "completed_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["packet_id"],
                                    values["output_id"],
                                    values["model_role"],
                                    values["model_name"],
                                    values["adapter_name"],
                                    values["dry_run"],
                                    values["status"],
                                    values["input_token_count"],
                                    values["output_token_count"],
                                    values["error_message"],
                                    values["created_at"],
                                    values["completed_at"],
                                ),
                            )

    def test_phase_7_report_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_7_tables
                }

        self.assertTrue(self.expected_phase_7_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_7_tables)

    def test_phase_7_report_job_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("job_type", "live_market_data"),
            ("cadence", "hourly"),
            ("status", "running_live"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"report-job-check-{index}",
                            "job_type": "weekly_chart_pack_index",
                            "name": "Weekly chart pack",
                            "description": "Manual chart pack index.",
                            "cadence": "weekly",
                            "config_json": "{}",
                            "status": "draft",
                            "last_run_at": None,
                            "next_due_at": "2026-06-22T10:00:00+00:00",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(
                                """
                                INSERT INTO report_jobs (
                                    id,
                                    job_type,
                                    name,
                                    description,
                                    cadence,
                                    config_json,
                                    status,
                                    last_run_at,
                                    next_due_at,
                                    created_at,
                                    updated_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    values["id"],
                                    values["job_type"],
                                    values["name"],
                                    values["description"],
                                    values["cadence"],
                                    values["config_json"],
                                    values["status"],
                                    values["last_run_at"],
                                    values["next_due_at"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_7_report_run_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("run_type", "live"),
            ("status", "sent"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"report-run-check-{index}",
                            "job_id": "job-check",
                            "run_type": "dry_run",
                            "dry_run": 1,
                            "status": "completed",
                            "input_json": "{}",
                            "output_json": '{"no_external_writes":true}',
                            "error_message": None,
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "completed_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(
                                """
                                INSERT INTO report_runs (
                                    id,
                                    job_id,
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
                                    values["id"],
                                    values["job_id"],
                                    values["run_type"],
                                    values["dry_run"],
                                    values["status"],
                                    values["input_json"],
                                    values["output_json"],
                                    values["error_message"],
                                    values["created_at"],
                                    values["completed_at"],
                                ),
                            )

    def test_phase_7_chart_pack_review_check_constraints_reject_invalid_values(self) -> None:
        invalid_cases = (
            ("source_type", "tradingview_api"),
            ("status", "executed"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"chart-pack-check-{index}",
                            "review_date": "2026-06-15",
                            "week_start": "2026-06-08",
                            "week_end": "2026-06-14",
                            "source_type": "fake_fixture",
                            "source_id": "fixture",
                            "title": "Weekly Chart Pack",
                            "thesis_context": "Manual review only.",
                            "chart_pack_json": "{}",
                            "tradingview_alerts_json": "{}",
                            "synthesis_markdown": "Manual synthesis.",
                            "structured_summary_json": "{}",
                            "status": "draft",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(
                                """
                                INSERT INTO chart_pack_reviews (
                                    id,
                                    review_date,
                                    week_start,
                                    week_end,
                                    source_type,
                                    source_id,
                                    title,
                                    thesis_context,
                                    chart_pack_json,
                                    tradingview_alerts_json,
                                    synthesis_markdown,
                                    structured_summary_json,
                                    status,
                                    created_at,
                                    updated_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    values["id"],
                                    values["review_date"],
                                    values["week_start"],
                                    values["week_end"],
                                    values["source_type"],
                                    values["source_id"],
                                    values["title"],
                                    values["thesis_context"],
                                    values["chart_pack_json"],
                                    values["tradingview_alerts_json"],
                                    values["synthesis_markdown"],
                                    values["structured_summary_json"],
                                    values["status"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_8_fitness_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_8_tables
                }

        self.assertTrue(self.expected_phase_8_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_8_tables)

    def test_phase_8_fitness_integration_state_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("integration_type", "notion_database"),
            ("status", "live_importing"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"fitness-state-check-{index}",
                            "integration_name": "Local CSV fitness tracker",
                            "integration_type": "local_csv_tracker",
                            "status": "draft",
                            "data_root_label": "personal_os_fitness_csvs",
                            "expected_files_json": '["workout_sessions.csv"]',
                            "last_validation_at": None,
                            "last_summary_json": None,
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["integration_name"],
                                    values["integration_type"],
                                    values["status"],
                                    values["data_root_label"],
                                    values["expected_files_json"],
                                    values["last_validation_at"],
                                    values["last_summary_json"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_8_fitness_validation_run_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("run_type", "live_import"),
            ("status", "sent"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"fitness-run-check-{index}",
                            "integration_state_id": "fitness-state-check",
                            "run_type": "fixture_validation",
                            "dry_run": 1,
                            "status": "completed",
                            "input_json": "{}",
                            "output_json": (
                                '{"no_external_writes":true,'
                                '"no_live_personalos_access":true}'
                            ),
                            "error_message": None,
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "completed_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["integration_state_id"],
                                    values["run_type"],
                                    values["dry_run"],
                                    values["status"],
                                    values["input_json"],
                                    values["output_json"],
                                    values["error_message"],
                                    values["created_at"],
                                    values["completed_at"],
                                ),
                            )

    def test_phase_8_fitness_file_contract_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("file_role", "apple_health_export"),
            ("status", "live"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"fitness-contract-check-{index}",
                            "file_name": "workout_sessions.csv",
                            "file_role": "workout_sessions",
                            "required_columns_json": '["session_id"]',
                            "optional_columns_json": "[]",
                            "status": "draft",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["file_name"],
                                    values["file_role"],
                                    values["required_columns_json"],
                                    values["optional_columns_json"],
                                    values["status"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_migration_checksum_drift_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "runtime"
            migrations_dir = temp_path / "migrations"
            migrations_dir.mkdir()
            migration_path = migrations_dir / "0001_bootstrap.sql"
            migration_path.write_text("SELECT 1;\n", encoding="utf-8")
            config = _config_for(runtime_dir, Environment.TEST)

            with connect_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection, migrations_dir=migrations_dir)
                second_applied = apply_migrations(connection, migrations_dir=migrations_dir)
                recorded_checksum = connection.execute(
                    f"SELECT checksum FROM {MIGRATION_METADATA_TABLE} WHERE version = ?",
                    ("0001",),
                ).fetchone()["checksum"]

                migration_path.write_text("SELECT 2;\n", encoding="utf-8")

                with self.assertRaises(MigrationChecksumMismatch) as context:
                    apply_migrations(connection, migrations_dir=migrations_dir)

            self.assertEqual([migration.version for migration in first_applied], ["0001"])
            self.assertEqual(second_applied, [])
            self.assertEqual(context.exception.version, "0001")
            self.assertEqual(context.exception.recorded_checksum, recorded_checksum)
            self.assertNotEqual(context.exception.current_checksum, recorded_checksum)

    def test_migration_discovery_finds_foundation_migrations(self) -> None:
        migrations = discover_migrations()

        self.assertEqual(
            [migration.version for migration in migrations],
            ["0001", "0002", "0003", "0004", "0005", "0006", "0007"],
        )
        self.assertEqual(
            [migration.name for migration in migrations],
            [
                "bootstrap",
                "system_events",
                "core_state_tables",
                "todoist_calendar_module_tables",
                "composer_model_tables",
                "report_jobs_chart_pack_tables",
                "fitness_integration_tables",
            ],
        )


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    return {row["name"] for row in rows}


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}

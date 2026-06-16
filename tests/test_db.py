import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
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
    expected_phase_9b_tables = {
        "runtime_bootstrap_runs": {
            "id",
            "profile_name",
            "runtime_mode",
            "db_path_label",
            "dry_run",
            "status",
            "input_json",
            "output_json",
            "error_message",
            "created_at",
            "completed_at",
        },
        "briefing_windows": {
            "id",
            "name",
            "scheduled_time",
            "timezone",
            "delivery_mode",
            "status",
            "created_at",
            "updated_at",
        },
    }
    expected_phase_10b_tables = {
        "daily_plans": {
            "id",
            "source_date",
            "timezone",
            "plan_json",
            "status",
            "created_at",
            "updated_at",
        },
        "briefing_outputs": {
            "id",
            "daily_plan_id",
            "briefing_window_id",
            "briefing_window_name",
            "source_date",
            "timezone",
            "composer_packet_id",
            "composer_output_id",
            "readable_text",
            "output_json",
            "manual_export_markdown",
            "completion_report_json",
            "delivery_mode",
            "status",
            "created_at",
            "updated_at",
        },
    }
    expected_phase_11a_tables = {
        "synthesis_import_previews": {
            "id",
            "source_type",
            "input_format",
            "input_hash",
            "source_timestamp",
            "source_reference",
            "raw_excerpt",
            "parsed_json",
            "preview_report_json",
            "status",
            "created_at",
            "updated_at",
        },
    }
    expected_phase_12b_tables = {
        "external_write_intents": {
            "intent_id",
            "source_type",
            "source_id",
            "target_system",
            "operation_type",
            "risk_level",
            "approval_mode",
            "status",
            "idempotency_key",
            "dedupe_key",
            "payload_json",
            "validation_report_json",
            "no_external_writes",
            "no_send_mode",
            "live_write",
            "created_at",
            "updated_at",
        },
        "external_write_attempts": {
            "attempt_id",
            "intent_id",
            "attempt_number",
            "mode",
            "adapter_name",
            "status",
            "request_fingerprint",
            "response_summary_json",
            "error_message",
            "no_external_writes",
            "no_send_mode",
            "live_write",
            "created_at",
        },
        "idempotency_records": {
            "idempotency_key",
            "target_system",
            "operation_type",
            "source_type",
            "source_id",
            "dedupe_key",
            "payload_fingerprint",
            "first_seen_at",
            "last_seen_at",
            "status",
            "linked_intent_id",
            "linked_attempt_id",
        },
    }

    def test_dev_and_test_connections_open_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"

            for environment in (Environment.DEVELOPMENT, Environment.TEST):
                with self.subTest(environment=environment):
                    config = _config_for(runtime_dir, environment)

                    with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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
            with _connected_sqlite(dev_config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                first_applied = apply_migrations(connection)
                second_applied = apply_migrations(connection)

                rows = connection.execute(
                    f"SELECT version, name, checksum FROM {MIGRATION_METADATA_TABLE}"
                ).fetchall()

            self.assertEqual(
                [migration.version for migration in first_applied],
                [
                    "0001",
                    "0002",
                    "0003",
                    "0004",
                    "0005",
                    "0006",
                    "0007",
                    "0008",
                    "0009",
                    "00010",
                    "00011",
                ],
            )
            self.assertEqual(second_applied, [])
            self.assertEqual(len(rows), 11)
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
            (
                "external_write_attempts",
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
                    "orphan-side-effect-attempt",
                    "missing-intent",
                    1,
                    "dry_run",
                    "fake_adapter",
                    "succeeded",
                    "sha256:request",
                    '{"no_external_writes":true,"no_send_mode":true}',
                    None,
                    1,
                    1,
                    0,
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
            (
                "briefing_outputs",
                """
                INSERT INTO briefing_outputs (
                    id,
                    daily_plan_id,
                    briefing_window_id,
                    briefing_window_name,
                    source_date,
                    timezone,
                    composer_packet_id,
                    composer_output_id,
                    readable_text,
                    output_json,
                    manual_export_markdown,
                    completion_report_json,
                    delivery_mode,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "orphan-briefing-output",
                    "missing-daily-plan",
                    None,
                    "morning",
                    "2026-06-15",
                    DEFAULT_TIMEZONE,
                    None,
                    None,
                    "Readable output.",
                    "{}",
                    "# Manual export\n\n- No-send preview\n- No external writes performed",
                    '{"no_external_writes":true}',
                    "no_send",
                    "generated",
                    "2026-06-15T10:00:00+00:00",
                    "2026-06-15T10:00:00+00:00",
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for table_name, sql, values in orphan_inserts:
                    with self.subTest(table_name=table_name):
                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(sql, values)

    def test_phase_2_state_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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

    def test_phase_9b_runtime_bootstrap_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_9b_tables
                }

        self.assertTrue(self.expected_phase_9b_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_9b_tables)

    def test_phase_10b_briefing_loop_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_10b_tables
                }

        self.assertTrue(self.expected_phase_10b_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_10b_tables)

    def test_phase_11a_synthesis_import_preview_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_11a_tables
                }

        self.assertTrue(self.expected_phase_11a_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_11a_tables)

    def test_phase_12b_side_effect_ledger_tables_and_columns_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                table_names = _table_names(connection)
                table_columns = {
                    table_name: _column_names(connection, table_name)
                    for table_name in self.expected_phase_12b_tables
                }

        self.assertTrue(self.expected_phase_12b_tables.keys() <= table_names)
        self.assertEqual(table_columns, self.expected_phase_12b_tables)

    def test_phase_12b_side_effect_ledger_check_constraints_reject_live_values(
        self,
    ) -> None:
        invalid_intent_cases = (
            ("target_system", "todoist_live_api"),
            ("operation_type", "execute"),
            ("risk_level", "critical"),
            ("approval_mode", "live_auto"),
            ("status", "completed_live"),
            ("no_external_writes", 0),
            ("no_send_mode", 0),
            ("live_write", 1),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_intent_cases):
                    with self.subTest(column_name=column_name):
                        values = _side_effect_intent_values(f"intent-check-{index}")
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["intent_id"],
                                    values["source_type"],
                                    values["source_id"],
                                    values["target_system"],
                                    values["operation_type"],
                                    values["risk_level"],
                                    values["approval_mode"],
                                    values["status"],
                                    values["idempotency_key"],
                                    values["dedupe_key"],
                                    values["payload_json"],
                                    values["validation_report_json"],
                                    values["no_external_writes"],
                                    values["no_send_mode"],
                                    values["live_write"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_12b_attempt_constraints_reject_live_values(self) -> None:
        invalid_attempt_cases = (
            ("mode", "live"),
            ("status", "completed_live"),
            ("no_external_writes", 0),
            ("no_send_mode", 0),
            ("live_write", 1),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                values = _side_effect_intent_values("intent-for-attempt-check")
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
                        values["intent_id"],
                        values["source_type"],
                        values["source_id"],
                        values["target_system"],
                        values["operation_type"],
                        values["risk_level"],
                        values["approval_mode"],
                        values["status"],
                        values["idempotency_key"],
                        values["dedupe_key"],
                        values["payload_json"],
                        values["validation_report_json"],
                        values["no_external_writes"],
                        values["no_send_mode"],
                        values["live_write"],
                        values["created_at"],
                        values["updated_at"],
                    ),
                )

                for index, (column_name, invalid_value) in enumerate(invalid_attempt_cases):
                    with self.subTest(column_name=column_name):
                        attempt = _side_effect_attempt_values(
                            f"attempt-check-{index}",
                            intent_id=values["intent_id"],
                        )
                        attempt[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    attempt["attempt_id"],
                                    attempt["intent_id"],
                                    attempt["attempt_number"],
                                    attempt["mode"],
                                    attempt["adapter_name"],
                                    attempt["status"],
                                    attempt["request_fingerprint"],
                                    attempt["response_summary_json"],
                                    attempt["error_message"],
                                    attempt["no_external_writes"],
                                    attempt["no_send_mode"],
                                    attempt["live_write"],
                                    attempt["created_at"],
                                ),
                            )

                attempt = _side_effect_attempt_values(
                    "attempt-check-live-blocked-succeeded",
                    intent_id=values["intent_id"],
                )
                attempt["mode"] = "live_blocked"
                attempt["status"] = "succeeded"
                with self.assertRaises(sqlite3.IntegrityError):
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
                            attempt["attempt_id"],
                            attempt["intent_id"],
                            attempt["attempt_number"],
                            attempt["mode"],
                            attempt["adapter_name"],
                            attempt["status"],
                            attempt["request_fingerprint"],
                            attempt["response_summary_json"],
                            attempt["error_message"],
                            attempt["no_external_writes"],
                            attempt["no_send_mode"],
                            attempt["live_write"],
                            attempt["created_at"],
                        ),
                    )

    def test_phase_12b_idempotency_records_reject_duplicate_dedupe_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                first = _side_effect_idempotency_values("idem:first")
                duplicate = _side_effect_idempotency_values("idem:second")
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
                        first["idempotency_key"],
                        first["target_system"],
                        first["operation_type"],
                        first["source_type"],
                        first["source_id"],
                        first["dedupe_key"],
                        first["payload_fingerprint"],
                        first["first_seen_at"],
                        first["last_seen_at"],
                        first["status"],
                        first["linked_intent_id"],
                        first["linked_attempt_id"],
                    ),
                )

                with self.assertRaises(sqlite3.IntegrityError):
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
                            duplicate["idempotency_key"],
                            duplicate["target_system"],
                            duplicate["operation_type"],
                            duplicate["source_type"],
                            duplicate["source_id"],
                            duplicate["dedupe_key"],
                            duplicate["payload_fingerprint"],
                            duplicate["first_seen_at"],
                            duplicate["last_seen_at"],
                            duplicate["status"],
                            duplicate["linked_intent_id"],
                            duplicate["linked_attempt_id"],
                        ),
                    )

    def test_phase_11a_synthesis_import_preview_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("source_type", "raw_notes"),
            ("input_format", "prose"),
            ("status", "applied"),
            ("raw_excerpt", "x" * 2001),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"synthesis-preview-check-{index}",
                            "source_type": "chatgpt_synthesis",
                            "input_format": "json",
                            "input_hash": "hash",
                            "source_timestamp": "2026-06-15T10:00:00+00:00",
                            "source_reference": "chatgpt-thread",
                            "raw_excerpt": "excerpt",
                            "parsed_json": "{}",
                            "preview_report_json": "{}",
                            "status": "validated",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
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
                                    values["id"],
                                    values["source_type"],
                                    values["input_format"],
                                    values["input_hash"],
                                    values["source_timestamp"],
                                    values["source_reference"],
                                    values["raw_excerpt"],
                                    values["parsed_json"],
                                    values["preview_report_json"],
                                    values["status"],
                                    values["created_at"],
                                    values["updated_at"],
                                ),
                            )

    def test_phase_9b_runtime_bootstrap_run_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("runtime_mode", "production"),
            ("dry_run", 2),
            ("status", "running_live"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"bootstrap-run-check-{index}",
                            "profile_name": "phase-9b-preview",
                            "runtime_mode": "local_runtime_preview",
                            "db_path_label": "temp-preview",
                            "dry_run": 0,
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
                                INSERT INTO runtime_bootstrap_runs (
                                    id,
                                    profile_name,
                                    runtime_mode,
                                    db_path_label,
                                    dry_run,
                                    status,
                                    input_json,
                                    output_json,
                                    error_message,
                                    created_at,
                                    completed_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    values["id"],
                                    values["profile_name"],
                                    values["runtime_mode"],
                                    values["db_path_label"],
                                    values["dry_run"],
                                    values["status"],
                                    values["input_json"],
                                    values["output_json"],
                                    values["error_message"],
                                    values["created_at"],
                                    values["completed_at"],
                                ),
                            )

    def test_phase_9b_briefing_window_check_constraints_reject_invalid_values(
        self,
    ) -> None:
        invalid_cases = (
            ("name", "overnight"),
            ("delivery_mode", "gmail_send"),
            ("status", "scheduled_live"),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            config = _config_for(runtime_dir, Environment.TEST)

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
                apply_migrations(connection)
                for index, (column_name, invalid_value) in enumerate(invalid_cases):
                    with self.subTest(column_name=column_name):
                        values = {
                            "id": f"briefing-window-check-{index}",
                            "name": "morning",
                            "scheduled_time": "08:00",
                            "timezone": DEFAULT_TIMEZONE,
                            "delivery_mode": "no_send",
                            "status": "draft",
                            "created_at": "2026-06-15T10:00:00+00:00",
                            "updated_at": "2026-06-15T10:00:00+00:00",
                        }
                        values[column_name] = invalid_value

                        with self.assertRaises(sqlite3.IntegrityError):
                            connection.execute(
                                """
                                INSERT INTO briefing_windows (
                                    id,
                                    name,
                                    scheduled_time,
                                    timezone,
                                    delivery_mode,
                                    status,
                                    created_at,
                                    updated_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    values["id"],
                                    values["name"],
                                    values["scheduled_time"],
                                    values["timezone"],
                                    values["delivery_mode"],
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

            with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
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
            [
                "0001",
                "0002",
                "0003",
                "0004",
                "0005",
                "0006",
                "0007",
                "0008",
                "0009",
                "00010",
                "00011",
            ],
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
                "runtime_bootstrap_tables",
                "briefing_loop_tables",
                "synthesis_import_preview_tables",
                "side_effect_idempotency_ledger_tables",
            ],
        )


def _side_effect_intent_values(intent_id: str) -> dict[str, object]:
    timestamp = "2026-06-15T10:00:00+00:00"
    return {
        "intent_id": intent_id,
        "source_type": "fake_fixture",
        "source_id": "phase-12b",
        "target_system": "todoist",
        "operation_type": "create",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "approved_for_dry_run",
        "idempotency_key": f"idem:todoist:create:{intent_id}",
        "dedupe_key": f"todoist:create:{intent_id}",
        "payload_json": '{"title":"Review ledger"}',
        "validation_report_json": '{"no_external_writes":true,"no_send_mode":true}',
        "no_external_writes": 1,
        "no_send_mode": 1,
        "live_write": 0,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _side_effect_attempt_values(attempt_id: str, *, intent_id: str) -> dict[str, object]:
    return {
        "attempt_id": attempt_id,
        "intent_id": intent_id,
        "attempt_number": 1,
        "mode": "dry_run",
        "adapter_name": "phase_12b_fake_adapter",
        "status": "succeeded",
        "request_fingerprint": f"sha256:{attempt_id}",
        "response_summary_json": '{"no_external_writes":true,"no_send_mode":true}',
        "error_message": None,
        "no_external_writes": 1,
        "no_send_mode": 1,
        "live_write": 0,
        "created_at": "2026-06-15T10:00:00+00:00",
    }


def _side_effect_idempotency_values(idempotency_key: str) -> dict[str, object]:
    timestamp = "2026-06-15T10:00:00+00:00"
    return {
        "idempotency_key": idempotency_key,
        "target_system": "todoist",
        "operation_type": "create",
        "source_type": "fake_fixture",
        "source_id": "phase-12b",
        "dedupe_key": "todoist:create:shared",
        "payload_fingerprint": "sha256:payload",
        "first_seen_at": timestamp,
        "last_seen_at": timestamp,
        "status": "approved_for_dry_run",
        "linked_intent_id": None,
        "linked_attempt_id": None,
    }


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(
    config: PersonalOSConfig,
    *,
    runtime_dir: Path,
) -> Iterator[sqlite3.Connection]:
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    try:
        yield connection
    finally:
        connection.close()


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

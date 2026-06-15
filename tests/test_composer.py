import json
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.composer import (
    COMPOSER_MODULE_READ_PERMISSION,
    COMPOSER_MODULE_RUN_PERMISSION,
    COMPOSER_MODULE_WRITE_PERMISSION,
    ComposerModulePermissionDenied,
    ComposerValidationError,
    FakeComposerAdapter,
    build_candidate_routing_report,
    build_composer_packet_from_state,
    build_validated_candidate_routing_report,
    create_composer_output_record,
    create_composer_packet_record,
    read_composer_output_count,
    read_composer_outputs,
    read_composer_packet_count,
    read_composer_packets,
    read_model_run_count,
    read_model_runs,
    route_composer_output_candidates,
    run_fake_composer_model,
    stable_composer_id,
    validate_composer_output,
    validate_composer_packet,
)
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.state import (
    count_composer_outputs,
    count_composer_packets,
    count_model_runs,
    create_calendar_block,
    create_composer_output,
    create_composer_packet,
    create_priority,
    create_routine,
    get_model_run,
    upsert_permission_setting,
)


class ComposerMigrationAndStateTest(unittest.TestCase):
    def test_migration_0005_is_applied(self) -> None:
        with _migrated_test_connection() as connection:
            rows = connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()

        migration_names = {row["version"]: row["name"] for row in rows}
        self.assertEqual(migration_names["0005"], "composer_model_tables")

    def test_composer_packets_schema_exists(self) -> None:
        with _migrated_test_connection() as connection:
            columns = _column_names(connection, "composer_packets")

        self.assertEqual(
            columns,
            {
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
        )

    def test_composer_outputs_schema_exists(self) -> None:
        with _migrated_test_connection() as connection:
            columns = _column_names(connection, "composer_outputs")

        self.assertEqual(
            columns,
            {
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
        )

    def test_model_runs_schema_exists(self) -> None:
        with _migrated_test_connection() as connection:
            columns = _column_names(connection, "model_runs")

        self.assertEqual(
            columns,
            {
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
        )

    def test_state_helpers_create_read_list_and_count_records(self) -> None:
        packet = _valid_packet()
        output = _valid_output(packet_id=packet["packet_id"])
        report = build_candidate_routing_report(output)

        with _migrated_test_connection() as connection:
            packet_row = create_composer_packet(
                connection,
                packet_id=packet["packet_id"],
                packet_type=packet["packet_type"],
                briefing_window=packet["briefing_window"],
                source_date=packet["source_date"],
                timezone=packet["timezone"],
                packet_json=packet,
                status="validated",
                created_at=packet["generated_at"],
                updated_at=packet["generated_at"],
            )
            output_row = create_composer_output(
                connection,
                output_id="composer-output-test",
                packet_id=packet["packet_id"],
                output_json=output,
                readable_text="Readable test output.",
                route_report=report,
                created_at=packet["generated_at"],
                updated_at=packet["generated_at"],
            )
            model_run = run_fake_composer_model(
                connection,
                packet=_valid_packet(packet_id="packet-state-run"),
                run_at="2026-06-15T14:00:00+00:00",
            )

        self.assertEqual(packet_row["packet_json"]["packet_id"], packet["packet_id"])
        self.assertEqual(output_row["route_report"]["no_external_writes"], True)
        self.assertEqual(model_run["status"], "blocked")

    def test_raw_state_counts_cover_composer_tables(self) -> None:
        packet = _valid_packet()
        output = _valid_output(packet_id=packet["packet_id"])

        with _migrated_test_connection() as connection:
            create_composer_packet(
                connection,
                packet_id=packet["packet_id"],
                packet_type=packet["packet_type"],
                briefing_window=packet["briefing_window"],
                source_date=packet["source_date"],
                timezone=packet["timezone"],
                packet_json=packet,
                created_at=packet["generated_at"],
                updated_at=packet["generated_at"],
            )
            create_composer_output(
                connection,
                output_id="composer-output-count",
                packet_id=packet["packet_id"],
                output_json=output,
                readable_text="Readable test output.",
                created_at=packet["generated_at"],
                updated_at=packet["generated_at"],
            )
            self.assertEqual(count_composer_packets(connection), 1)
            self.assertEqual(count_composer_outputs(connection), 1)
            self.assertEqual(count_model_runs(connection), 0)


class ComposerPermissionTest(unittest.TestCase):
    def test_permission_defaults_fail_closed(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(ComposerModulePermissionDenied):
                read_composer_packets(connection)
            with self.assertRaises(ComposerModulePermissionDenied):
                route_composer_output_candidates(connection, output_json=_valid_output())

            create_result = create_composer_packet_record(connection, packet=_valid_packet())
            run_result = run_fake_composer_model(
                connection,
                packet=_valid_packet(packet_id="packet-permission-run"),
                run_at="2026-06-15T14:00:00+00:00",
            )

        self.assertEqual(create_result["status"], "blocked")
        self.assertIn("Missing Composer module permission", create_result["reason"])
        self.assertEqual(run_result["status"], "blocked")

    def test_permission_gated_read_list_count_helpers(self) -> None:
        packet = _valid_packet()
        output = _valid_output(packet_id=packet["packet_id"])

        with _migrated_test_connection() as connection:
            _create_raw_packet_and_output(connection, packet, output)
            _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)

            packets = read_composer_packets(connection)
            packet_count = read_composer_packet_count(connection)
            outputs = read_composer_outputs(connection, packet_id=packet["packet_id"])
            output_count = read_composer_output_count(connection)
            runs = read_model_runs(connection)
            run_count = read_model_run_count(connection)

        self.assertEqual([item["id"] for item in packets], [packet["packet_id"]])
        self.assertEqual(packet_count, 1)
        self.assertEqual([item["packet_id"] for item in outputs], [packet["packet_id"]])
        self.assertEqual(output_count, 1)
        self.assertEqual(runs, [])
        self.assertEqual(run_count, 0)

    def test_permission_gated_write_helpers(self) -> None:
        packet = _valid_packet()
        output = _valid_output(packet_id=packet["packet_id"])

        with _migrated_test_connection() as connection:
            blocked_packet = create_composer_packet_record(connection, packet=packet)
            _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
            created_packet = create_composer_packet_record(connection, packet=packet)
            created_output = create_composer_output_record(
                connection,
                output_id="composer-output-write",
                packet_id=packet["packet_id"],
                output_json=output,
                readable_text="Readable test output.",
                route_report=build_candidate_routing_report(output),
                created_at=packet["generated_at"],
                updated_at=packet["generated_at"],
            )

        self.assertEqual(blocked_packet["status"], "blocked")
        self.assertEqual(created_packet["status"], "created")
        self.assertEqual(created_output["status"], "created")
        self.assertEqual(created_output["output"]["packet_id"], packet["packet_id"])
        self.assertEqual(created_output["output"]["output_json"]["packet_id"], packet["packet_id"])

    def test_composer_output_record_rejects_packet_id_mismatch(self) -> None:
        packet = _valid_packet(packet_id="packet-persisted")
        output = _valid_output(packet_id="packet-other")

        with _migrated_test_connection() as connection:
            _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
            create_composer_packet_record(connection, packet=packet)
            with self.assertRaises(ComposerValidationError):
                create_composer_output_record(
                    connection,
                    output_id="composer-output-mismatch",
                    packet_id="packet-persisted",
                    output_json=output,
                    readable_text="Readable test output.",
                    route_report=build_candidate_routing_report(output),
                    created_at=packet["generated_at"],
                    updated_at=packet["generated_at"],
                )
            output_count = count_composer_outputs(connection)

        self.assertEqual(output_count, 0)


class ComposerPacketValidationTest(unittest.TestCase):
    def test_packet_builder_happy_path_from_dev_test_state_summaries(self) -> None:
        with _migrated_test_connection() as connection:
            create_routine(
                connection,
                routine_id="routine-1",
                name="Morning review",
                created_at_utc="2026-06-15T10:00:00+00:00",
                updated_at_utc="2026-06-15T10:00:00+00:00",
            )
            create_priority(
                connection,
                priority_id="priority-1",
                title="Priority review",
                created_at_utc="2026-06-15T10:00:00+00:00",
                updated_at_utc="2026-06-15T10:00:00+00:00",
            )
            create_calendar_block(
                connection,
                title="Deep work",
                source_type="priority",
                source_id="priority-1",
                start_time="2026-06-15T10:00:00-05:00",
                end_time="2026-06-15T11:00:00-05:00",
                duration_minutes=60,
                calendar_id="primary",
                timezone=DEFAULT_TIMEZONE,
                created_at_utc="2026-06-15T10:00:00+00:00",
                updated_at_utc="2026-06-15T10:00:00+00:00",
            )

            packet = build_composer_packet_from_state(
                connection,
                packet_id="packet-builder",
                source_date="2026-06-15",
                generated_at="2026-06-15T14:00:00+00:00",
            )

        self.assertEqual(packet["schema_version"], "composer_packet.v1")
        self.assertEqual(packet["timezone"], DEFAULT_TIMEZONE)
        self.assertEqual(packet["inputs"]["routine_state"][0]["name"], "Morning review")
        self.assertEqual(
            packet["inputs"]["today_schedule_summary"][0]["title"],
            "Deep work",
        )

    def test_packet_builder_excludes_forbidden_inputs(self) -> None:
        with _migrated_test_connection() as connection:
            create_priority(
                connection,
                priority_id="priority-sensitive",
                title="Allowed title",
                metadata={"api_key": "not included"},
                notes="raw_notes should not be included",
                created_at_utc="2026-06-15T10:00:00+00:00",
                updated_at_utc="2026-06-15T10:00:00+00:00",
            )

            packet = build_composer_packet_from_state(
                connection,
                packet_id="packet-forbidden-excluded",
                source_date="2026-06-15",
                generated_at="2026-06-15T14:00:00+00:00",
            )

        serialized = json.dumps(packet, sort_keys=True)
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("raw_notes", serialized)
        self.assertEqual(packet["inputs"]["priority_summaries"][0]["summary"], "")

    def test_packet_validation_rejects_missing_required_fields(self) -> None:
        packet = _valid_packet()
        del packet["inputs"]

        with self.assertRaises(ComposerValidationError):
            validate_composer_packet(packet)

    def test_packet_validation_rejects_forbidden_field_names_and_claims(self) -> None:
        packet = _valid_packet(warnings=["claims full_vault access"])

        with self.assertRaises(ComposerValidationError):
            validate_composer_packet(packet)


class ComposerOutputValidationTest(unittest.TestCase):
    def test_output_validation_accepts_valid_structured_output(self) -> None:
        output = validate_composer_output(
            _valid_output(),
            readable_text="Readable structured brief.",
        )

        self.assertEqual(output["schema_version"], "composer_output.v1")
        self.assertEqual(output["todoist_tasks"][0]["priority"], 2)
        self.assertEqual(output["calendar_blocks"][0]["timezone"], DEFAULT_TIMEZONE)

    def test_output_validation_rejects_prose_only_output(self) -> None:
        with self.assertRaises(ComposerValidationError):
            validate_composer_output("this is prose only", readable_text="Readable.")

    def test_output_validation_rejects_missing_required_sections(self) -> None:
        output = _valid_output()
        del output["warnings"]

        with self.assertRaises(ComposerValidationError):
            validate_composer_output(output, readable_text="Readable.")

    def test_output_validation_rejects_missing_or_empty_readable_text(self) -> None:
        with self.assertRaises(ComposerValidationError):
            validate_composer_output(_valid_output(), readable_text=None)
        with self.assertRaises(ComposerValidationError):
            validate_composer_output(_valid_output(), readable_text=" ")

    def test_output_validation_rejects_malformed_todoist_tasks(self) -> None:
        output = _valid_output()
        output["todoist_tasks"][0]["priority"] = 5

        with self.assertRaises(ValueError):
            validate_composer_output(output, readable_text="Readable.")

    def test_output_validation_rejects_malformed_calendar_blocks(self) -> None:
        output = _valid_output()
        output["calendar_blocks"][0]["duration_minutes"] = 45

        with self.assertRaises(ValueError):
            validate_composer_output(output, readable_text="Readable.")

    def test_output_validation_rejects_high_risk_auto_allowed_candidates(self) -> None:
        output = _valid_output()
        output["todoist_tasks"][0]["risk_level"] = "high"
        output["todoist_tasks"][0]["approval_mode"] = "auto_allowed"

        with self.assertRaises(ValueError):
            validate_composer_output(output, readable_text="Readable.")

    def test_output_validation_rejects_medium_risk_auto_allowed_candidates(self) -> None:
        output = _valid_output()
        output["calendar_blocks"][0]["risk_level"] = "medium"
        output["calendar_blocks"][0]["approval_mode"] = "auto_allowed"

        with self.assertRaises(ValueError):
            validate_composer_output(output, readable_text="Readable.")

    def test_output_validation_rejects_forbidden_access_claims(self) -> None:
        output = _valid_output()
        output["email_briefs"][0]["body_markdown"] = "I used live_todoist_api data."

        with self.assertRaises(ComposerValidationError):
            validate_composer_output(output, readable_text="Readable.")


class ComposerRoutingAndAdapterTest(unittest.TestCase):
    def test_routing_valid_todoist_candidates_through_phase_5_validators(self) -> None:
        report = build_candidate_routing_report(_valid_output())

        self.assertEqual(report["accepted_candidates"][0]["candidate_type"], "todoist_task")
        self.assertEqual(report["accepted_candidates"][0]["status"], "accepted")
        self.assertFalse(report["accepted_candidates"][0]["database_write"])

    def test_routing_valid_calendar_candidates_through_phase_5_validators(self) -> None:
        report = build_candidate_routing_report(_valid_output())

        calendar_entries = [
            item
            for item in report["accepted_candidates"]
            if item["candidate_type"] == "calendar_block"
        ]
        self.assertEqual(calendar_entries[0]["status"], "accepted")
        self.assertFalse(calendar_entries[0]["external_mutation"])

    def test_rejected_candidate_report_shape(self) -> None:
        output = _valid_output()
        output["todoist_tasks"][0]["priority"] = 9

        report = build_candidate_routing_report(output)

        self.assertEqual(report["accepted_candidates"], [report["accepted_candidates"][0]])
        self.assertEqual(report["rejected_candidates"][0]["status"], "blocked_malformed")
        self.assertEqual(report["rejected_candidates"][0]["candidate_type"], "todoist_task")
        self.assertTrue(report["no_external_writes"])

    def test_blocked_high_risk_report_shape(self) -> None:
        output = _valid_output()
        output["calendar_blocks"][0]["risk_level"] = "high"
        output["calendar_blocks"][0]["approval_mode"] = "auto_allowed"

        report = build_candidate_routing_report(output)

        self.assertEqual(report["blocked_candidates"][0]["status"], "blocked_high_risk")
        self.assertEqual(report["blocked_candidates"][0]["candidate_type"], "calendar_block")
        self.assertTrue(report["no_external_writes"])

    def test_review_required_candidates_are_accepted_but_marked(self) -> None:
        output = _valid_output()
        output["todoist_tasks"][0]["risk_level"] = "medium"
        output["todoist_tasks"][0]["approval_mode"] = "approval_required"

        report = build_candidate_routing_report(output)
        todoist_entries = [
            item
            for item in report["accepted_candidates"]
            if item["candidate_type"] == "todoist_task"
        ]

        self.assertEqual(todoist_entries[0]["status"], "blocked_review_required")
        self.assertTrue(todoist_entries[0]["approval"]["requires_approval"])

    def test_fake_composer_adapter_deterministic_output(self) -> None:
        adapter = FakeComposerAdapter()
        packet = _valid_packet()

        first = adapter.compose(packet)
        second = adapter.compose(packet)

        self.assertEqual(first, second)
        self.assertEqual(adapter.calls, [{"packet_id": "packet-1"}, {"packet_id": "packet-1"}])

    def test_fake_model_run_success_persists_records(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
            _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)
            _set_permission(connection, COMPOSER_MODULE_READ_PERMISSION)
            result = run_fake_composer_model(
                connection,
                packet=_valid_packet(packet_id="packet-run-success"),
                run_at="2026-06-15T14:00:00+00:00",
            )
            model_run = get_model_run(connection, result["model_run"]["id"])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model_run"]["model_role"], "composer_model")
        self.assertEqual(result["model_run"]["model_name"], "fake-composer-v1")
        self.assertEqual(result["model_run"]["adapter_name"], "fake_composer_adapter")
        self.assertTrue(result["model_run"]["dry_run"])
        self.assertEqual(model_run["status"], "completed")
        self.assertTrue(result["route_report"]["no_external_writes"])

    def test_fake_model_run_failure_persists_failed_model_run(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
            _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)
            result = run_fake_composer_model(
                connection,
                packet=_valid_packet(packet_id="packet-run-failure"),
                adapter=FakeComposerAdapter(should_fail=True),
                run_at="2026-06-15T14:00:00+00:00",
            )
            model_runs = count_model_runs(connection)
            outputs = count_composer_outputs(connection)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["model_run"]["status"], "failed")
        self.assertEqual(model_runs, 1)
        self.assertEqual(outputs, 0)

    def test_fake_run_does_not_touch_external_systems(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, COMPOSER_MODULE_WRITE_PERMISSION)
            _set_permission(connection, COMPOSER_MODULE_RUN_PERMISSION)
            result = run_fake_composer_model(
                connection,
                packet=_valid_packet(packet_id="packet-no-external"),
                run_at="2026-06-15T14:00:00+00:00",
            )

        self.assertTrue(result["dry_run"])
        self.assertTrue(result["no_send"])
        self.assertFalse(result["external_mutation"])
        self.assertFalse(result["network_called"])

    def test_route_report_includes_no_external_writes_true(self) -> None:
        report = build_candidate_routing_report(_valid_output())

        self.assertIs(report["no_external_writes"], True)
        self.assertIs(report["candidate_routing_only"], True)

    def test_candidate_routing_report_is_not_full_output_validation(self) -> None:
        candidate_only_payload = {
            "todoist_tasks": [],
            "calendar_blocks": [],
            "warnings": [],
        }

        report = build_candidate_routing_report(candidate_only_payload)

        self.assertTrue(report["candidate_routing_only"])
        self.assertEqual(report["accepted_candidates"], [])
        with self.assertRaises(ComposerValidationError):
            validate_composer_output(candidate_only_payload, readable_text="Readable.")

    def test_validated_candidate_routing_report_requires_full_output(self) -> None:
        valid_report = build_validated_candidate_routing_report(
            _valid_output(),
            readable_text="Readable test output.",
        )
        invalid_output = _valid_output()
        del invalid_output["warnings"]

        self.assertFalse(valid_report["candidate_routing_only"])
        self.assertEqual(valid_report["full_output_validation"], "passed")
        self.assertTrue(valid_report["no_external_writes"])
        with self.assertRaises(ComposerValidationError):
            build_validated_candidate_routing_report(
                invalid_output,
                readable_text="Readable test output.",
            )

    def test_no_credentials_or_secrets_in_output_reports(self) -> None:
        report = build_candidate_routing_report(_valid_output())
        serialized = json.dumps(report, sort_keys=True).lower()

        for forbidden in ("credential", "secret", "token", "oauth", "password"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)


class ComposerArtifactSafetyTest(unittest.TestCase):
    def test_repo_has_no_runtime_database_or_var_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        sqlite_artifacts = [
            path
            for path in repo_root.rglob("*")
            if ".git" not in path.parts
            and path.is_file()
            and path.suffix in {".sqlite", ".sqlite3", ".db"}
        ]
        var_dirs = [
            path
            for path in repo_root.rglob("var")
            if ".git" not in path.parts and path.is_dir()
        ]

        self.assertEqual(sqlite_artifacts, [])
        self.assertEqual(var_dirs, [])


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


def _set_permission(
    connection: sqlite3.Connection,
    category: str,
    mode: PermissionMode = PermissionMode.AUTO_WRITE,
) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=mode.value,
        metadata={"phase": "6", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _create_raw_packet_and_output(
    connection: sqlite3.Connection,
    packet: dict[str, object],
    output: dict[str, object],
) -> None:
    create_composer_packet(
        connection,
        packet_id=str(packet["packet_id"]),
        packet_type=str(packet["packet_type"]),
        briefing_window=str(packet["briefing_window"]),
        source_date=str(packet["source_date"]),
        timezone=str(packet["timezone"]),
        packet_json=packet,
        created_at=str(packet["generated_at"]),
        updated_at=str(packet["generated_at"]),
    )
    create_composer_output(
        connection,
        output_id=stable_composer_id("composer-output", str(packet["packet_id"])),
        packet_id=str(packet["packet_id"]),
        output_json=output,
        readable_text="Readable test output.",
        route_report=build_candidate_routing_report(output),
        created_at=str(packet["generated_at"]),
        updated_at=str(packet["generated_at"]),
    )


def _valid_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": "composer_packet.v1",
        "packet_id": "packet-1",
        "packet_type": "daily_brief",
        "briefing_window": "morning",
        "source_date": "2026-06-15",
        "timezone": DEFAULT_TIMEZONE,
        "generated_at": "2026-06-15T14:00:00+00:00",
        "inputs": {
            "routine_state": [],
            "priority_summaries": [],
            "followup_summaries": [],
            "todoist_task_summaries": [],
            "calendar_block_summaries": [],
            "calendar_availability_summary": {},
            "today_schedule_summary": [],
            "wsp_routine_rules": [],
            "prior_briefing_summaries": [],
            "completion_status": {},
        },
        "omissions": ["Protected source classes omitted by policy."],
        "warnings": [],
    }
    packet.update(overrides)
    return packet


def _valid_output(**overrides: object) -> dict[str, object]:
    packet_id = str(overrides.pop("packet_id", "packet-1"))
    output: dict[str, object] = {
        "schema_version": "composer_output.v1",
        "packet_id": packet_id,
        "email_briefs": [
            {
                "briefing_window": "morning",
                "subject": "Morning brief",
                "body_markdown": "Review the safe dev/test summary.",
                "summary": "Safe summary.",
            }
        ],
        "todoist_tasks": [_todoist_candidate(packet_id=packet_id)],
        "calendar_blocks": [_calendar_candidate(packet_id=packet_id)],
        "followups": [_followup_candidate(packet_id=packet_id)],
        "warnings": [],
    }
    output.update(overrides)
    return output


def _todoist_candidate(**overrides: object) -> dict[str, object]:
    packet_id = str(overrides.pop("packet_id", "packet-1"))
    candidate: dict[str, object] = {
        "task_title": "Review morning brief",
        "description": "Review the generated candidate.",
        "source_type": "composer_output",
        "source_id": packet_id,
        "project": "Admin",
        "labels": ["composer", "preview"],
        "due_date_or_due_string": "2026-06-15",
        "priority": 2,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "dedupe_key": f"composer:{packet_id}:todoist",
        "status": "proposed",
    }
    candidate.update(overrides)
    return candidate


def _calendar_candidate(**overrides: object) -> dict[str, object]:
    packet_id = str(overrides.pop("packet_id", "packet-1"))
    candidate: dict[str, object] = {
        "title": "Review morning brief",
        "description": "Self-only review block.",
        "source_type": "composer_output",
        "source_id": packet_id,
        "start_time": "2026-06-15T10:00:00-05:00",
        "end_time": "2026-06-15T10:30:00-05:00",
        "duration_minutes": 30,
        "calendar_id": "primary",
        "timezone": DEFAULT_TIMEZONE,
        "approval_mode": "auto_allowed",
        "risk_level": "low",
        "dedupe_key": f"composer:{packet_id}:calendar",
        "status": "proposed",
    }
    candidate.update(overrides)
    return candidate


def _followup_candidate(**overrides: object) -> dict[str, object]:
    packet_id = str(overrides.pop("packet_id", "packet-1"))
    candidate: dict[str, object] = {
        "title": "Check brief result",
        "summary": "Confirm the preview needs no edits.",
        "source_type": "composer_output",
        "source_id": packet_id,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "dedupe_key": f"composer:{packet_id}:followup",
        "status": "proposed",
    }
    candidate.update(overrides)
    return candidate


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}

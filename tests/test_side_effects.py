import inspect
import os
import re
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos import cli, idempotency, side_effects
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.side_effects import (
    SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION,
    SIDE_EFFECT_LEDGER_WRITE_PERMISSION,
    SideEffectLedgerValidationError,
    build_external_write_intent,
    build_side_effect_completion_report,
    count_external_write_attempts,
    count_external_write_intents,
    count_idempotency_records,
    create_external_write_intent_record,
    get_idempotency_record,
    record_simulated_external_write_attempt,
    summarize_side_effect_ledgers,
)
from personalos.state import upsert_permission_setting


REPO_ROOT = Path(__file__).resolve().parents[1]


class IdempotencyHelperTest(unittest.TestCase):
    def test_payload_fingerprint_is_stable_for_equivalent_payloads(self) -> None:
        first = {"title": "Review", "labels": ["ops", "ledger"], "meta": {"b": 2, "a": 1}}
        second = {"meta": {"a": 1, "b": 2}, "labels": ["ops", "ledger"], "title": "Review"}

        self.assertEqual(
            idempotency.payload_fingerprint(first),
            idempotency.payload_fingerprint(second),
        )
        self.assertEqual(
            idempotency.generate_idempotency_key(
                target_system="todoist",
                operation_type="create",
                source_type="fake_fixture",
                source_id="phase-12b",
                dedupe_key="review-ledger",
                payload=first,
            ),
            idempotency.generate_idempotency_key(
                target_system="todoist",
                operation_type="create",
                source_type="fake_fixture",
                source_id="phase-12b",
                dedupe_key="review-ledger",
                payload=second,
            ),
        )

    def test_different_payloads_or_target_systems_get_different_keys(self) -> None:
        base_payload = {"title": "Review"}
        changed_payload = {"title": "Review again"}
        todoist_key = idempotency.generate_idempotency_key(
            target_system="todoist",
            operation_type="create",
            source_type="fake_fixture",
            source_id="phase-12b",
            dedupe_key="review-ledger",
            payload=base_payload,
        )
        calendar_key = idempotency.generate_idempotency_key(
            target_system="calendar",
            operation_type="create",
            source_type="fake_fixture",
            source_id="phase-12b",
            dedupe_key="review-ledger",
            payload=base_payload,
        )
        changed_payload_key = idempotency.generate_idempotency_key(
            target_system="todoist",
            operation_type="create",
            source_type="fake_fixture",
            source_id="phase-12b",
            dedupe_key="review-ledger",
            payload=changed_payload,
        )

        self.assertNotEqual(todoist_key, calendar_key)
        self.assertNotEqual(todoist_key, changed_payload_key)
        self.assertNotEqual(
            idempotency.payload_fingerprint(base_payload),
            idempotency.payload_fingerprint(changed_payload),
        )


class SideEffectIntentValidationTest(unittest.TestCase):
    def test_safe_low_risk_todoist_and_calendar_intents_validate_without_live_write(self) -> None:
        todoist = build_external_write_intent(**_todoist_intent_input())
        calendar = build_external_write_intent(**_calendar_intent_input())

        self.assertEqual(todoist["target_system"], "todoist")
        self.assertEqual(calendar["target_system"], "calendar")
        self.assertEqual(todoist["status"], "approved_for_dry_run")
        self.assertEqual(calendar["status"], "approved_for_dry_run")
        self.assertTrue(todoist["no_external_writes"])
        self.assertTrue(calendar["no_send_mode"])
        self.assertFalse(todoist["live_write"])
        self.assertFalse(calendar["live_write"])

    def test_high_risk_intent_cannot_be_auto_allowed(self) -> None:
        with self.assertRaises(ValueError):
            build_external_write_intent(
                **_todoist_intent_input(
                    risk_level="high",
                    approval_mode="auto_allowed",
                )
            )

    def test_live_write_claim_is_rejected_for_attempts(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_ledger_permissions(connection)
            intent_result = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(),
            )

            with self.assertRaises(SideEffectLedgerValidationError):
                record_simulated_external_write_attempt(
                    connection,
                    intent_id=intent_result["intent"]["intent_id"],
                    mode="dry_run",
                    adapter_name="phase_12b_fake_adapter",
                    status="succeeded",
                    response_summary={"result": "would_create"},
                    live_write=True,
                )

        self.assertEqual(intent_result["status"], "created")


class SideEffectLedgerFlowTest(unittest.TestCase):
    def test_permission_defaults_fail_closed_without_persisting_intent(self) -> None:
        with _migrated_test_connection() as connection:
            result = create_external_write_intent_record(connection, **_todoist_intent_input())
            counts = _side_effect_counts(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("Missing side-effect ledger permission", result["reason"])
        self.assertFalse(result["database_write"])
        self.assertEqual(counts["external_write_intents"], 0)
        self.assertEqual(counts["idempotency_records"], 0)

    def test_create_intent_records_idempotency_row_without_external_mutation(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, SIDE_EFFECT_LEDGER_WRITE_PERMISSION)
            result = create_external_write_intent_record(connection, **_todoist_intent_input())
            record = get_idempotency_record(
                connection,
                result["intent"]["idempotency_key"],
            )
            counts = _side_effect_counts(connection)

        self.assertEqual(result["status"], "created")
        self.assertEqual(counts["external_write_intents"], 1)
        self.assertEqual(counts["idempotency_records"], 1)
        self.assertIsNotNone(record)
        self.assertFalse(result["external_mutation"])
        self.assertTrue(result["completion_report"]["no_external_writes"])
        self.assertTrue(result["completion_report"]["no_send_mode"])
        self.assertFalse(result["completion_report"]["live_write"])

    def test_duplicate_intent_is_skipped_without_duplicate_rows(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, SIDE_EFFECT_LEDGER_WRITE_PERMISSION)
            first = create_external_write_intent_record(connection, **_todoist_intent_input())
            duplicate = create_external_write_intent_record(connection, **_todoist_intent_input())
            counts = _side_effect_counts(connection)

        self.assertEqual(first["status"], "created")
        self.assertEqual(duplicate["status"], "skipped_duplicate")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["intent"], first["intent"])
        self.assertEqual(counts["external_write_intents"], 1)
        self.assertEqual(counts["idempotency_records"], 1)

    def test_explicit_dedupe_collision_is_skipped_even_when_payload_differs(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, SIDE_EFFECT_LEDGER_WRITE_PERMISSION)
            first = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(dedupe_key="phase-12b-explicit"),
            )
            duplicate = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(
                    dedupe_key="phase-12b-explicit",
                    payload={"title": "Different title"},
                ),
            )
            counts = _side_effect_counts(connection)

        self.assertEqual(first["status"], "created")
        self.assertEqual(duplicate["status"], "skipped_duplicate")
        self.assertEqual(counts["external_write_intents"], 1)
        self.assertEqual(counts["idempotency_records"], 1)

    def test_dry_run_attempt_recording_updates_intent_and_completion_report(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_ledger_permissions(connection)
            intent_result = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(),
            )
            attempt_result = record_simulated_external_write_attempt(
                connection,
                intent_id=intent_result["intent"]["intent_id"],
                mode="dry_run",
                adapter_name="phase_12b_fake_adapter",
                status="succeeded",
                response_summary={"result": "would_create", "external_mutation": False},
            )
            counts = _side_effect_counts(connection)

        report = attempt_result["completion_report"]
        self.assertEqual(attempt_result["status"], "recorded")
        self.assertEqual(attempt_result["attempt"]["attempt_number"], 1)
        self.assertEqual(attempt_result["attempt"]["mode"], "dry_run")
        self.assertEqual(attempt_result["intent_after"]["status"], "dry_run_recorded")
        self.assertEqual(counts["external_write_attempts"], 1)
        self.assertTrue(report["no_external_writes"])
        self.assertTrue(report["no_send_mode"])
        self.assertFalse(report["live_write"])
        self.assertTrue(report["simulated_or_dry_run"])

    def test_failed_and_blocked_attempts_are_recorded_without_external_mutation(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_ledger_permissions(connection)
            failed_intent = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(source_id="failed"),
            )
            blocked_intent = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(source_id="blocked"),
            )
            failed = record_simulated_external_write_attempt(
                connection,
                intent_id=failed_intent["intent"]["intent_id"],
                mode="dry_run",
                adapter_name="phase_12b_fake_adapter",
                status="failed",
                response_summary={"result": "validation_failed"},
                error_message="Fixture failure.",
            )
            blocked = record_simulated_external_write_attempt(
                connection,
                intent_id=blocked_intent["intent"]["intent_id"],
                mode="live_blocked",
                adapter_name="phase_12b_fake_adapter",
                status="blocked",
                response_summary={"result": "live route blocked"},
            )
            counts = _side_effect_counts(connection)

        self.assertEqual(failed["intent_after"]["status"], "failed")
        self.assertEqual(blocked["intent_after"]["status"], "blocked")
        self.assertFalse(failed["external_mutation"])
        self.assertFalse(blocked["external_mutation"])
        self.assertEqual(counts["external_write_attempts"], 2)

    def test_read_only_summary_does_not_mutate_database(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_ledger_permissions(connection)
            intent_result = create_external_write_intent_record(
                connection,
                **_todoist_intent_input(),
            )
            record_simulated_external_write_attempt(
                connection,
                intent_id=intent_result["intent"]["intent_id"],
                mode="simulated",
                adapter_name="phase_12b_fake_adapter",
                status="succeeded",
                response_summary={"result": "simulated"},
            )
            before = _table_counts(connection)
            summary = summarize_side_effect_ledgers(connection)
            after = _table_counts(connection)

        self.assertEqual(before, after)
        self.assertEqual(summary["intent_count"], 1)
        self.assertEqual(summary["attempt_count"], 1)
        self.assertEqual(summary["idempotency_record_count"], 1)
        self.assertFalse(summary["live_write"])

    def test_completion_report_shape_is_explicitly_no_send_and_dry_run(self) -> None:
        report = build_side_effect_completion_report(
            status="succeeded",
            intents_considered=1,
            attempts_recorded=1,
            idempotency_key="idem:todoist:create:test",
        )

        self.assertTrue(report["no_external_writes"])
        self.assertTrue(report["no_send_mode"])
        self.assertFalse(report["live_write"])
        self.assertTrue(report["simulated_or_dry_run"])
        self.assertTrue(report["no_todoist_writes"])
        self.assertTrue(report["no_calendar_writes"])
        self.assertTrue(report["no_gmail_send"])
        self.assertTrue(report["no_personalos_writes"])

    def test_foreign_key_enforcement_rejects_orphan_attempt_directly(self) -> None:
        with _migrated_test_connection() as connection:
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
                        "orphan-attempt",
                        "missing-intent",
                        1,
                        "dry_run",
                        "phase_12b_fake_adapter",
                        "succeeded",
                        "sha256:request",
                        "{}",
                        None,
                        1,
                        1,
                        0,
                        "2026-06-15T10:00:00+00:00",
                    ),
                )


class SideEffectBoundaryTest(unittest.TestCase):
    def test_docs_describe_phase_12b_side_effect_boundary(self) -> None:
        docs_text = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "SAFETY_POLICY.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "CODEX_WORKFLOW.md").read_text(encoding="utf-8"),
            ]
        ).lower()

        required_phrases = (
            "phase 12b",
            "side-effect",
            "idempotency",
            "external_write_intents",
            "external_write_attempts",
            "idempotency_records",
            "no_external_writes=true",
            "no_send_mode=true",
            "live_write=false",
            "no live todoist writes",
            "no live calendar writes",
            "no personalos markdown writes",
            "no scheduler",
            "no launchagents",
            "no production db activation",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_side_effect_modules_have_no_live_api_client_imports(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(side_effects),
                inspect.getsource(idempotency),
                inspect.getsource(cli),
            ]
        )
        forbidden_imports = (
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "openrouter",
            "googleapiclient",
            "todoist",
            "gmail",
            "tradingview",
            "notion",
            "healthkit",
            "oura",
            "whoop",
            "garmin",
            "fitbit",
        )
        for module_name in forbidden_imports:
            pattern = rf"^\s*(from|import)\s+{re.escape(module_name)}\b"
            with self.subTest(module_name=module_name):
                self.assertIsNone(re.search(pattern, source, re.MULTILINE))

    def test_side_effect_modules_do_not_reference_protected_runtime_paths(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(side_effects),
                inspect.getsource(idempotency),
            ]
        ).lower()

        self.assertNotIn("/users/coldstake/personalos", source)
        self.assertNotIn("/users/coldstake/.openclaw", source)
        self.assertNotIn("launchagents", source)
        self.assertNotIn("oauth", source)

    def test_phase_12b_tests_leave_no_repo_var_or_sqlite_artifacts(self) -> None:
        db_artifacts: list[Path] = []
        var_dirs: list[Path] = []
        for directory, directories, filenames in os.walk(REPO_ROOT):
            current = Path(directory)
            if ".git" in current.parts:
                directories[:] = []
                continue
            directories[:] = [item for item in directories if item != ".git"]
            for dirname in directories:
                if dirname == "var":
                    var_dirs.append(current / dirname)
            for filename in filenames:
                path = current / filename
                if filename in {".sqlite", ".sqlite3"} or path.suffix in {
                    ".sqlite",
                    ".sqlite3",
                    ".db",
                }:
                    db_artifacts.append(path)

        self.assertEqual(db_artifacts, [])
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


def _enable_ledger_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SIDE_EFFECT_LEDGER_WRITE_PERMISSION)
    _set_permission(connection, SIDE_EFFECT_LEDGER_ATTEMPT_PERMISSION)


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"phase": "12b", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _todoist_intent_input(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_type": "fake_fixture",
        "source_id": "phase-12b",
        "target_system": "todoist",
        "operation_type": "create",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "payload": {
            "title": "Review side-effect ledger",
            "project": "Personal OS",
            "labels": ["review", "ledger"],
        },
        "validation_report": {
            "validated_by": "tests",
            "no_external_writes": True,
            "no_send_mode": True,
        },
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": "2026-06-15T10:00:00+00:00",
    }
    values.update(overrides)
    return values


def _calendar_intent_input(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_type": "fake_fixture",
        "source_id": "phase-12b-calendar",
        "target_system": "calendar",
        "operation_type": "create",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "payload": {
            "title": "Review side-effect ledger",
            "start_time": "2026-06-15T10:00:00+00:00",
            "end_time": "2026-06-15T10:30:00+00:00",
            "calendar_id": "primary",
        },
        "validation_report": {
            "validated_by": "tests",
            "no_external_writes": True,
            "no_send_mode": True,
        },
        "created_at": "2026-06-15T10:00:00+00:00",
        "updated_at": "2026-06-15T10:00:00+00:00",
    }
    values.update(overrides)
    return values


def _side_effect_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "external_write_intents": count_external_write_intents(connection),
        "external_write_attempts": count_external_write_attempts(connection),
        "idempotency_records": count_idempotency_records(connection),
    }


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        table_name = row["name"]
        if table_name.startswith("sqlite_"):
            continue
        counts[table_name] = int(
            connection.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        )
    return counts

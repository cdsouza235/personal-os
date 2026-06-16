import json
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.runtime_bootstrap import (
    RUNTIME_BOOTSTRAP_RUN_PERMISSION,
    RUNTIME_BOOTSTRAP_WRITE_PERMISSION,
    bootstrap_runtime_database,
)
from personalos.state import (
    SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS,
    count_calendar_blocks,
    count_followups,
    count_priorities,
    count_projects,
    count_routines,
    count_synthesis_import_previews,
    count_todoist_tasks,
    upsert_permission_setting,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
    SynthesisImportPermissionDenied,
    SynthesisImportValidationError,
    build_synthesis_import_preview,
    create_synthesis_import_preview_record,
    parse_synthesis_import,
    read_synthesis_import_preview,
    read_synthesis_import_preview_count,
    read_synthesis_import_previews,
    stable_input_hash,
)


class SynthesisImportParsingTest(unittest.TestCase):
    def test_valid_json_import_is_accepted(self) -> None:
        preview = build_synthesis_import_preview(json.dumps(_payload()))

        self.assertEqual(preview["input_format"], "json")
        self.assertEqual(preview["parsed_import"]["source_type"], "chatgpt_synthesis")
        self.assertEqual(preview["preview_report"]["candidate_counts"]["total"], 7)
        self.assertEqual(len(preview["preview_report"]["accepted_candidates"]), 6)
        self.assertEqual(len(preview["preview_report"]["questions_for_review"]), 1)

    def test_markdown_fenced_json_import_is_accepted(self) -> None:
        raw_input = "ChatGPT synthesis follows.\n\n```json\n" + json.dumps(_payload()) + "\n```"

        preview = build_synthesis_import_preview(raw_input)

        self.assertEqual(preview["input_format"], "markdown_fenced_json")
        self.assertEqual(preview["preview_report"]["source_type"], "chatgpt_synthesis")

    def test_structured_markdown_subset_is_accepted(self) -> None:
        raw_input = """
# Structured Import
Source Type: chatgpt_synthesis
Source Timestamp: 2026-06-15T10:00:00+00:00
Source Reference: chatgpt-thread-structured
Summary: Structured ChatGPT synthesis for import preview.

## Todoist Tasks
- task_title: Review structured synthesis
  description: Confirm the preview-only import report.
  source_type: chatgpt_synthesis
  source_id: structured-1
  project: Admin
  labels: synthesis, preview
  due_date_or_due_string: 2026-06-16
  priority: 2
  risk_level: low
  approval_mode: auto_allowed
  dedupe_key: structured todoist one
  status: proposed

## Review Questions
- question: Should this preview be applied in a later phase?
  reason: Phase 11A is preview-only.
  candidate_refs: todoist_tasks[0]
  status: open
"""

        preview = build_synthesis_import_preview(raw_input)

        self.assertEqual(preview["input_format"], "structured_markdown")
        self.assertEqual(preview["preview_report"]["candidate_counts"]["todoist_tasks"], 1)
        self.assertEqual(preview["preview_report"]["questions_for_review"][0]["status"], "open")

    def test_unsupported_prose_and_raw_notes_are_rejected(self) -> None:
        with self.assertRaises(SynthesisImportValidationError):
            parse_synthesis_import("I had a messy day and maybe should make tasks from it.")

        raw_notes_payload = _payload(source_type="raw_notes")
        with self.assertRaises(SynthesisImportValidationError):
            parse_synthesis_import(json.dumps(raw_notes_payload))

    def test_forbidden_source_types_are_rejected(self) -> None:
        for source_type in (
            "raw_journal",
            "full_vault_dump",
            "legal_source_documents",
            "tax_source_documents",
            "credential_dump",
            "unrestricted_file_input",
        ):
            with self.subTest(source_type=source_type):
                with self.assertRaises(SynthesisImportValidationError):
                    parse_synthesis_import(json.dumps(_payload(source_type=source_type)))

    def test_credential_like_input_is_rejected(self) -> None:
        raw_input = json.dumps(
            {
                **_payload(),
                "summary": "This contains api_key material and must be rejected.",
            }
        )

        with self.assertRaises(SynthesisImportValidationError):
            parse_synthesis_import(raw_input)


class SynthesisImportCandidateValidationTest(unittest.TestCase):
    def test_priority_followup_routine_todoist_calendar_and_clarity_candidates_preview(
        self,
    ) -> None:
        report = build_synthesis_import_preview(json.dumps(_payload()))["preview_report"]
        accepted_types = [item["candidate_type"] for item in report["accepted_candidates"]]

        self.assertEqual(report["candidate_counts"]["priorities"], 1)
        self.assertEqual(report["candidate_counts"]["followups"], 1)
        self.assertEqual(report["candidate_counts"]["routine_changes"], 1)
        self.assertEqual(report["candidate_counts"]["todoist_tasks"], 1)
        self.assertEqual(report["candidate_counts"]["calendar_blocks"], 1)
        self.assertEqual(report["candidate_counts"]["clarity_notes"], 1)
        self.assertIn("priorities", accepted_types)
        self.assertIn("followups", accepted_types)
        self.assertIn("routine_changes", accepted_types)
        self.assertIn("todoist_tasks", accepted_types)
        self.assertIn("calendar_blocks", accepted_types)
        self.assertIn("clarity_notes", accepted_types)

    def test_malformed_todoist_and_calendar_candidates_are_rejected(self) -> None:
        malformed = _payload(
            candidates={
                **_empty_candidates(),
                "todoist_tasks": [{**_todoist_candidate(), "priority": 5}],
                "calendar_blocks": [{**_calendar_candidate(), "duration_minutes": 45}],
            }
        )

        report = build_synthesis_import_preview(json.dumps(malformed))["preview_report"]

        rejected_types = [item["candidate_type"] for item in report["rejected_candidates"]]
        self.assertEqual(rejected_types, ["todoist_tasks", "calendar_blocks"])

    def test_medium_or_high_risk_auto_allowed_candidates_are_blocked(self) -> None:
        payload = _payload(
            candidates={
                **_empty_candidates(),
                "todoist_tasks": [
                    {
                        **_todoist_candidate(),
                        "task_title": "Review high-risk contract",
                        "risk_level": "high",
                        "approval_mode": "auto_allowed",
                    }
                ],
            }
        )

        report = build_synthesis_import_preview(json.dumps(payload))["preview_report"]

        self.assertEqual(len(report["blocked_candidates"]), 1)
        self.assertIn("Medium/high-risk", report["blocked_candidates"][0]["reason"])

    def test_crypto_portfolio_execution_low_auto_allowed_is_blocked(self) -> None:
        report = _report_for_single_todoist(
            {
                **_todoist_candidate(),
                "task_title": "Buy crypto for portfolio rebalance",
                "description": "Execute BTC allocation change.",
            }
        )

        self.assertEqual(len(report["blocked_candidates"]), 1)
        self.assertIn("Portfolio, crypto", report["blocked_candidates"][0]["reason"])

    def test_legal_tax_medical_execution_auto_allowed_is_blocked(self) -> None:
        report = _report_for_single_todoist(
            {
                **_todoist_candidate(),
                "task_title": "File tax amendment",
                "description": "Submit the tax directive automatically.",
            }
        )

        self.assertEqual(len(report["blocked_candidates"]), 1)
        self.assertIn("Legal, tax, or medical", report["blocked_candidates"][0]["reason"])

    def test_relationship_message_requires_approval_or_manual(self) -> None:
        blocked = _report_for_single_todoist(
            {
                **_todoist_candidate(),
                "task_title": "Send relationship message to Alex",
                "recipient": "Alex",
            }
        )
        review_required = _report_for_single_todoist(
            {
                **_todoist_candidate(),
                "task_title": "Send relationship message to Alex",
                "recipient": "Alex",
                "risk_level": "high",
                "approval_mode": "approval_required",
                "status": "needs_approval",
            }
        )

        self.assertEqual(len(blocked["blocked_candidates"]), 1)
        self.assertEqual(len(review_required["review_required_candidates"]), 1)

    def test_external_calendar_meeting_requires_approval_or_manual(self) -> None:
        blocked = _payload(
            candidates={
                **_empty_candidates(),
                "calendar_blocks": [
                    {
                        **_calendar_candidate(),
                        "title": "Meet with Alex",
                        "attendees": ["alex@example.test"],
                    }
                ],
            }
        )
        review_required = _payload(
            candidates={
                **_empty_candidates(),
                "calendar_blocks": [
                    {
                        **_calendar_candidate(),
                        "title": "Meet with Alex",
                        "attendees": ["alex@example.test"],
                        "risk_level": "high",
                        "approval_mode": "approval_required",
                        "status": "needs_approval",
                    }
                ],
            }
        )

        blocked_report = build_synthesis_import_preview(json.dumps(blocked))["preview_report"]
        review_report = build_synthesis_import_preview(
            json.dumps(review_required)
        )["preview_report"]

        self.assertEqual(len(blocked_report["blocked_candidates"]), 1)
        self.assertEqual(len(review_report["review_required_candidates"]), 1)


class SynthesisImportReportTest(unittest.TestCase):
    def test_preview_report_counts_questions_and_safety_flags(self) -> None:
        report = build_synthesis_import_preview(json.dumps(_payload()))["preview_report"]

        self.assertEqual(report["candidate_counts"]["total"], 7)
        self.assertEqual(report["rejected_candidates"], [])
        self.assertEqual(report["blocked_candidates"], [])
        self.assertEqual(len(report["questions_for_review"]), 1)
        self.assertTrue(report["no_external_writes"])
        self.assertTrue(report["no_state_mutation"])
        self.assertTrue(report["no_personalos_writes"])
        self.assertTrue(report["no_todoist_writes"])
        self.assertTrue(report["no_calendar_writes"])
        self.assertTrue(report["no_gmail_send"])
        self.assertTrue(report["no_live_model_call"])

    def test_preview_report_does_not_mutate_state(self) -> None:
        with _migrated_test_connection() as connection:
            before = _core_counts(connection)
            build_synthesis_import_preview(json.dumps(_payload()))
            after = _core_counts(connection)

        self.assertEqual(after, before)


class SynthesisImportPersistenceTest(unittest.TestCase):
    def test_persisted_preview_create_read_list_and_count_work(self) -> None:
        with _migrated_test_connection() as connection:
            _set_synthesis_permissions(connection)
            result = create_synthesis_import_preview_record(
                connection,
                json.dumps(_payload()),
                created_at="2026-06-15T10:00:00+00:00",
            )
            preview_id = result["record"]["id"]
            read_back = read_synthesis_import_preview(connection, preview_id=preview_id)
            listed = read_synthesis_import_previews(connection)
            count = read_synthesis_import_preview_count(connection)

        self.assertEqual(result["status"], "created")
        self.assertEqual(read_back["id"], preview_id)
        self.assertEqual([item["id"] for item in listed], [preview_id])
        self.assertEqual(count, 1)
        self.assertTrue(result["preview_report"]["no_external_writes"])

    def test_input_hash_is_stable_and_raw_excerpt_is_bounded(self) -> None:
        long_payload = _payload(summary="x" * 3000)
        raw_input = json.dumps(long_payload, sort_keys=True)

        with _migrated_test_connection() as connection:
            _set_synthesis_permissions(connection)
            result = create_synthesis_import_preview_record(connection, raw_input)

        self.assertEqual(stable_input_hash(raw_input), result["record"]["input_hash"])
        self.assertEqual(
            len(result["record"]["raw_excerpt"]),
            SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS,
        )
        self.assertLess(len(result["record"]["raw_excerpt"]), len(raw_input))

    def test_schema_check_constraints_are_enforced(self) -> None:
        too_long_excerpt = "x" * (SYNTHESIS_IMPORT_RAW_EXCERPT_MAX_CHARS + 1)
        invalid_cases = (
            ("bad-source", "chatgpt_synthesis", "json", "validated", "short"),
            ("bad-format", "chatgpt_synthesis", "prose", "validated", "short"),
            ("bad-status", "chatgpt_synthesis", "json", "apply_live", "short"),
            ("bad-excerpt", "chatgpt_synthesis", "json", "validated", too_long_excerpt),
        )

        with _migrated_test_connection() as connection:
            for preview_id, source_type, input_format, status, excerpt in invalid_cases:
                with self.subTest(preview_id=preview_id):
                    with self.assertRaises(sqlite3.IntegrityError):
                        connection.execute(
                            """
                            INSERT INTO synthesis_import_previews (
                                id,
                                source_type,
                                input_format,
                                input_hash,
                                raw_excerpt,
                                parsed_json,
                                preview_report_json,
                                status,
                                created_at,
                                updated_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                preview_id,
                                source_type if preview_id != "bad-source" else "raw_notes",
                                input_format,
                                "hash",
                                excerpt,
                                "{}",
                                "{}",
                                status,
                                "2026-06-15T10:00:00+00:00",
                                "2026-06-15T10:00:00+00:00",
                            ),
                        )

    def test_no_execution_rail_or_gmail_writes_occur_on_persist(self) -> None:
        with _migrated_test_connection() as connection:
            _set_synthesis_permissions(connection)
            result = create_synthesis_import_preview_record(connection, json.dumps(_payload()))
            todoist_count = count_todoist_tasks(connection)
            calendar_count = count_calendar_blocks(connection)

        self.assertEqual(result["record"]["status"], "validated")
        self.assertEqual(todoist_count, 0)
        self.assertEqual(calendar_count, 0)
        self.assertTrue(result["no_gmail_send"])


class SynthesisImportPermissionTest(unittest.TestCase):
    def test_defaults_fail_closed_for_persistence_and_reads(self) -> None:
        with _migrated_test_connection() as connection:
            result = create_synthesis_import_preview_record(connection, json.dumps(_payload()))
            count = count_synthesis_import_previews(connection)
            with self.assertRaises(SynthesisImportPermissionDenied):
                read_synthesis_import_previews(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(count, 0)

    def test_write_and_preview_permissions_are_required_for_persistence(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)
            write_missing = create_synthesis_import_preview_record(
                connection,
                json.dumps(_payload()),
            )

        with _migrated_test_connection() as connection:
            _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
            preview_missing = create_synthesis_import_preview_record(
                connection,
                json.dumps(_payload()),
            )

        self.assertEqual(write_missing["status"], "blocked")
        self.assertIn(SYNTHESIS_IMPORT_WRITE_PERMISSION, write_missing["reason"])
        self.assertEqual(preview_missing["status"], "blocked")
        self.assertIn(SYNTHESIS_IMPORT_PREVIEW_PERMISSION, preview_missing["reason"])

    def test_read_permission_is_required_for_list_and_count(self) -> None:
        with _migrated_test_connection() as connection:
            _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
            _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)
            create_synthesis_import_preview_record(connection, json.dumps(_payload()))

            with self.assertRaises(SynthesisImportPermissionDenied):
                read_synthesis_import_preview_count(connection)

            _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
            self.assertEqual(read_synthesis_import_preview_count(connection), 1)


class SynthesisImportBootstrapSmokeTest(unittest.TestCase):
    def test_bootstrap_runtime_db_can_store_preview_without_core_state_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            profile = _runtime_profile(temp_path)
            with _migrated_connection(temp_path / "auth-runtime") as permission_connection:
                _set_permission(permission_connection, RUNTIME_BOOTSTRAP_WRITE_PERMISSION)
                _set_permission(permission_connection, RUNTIME_BOOTSTRAP_RUN_PERMISSION)
                bootstrap_result = bootstrap_runtime_database(
                    profile,
                    permission_connection=permission_connection,
                )

            self.assertEqual(bootstrap_result["status"], "completed")
            db_path = Path(profile["db_path"])
            with _sqlite_connection(db_path) as connection:
                _set_synthesis_permissions(connection)
                baseline = _core_counts(connection)
                result = create_synthesis_import_preview_record(
                    connection,
                    json.dumps(_payload(source_type="fake_fixture")),
                )
                after = _core_counts(connection)
                preview_count = count_synthesis_import_previews(connection)

        self.assertEqual(result["status"], "created")
        self.assertEqual(preview_count, 1)
        self.assertEqual(after, baseline)
        self.assertTrue(result["no_external_writes"])
        self.assertTrue(result["no_state_mutation"])


def _payload(
    *,
    source_type: str = "chatgpt_synthesis",
    summary: str = "Structured ChatGPT synthesis for preview import.",
    candidates: dict[str, list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "synthesis_import.v1",
        "source_type": source_type,
        "source_timestamp": "2026-06-15T10:00:00+00:00",
        "source_reference": "chatgpt-thread-1",
        "summary": summary,
        "candidates": candidates if candidates is not None else _full_candidates(),
        "warnings": ["Preview only; no writes."],
    }


def _empty_candidates() -> dict[str, list[dict[str, object]]]:
    return {
        "priorities": [],
        "projects": [],
        "followups": [],
        "routine_changes": [],
        "todoist_tasks": [],
        "calendar_blocks": [],
        "clarity_notes": [],
        "review_questions": [],
    }


def _full_candidates() -> dict[str, list[dict[str, object]]]:
    candidates = _empty_candidates()
    candidates["priorities"] = [_priority_candidate()]
    candidates["followups"] = [_followup_candidate()]
    candidates["routine_changes"] = [_routine_change_candidate()]
    candidates["todoist_tasks"] = [_todoist_candidate()]
    candidates["calendar_blocks"] = [_calendar_candidate()]
    candidates["clarity_notes"] = [_clarity_note_candidate()]
    candidates["review_questions"] = [_review_question()]
    return candidates


def _priority_candidate() -> dict[str, object]:
    return {
        "title": "Stabilize synthesis import previews",
        "summary": "Keep imports preview-only until apply gates exist.",
        "source_type": "chatgpt_synthesis",
        "source_id": "synth-1",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "active",
        "review_note": "Review in the next implementation phase.",
    }


def _followup_candidate() -> dict[str, object]:
    return {
        "title": "Review Phase 11B gate",
        "summary": "Decide whether the next phase is UI preview or apply flow.",
        "source_type": "chatgpt_synthesis",
        "source_id": "synth-1",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "open",
        "due_date_or_review_note": "Review after Phase 11A PR.",
    }


def _routine_change_candidate() -> dict[str, object]:
    return {
        "routine_name": "Evening review",
        "change_type": "review",
        "summary": "Consider adding synthesis import review to shutdown.",
        "proposed_fields": {"review_prompt": "Check synthesis import previews."},
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
    }


def _todoist_candidate() -> dict[str, object]:
    return {
        "task_title": "Review synthesis import preview",
        "description": "Check accepted and blocked candidates.",
        "source_type": "chatgpt_synthesis",
        "source_id": "synth-1",
        "project": "Admin",
        "labels": ["synthesis", "preview"],
        "due_date_or_due_string": "2026-06-16",
        "priority": 2,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "dedupe_key": "synthesis import todoist review",
        "status": "proposed",
    }


def _calendar_candidate() -> dict[str, object]:
    return {
        "title": "Review synthesis import preview",
        "description": "Self-only review block.",
        "source_type": "chatgpt_synthesis",
        "source_id": "synth-1",
        "start_time": "2026-06-16T10:00:00-05:00",
        "end_time": "2026-06-16T10:30:00-05:00",
        "duration_minutes": 30,
        "calendar_id": "primary",
        "timezone": DEFAULT_TIMEZONE,
        "approval_mode": "auto_allowed",
        "risk_level": "low",
        "dedupe_key": "synthesis import calendar review",
        "status": "proposed",
    }


def _clarity_note_candidate() -> dict[str, object]:
    return {
        "title": "Synthesis import remains preview-only",
        "summary": "No PersonalOS Markdown write should happen in Phase 11A.",
        "category": "architecture",
        "source_reference": "chatgpt-thread-1",
        "durable_insight": "Import previews need explicit apply gates before mutation.",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
    }


def _review_question() -> dict[str, object]:
    return {
        "question": "Should Phase 11B add a dashboard paste/import preview UI?",
        "reason": "Phase 11A has no paste box or apply flow.",
        "candidate_refs": ["todoist_tasks[0]", "calendar_blocks[0]"],
        "status": "open",
    }


def _report_for_single_todoist(candidate: dict[str, object]) -> dict[str, object]:
    payload = _payload(
        candidates={
            **_empty_candidates(),
            "todoist_tasks": [candidate],
        }
    )
    return build_synthesis_import_preview(json.dumps(payload))["preview_report"]


def _core_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "routines": count_routines(connection),
        "priorities": count_priorities(connection),
        "projects": count_projects(connection),
        "followups": count_followups(connection),
        "todoist_tasks": count_todoist_tasks(connection),
        "calendar_blocks": count_calendar_blocks(connection),
    }


@contextmanager
def _migrated_test_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        with _migrated_connection(Path(temp_dir) / "runtime") as connection:
            yield connection


@contextmanager
def _migrated_connection(runtime_dir: Path) -> Iterator[sqlite3.Connection]:
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


@contextmanager
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _set_synthesis_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"source": "tests"},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


def _runtime_profile(temp_path: Path) -> dict[str, object]:
    return {
        "profile_name": "phase-11a-preview",
        "runtime_mode": "local_runtime_preview",
        "db_path_label": "temp-runtime-preview",
        "db_path": str(temp_path / "runtime" / "preview" / "personalos.sqlite3"),
        "backup_enabled": True,
        "backup_dir": None,
        "no_external_writes": True,
        "no_send_mode": True,
        "seed_profile_name": "mvp_preview_safe_seed",
        "created_by": "tests",
    }

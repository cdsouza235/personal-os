import json
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import personalos.synthesis_apply as synthesis_apply_module
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.permissions import PermissionMode
from personalos.side_effects import (
    count_external_write_attempts,
    count_external_write_intents,
)
from personalos.state import (
    count_calendar_blocks,
    count_followups,
    count_priorities,
    count_projects,
    count_synthesis_import_previews,
    count_todoist_tasks,
    get_followup,
    get_priority,
    get_project,
    get_synthesis_import_preview,
    upsert_permission_setting,
)
from personalos.synthesis_apply import (
    SYNTHESIS_APPLY_APPLY_PERMISSION,
    SYNTHESIS_APPLY_READ_PERMISSION,
    SYNTHESIS_APPLY_WRITE_PERMISSION,
    SynthesisApplyPermissionDenied,
    SynthesisApplyValidationError,
    apply_synthesis_import_preview,
    count_synthesis_apply_items,
    count_synthesis_apply_runs,
    list_synthesis_apply_items,
    summarize_synthesis_apply_runs,
)
from personalos.synthesis_import import (
    SYNTHESIS_IMPORT_PREVIEW_PERMISSION,
    SYNTHESIS_IMPORT_READ_PERMISSION,
    SYNTHESIS_IMPORT_WRITE_PERMISSION,
    create_synthesis_import_preview_record,
)


class SynthesisApplyPermissionTest(unittest.TestCase):
    def test_apply_fails_closed_without_explicit_apply_permission(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_synthesis_import_permissions(connection)
            preview_id = _create_preview(connection)
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["database_write"])
        self.assertFalse(result["internal_state_mutation"])
        self.assertFalse(result["rolled_back"])
        self.assertIn(SYNTHESIS_APPLY_READ_PERMISSION, result["reason"])

    def test_apply_permission_is_required_even_when_read_and_write_are_enabled(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_synthesis_import_permissions(connection)
            _set_permission(connection, SYNTHESIS_APPLY_READ_PERMISSION)
            _set_permission(connection, SYNTHESIS_APPLY_WRITE_PERMISSION)
            preview_id = _create_preview(connection)
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn(SYNTHESIS_APPLY_APPLY_PERMISSION, result["reason"])

    def test_read_summary_requires_read_permission(self) -> None:
        with _migrated_test_connection() as connection:
            with self.assertRaises(SynthesisApplyPermissionDenied):
                summarize_synthesis_apply_runs(connection)


class SynthesisApplyApprovalValidationTest(unittest.TestCase):
    def test_approval_preview_id_must_match(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection)

            with self.assertRaises(SynthesisApplyValidationError):
                apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval=_approval("wrong-preview", ("priority", 0)),
                )

    def test_candidate_hash_mismatch_is_rejected_before_apply(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection)
            before = _core_counts(connection)

            with self.assertRaises(SynthesisApplyValidationError):
                apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval={
                        "preview_id": preview_id,
                        "approved_candidates": [
                            {
                                "candidate_type": "priority",
                                "candidate_index": 0,
                                "candidate_hash": "not-the-candidate-hash",
                            }
                        ],
                    },
                )
            after = _core_counts(connection)

        self.assertEqual(after, before)

    def test_missing_candidate_ref_is_rejected_before_apply(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection)
            before = _core_counts(connection)

            with self.assertRaises(SynthesisApplyValidationError):
                apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval=_approval(preview_id, ("priority", 99)),
                )
            after = _core_counts(connection)

        self.assertEqual(after, before)

    def test_apply_rejects_stored_project_candidate_with_invalid_status(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            _overwrite_preview_candidate_status(
                connection,
                preview_id=preview_id,
                section="projects",
                status="needs-triage",
            )
            before = _core_counts(connection)

            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("project", 0)),
            )
            after = _core_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(after, before)
        self.assertTrue(any("project status must be one of" in item["error_message"] for item in items))

    def test_apply_rejects_stored_followup_candidate_with_invalid_status(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            _overwrite_preview_candidate_status(
                connection,
                preview_id=preview_id,
                section="followups",
                status="maybe-laterish",
            )
            before = _core_counts(connection)

            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("followup", 0)),
            )
            after = _core_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(after, before)
        self.assertTrue(any("followup status must be one of" in item["error_message"] for item in items))


class SynthesisApplyBehaviorTest(unittest.TestCase):
    def test_safe_priority_project_and_followup_apply_to_internal_state_only(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection)
            before = _all_counts(connection)
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(
                    preview_id,
                    ("priority", 0),
                    ("project", 0),
                    ("followup", 0),
                ),
                approval_source_type="json_file",
                approval_source_hash="approval-hash",
            )
            after = _all_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            preview = get_synthesis_import_preview(connection, preview_id)
            applied_item_by_type = {
                item["candidate_type"]: item
                for item in items
                if item["apply_status"] == "applied"
            }
            created_priority = get_priority(
                connection,
                applied_item_by_type["priorities"]["target_id"],
            )
            created_project = get_project(
                connection,
                applied_item_by_type["projects"]["target_id"],
            )
            created_followup = get_followup(
                connection,
                applied_item_by_type["followups"]["target_id"],
            )

        self.assertEqual(result["status"], "partially_completed")
        self.assertEqual(after["priorities"] - before["priorities"], 1)
        self.assertEqual(after["projects"] - before["projects"], 1)
        self.assertEqual(after["followups"] - before["followups"], 1)
        self.assertEqual(after["todoist_tasks"], before["todoist_tasks"])
        self.assertEqual(after["calendar_blocks"], before["calendar_blocks"])
        self.assertEqual(after["external_write_intents"], before["external_write_intents"])
        self.assertEqual(after["external_write_attempts"], before["external_write_attempts"])
        self.assertEqual(after["synthesis_apply_runs"] - before["synthesis_apply_runs"], 1)
        self.assertEqual(result["completion_report"]["counts"]["applied_candidate_count"], 3)
        self.assertTrue(result["no_external_writes"])
        self.assertTrue(result["no_send_mode"])
        self.assertFalse(result["live_write"])
        self.assertTrue(result["internal_state_mutation"])
        self.assertFalse(result["rolled_back"])
        self.assertTrue(result["completion_report"]["internal_state_mutation"])
        self.assertFalse(result["completion_report"]["rolled_back"])
        self.assertEqual(preview["status"], "apply_partially_completed")
        applied_targets = {(item["candidate_type"], item["apply_status"]) for item in items}
        self.assertIn(("priorities", "applied"), applied_targets)
        self.assertIn(("projects", "applied"), applied_targets)
        self.assertIn(("followups", "applied"), applied_targets)
        self.assertIn(("todoist_tasks", "not_applied"), applied_targets)
        self.assertIn(("calendar_blocks", "not_applied"), applied_targets)
        self.assertTrue(
            all(
                item["target_table"] in {None, "priorities", "projects", "followups"}
                for item in items
            )
        )
        self.assertIsNotNone(created_priority)
        self.assertIsNotNone(created_project)
        self.assertIsNotNone(created_followup)
        self.assertEqual(
            applied_item_by_type["priorities"]["target_id"],
            created_priority["priority_id"],
        )
        self.assertEqual(
            applied_item_by_type["projects"]["target_id"],
            created_project["project_id"],
        )
        self.assertEqual(
            applied_item_by_type["followups"]["target_id"],
            created_followup["followup_id"],
        )

    def test_unsupported_candidates_can_be_explicitly_rejected(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection)
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval={
                    "preview_id": preview_id,
                    "approved_candidates": [],
                    "rejected_candidates": [
                        {
                            "candidate_type": "todoist_task",
                            "candidate_index": 0,
                            "reason": "external rail not allowed in Phase 13A",
                        }
                    ],
                    "approval_note": "Reject external rail candidates.",
                },
            )
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )

        rejected = [
            item
            for item in items
            if item["candidate_type"] == "todoist_tasks"
        ][0]
        self.assertEqual(result["status"], "no_op")
        self.assertEqual(rejected["approval_status"], "rejected")
        self.assertEqual(rejected["apply_status"], "not_applied")
        self.assertIn("external rail", rejected["error_message"])

    def test_high_stakes_execution_candidate_is_blocked(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_high_stakes_payload())
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            priority_count = count_priorities(connection)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(items[0]["approval_status"], "blocked")
        self.assertEqual(items[0]["apply_status"], "blocked")
        self.assertTrue(items[0]["high_stakes"])
        self.assertEqual(priority_count, 0)

    def test_manual_only_candidate_is_review_required_not_applied(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_manual_only_payload())
            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            priority_count = count_priorities(connection)

        self.assertEqual(result["status"], "no_op")
        self.assertEqual(items[0]["approval_status"], "review_required")
        self.assertEqual(items[0]["apply_status"], "not_applied")
        self.assertEqual(priority_count, 0)

    def test_apply_rerun_skips_duplicate_internal_state_records(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            approval = _approval(preview_id, ("priority", 0), ("project", 0), ("followup", 0))
            first = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=approval,
            )
            second = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=approval,
            )
            second_items = list_synthesis_apply_items(
                connection,
                apply_run_id=second["apply_run_id"],
            )
            counts = {
                "priorities": count_priorities(connection),
                "projects": count_projects(connection),
                "followups": count_followups(connection),
                "apply_runs": count_synthesis_apply_runs(connection),
            }

        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "no_op")
        self.assertEqual(counts["priorities"], 1)
        self.assertEqual(counts["projects"], 1)
        self.assertEqual(counts["followups"], 1)
        self.assertEqual(counts["apply_runs"], 2)
        self.assertFalse(second["internal_state_mutation"])
        self.assertFalse(second["completion_report"]["internal_state_mutation"])
        self.assertFalse(second["rolled_back"])
        self.assertEqual(
            {item["apply_status"] for item in second_items},
            {"skipped_duplicate"},
        )

    def test_apply_reruns_candidate_validation_and_records_failed_item(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            preview = get_synthesis_import_preview(connection, preview_id)
            parsed = dict(preview["parsed_json"])
            candidates = dict(parsed["candidates"])
            priorities = [dict(candidates["priorities"][0])]
            priorities[0].pop("title")
            candidates["priorities"] = priorities
            parsed["candidates"] = candidates
            connection.execute(
                """
                UPDATE synthesis_import_previews
                SET parsed_json = ?
                WHERE id = ?
                """,
                (json.dumps(parsed, allow_nan=False, sort_keys=True), preview_id),
            )
            connection.commit()

            result = apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            priority_item = [
                item
                for item in items
                if item["candidate_type"] == "priorities"
            ][0]
            priority_count = count_priorities(connection)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(priority_item["apply_status"], "failed")
        self.assertTrue(priority_item["validation_report"]["validation_reran"])
        self.assertEqual(priority_count, 0)

    def test_summary_reports_latest_safety_flags_read_only(self) -> None:
        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            apply_synthesis_import_preview(
                connection,
                preview_id=preview_id,
                approval=_approval(preview_id, ("priority", 0)),
            )
            before = _all_counts(connection)
            summary = summarize_synthesis_apply_runs(connection)
            after = _all_counts(connection)

        self.assertEqual(after, before)
        self.assertTrue(summary["available"])
        self.assertEqual(summary["apply_run_count"], 1)
        self.assertTrue(summary["latest_no_external_writes"])
        self.assertFalse(summary["latest_live_write"])
        self.assertTrue(summary["read_only"])


class SynthesisApplyAtomicityTest(unittest.TestCase):
    def test_apply_run_insert_failure_rolls_back_core_insert_and_records_recovery(
        self,
    ) -> None:
        original_insert_run = synthesis_apply_module._insert_apply_run
        calls = 0

        def fail_once(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise sqlite3.OperationalError("simulated apply run insert failure")
            original_insert_run(*args, **kwargs)

        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            before = _all_counts(connection)

            with patch.object(
                synthesis_apply_module,
                "_insert_apply_run",
                side_effect=fail_once,
            ):
                result = apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval=_approval(preview_id, ("priority", 0)),
                )

            after = _all_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            preview = get_synthesis_import_preview(connection, preview_id)

        self.assertEqual(calls, 2)
        self._assert_rollback_recovery(result, before, after, items, preview)
        self.assertEqual(after["priorities"], before["priorities"])

    def test_apply_item_insert_failure_rolls_back_core_rows_without_applied_audit_items(
        self,
    ) -> None:
        original_insert_item = synthesis_apply_module._insert_apply_item
        calls = 0

        def fail_once(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise sqlite3.OperationalError("simulated apply item insert failure")
            original_insert_item(*args, **kwargs)

        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            before = _all_counts(connection)

            with patch.object(
                synthesis_apply_module,
                "_insert_apply_item",
                side_effect=fail_once,
            ):
                result = apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval=_approval(
                        preview_id,
                        ("priority", 0),
                        ("project", 0),
                        ("followup", 0),
                    ),
                )

            after = _all_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            preview = get_synthesis_import_preview(connection, preview_id)

        self.assertEqual(calls, 4)
        self._assert_rollback_recovery(result, before, after, items, preview)
        self.assertEqual(after["priorities"], before["priorities"])
        self.assertEqual(after["projects"], before["projects"])
        self.assertEqual(after["followups"], before["followups"])

    def test_preview_status_update_failure_rolls_back_core_and_audit_rows(
        self,
    ) -> None:
        original_update_status = synthesis_apply_module.update_synthesis_import_preview_status
        calls = 0

        def fail_once(*args: object, **kwargs: object) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise sqlite3.OperationalError("simulated preview status update failure")
            return original_update_status(*args, **kwargs)

        with _migrated_test_connection() as connection:
            _enable_all_permissions(connection)
            preview_id = _create_preview(connection, payload=_safe_core_only_payload())
            before = _all_counts(connection)

            with patch.object(
                synthesis_apply_module,
                "update_synthesis_import_preview_status",
                side_effect=fail_once,
            ):
                result = apply_synthesis_import_preview(
                    connection,
                    preview_id=preview_id,
                    approval=_approval(
                        preview_id,
                        ("priority", 0),
                        ("project", 0),
                        ("followup", 0),
                    ),
                )

            after = _all_counts(connection)
            items = list_synthesis_apply_items(
                connection,
                apply_run_id=result["apply_run_id"],
            )
            preview = get_synthesis_import_preview(connection, preview_id)

        self.assertEqual(calls, 2)
        self._assert_rollback_recovery(result, before, after, items, preview)
        self.assertEqual(after["priorities"], before["priorities"])
        self.assertEqual(after["projects"], before["projects"])
        self.assertEqual(after["followups"], before["followups"])

    def _assert_rollback_recovery(
        self,
        result: dict[str, object],
        before: dict[str, int],
        after: dict[str, int],
        items: list[dict[str, object]],
        preview: dict[str, object] | None,
    ) -> None:
        self.assertEqual(result["status"], "failed")
        self.assertIn("rolled back", result["reason"])
        self.assertTrue(result["database_write"])
        self.assertFalse(result["internal_state_mutation"])
        self.assertTrue(result["rolled_back"])
        self.assertFalse(result["external_mutation"])
        self.assertTrue(result["no_external_writes"])
        self.assertTrue(result["no_send_mode"])
        self.assertFalse(result["live_write"])
        self.assertEqual(after["synthesis_apply_runs"] - before["synthesis_apply_runs"], 1)
        self.assertEqual(
            after["synthesis_apply_items"] - before["synthesis_apply_items"],
            len(items),
        )
        self.assertEqual(after["external_write_intents"], before["external_write_intents"])
        self.assertEqual(after["external_write_attempts"], before["external_write_attempts"])
        self.assertEqual(preview["status"], "apply_failed")
        self.assertEqual(result["run"]["status"], "failed")
        self.assertFalse(result["run"]["internal_state_mutation"])
        self.assertTrue(result["completion_report"]["rolled_back"])
        self.assertTrue(result["completion_report"]["rollback_verified"])
        self.assertFalse(result["completion_report"]["internal_state_mutation"])
        self.assertNotIn("applied", {item["apply_status"] for item in items})
        rollback_items = [
            item
            for item in items
            if item["approval_status"] == "approved"
            and item["target_table"] in {"priorities", "projects", "followups"}
        ]
        self.assertGreaterEqual(len(rollback_items), 1)
        self.assertTrue(
            all(item["rollback_metadata"]["rolled_back"] for item in rollback_items)
        )
        self.assertTrue(
            all(item["apply_status"] == "failed" for item in rollback_items)
        )


def _create_preview(
    connection: sqlite3.Connection,
    *,
    payload: dict[str, object] | None = None,
) -> str:
    result = create_synthesis_import_preview_record(
        connection,
        json.dumps(payload or _payload(), allow_nan=False, sort_keys=True),
    )
    if result["status"] != "created":
        raise AssertionError(f"preview setup failed: {result['status']}")
    return result["record"]["id"]


def _overwrite_preview_candidate_status(
    connection: sqlite3.Connection,
    *,
    preview_id: str,
    section: str,
    status: str,
) -> None:
    preview = get_synthesis_import_preview(connection, preview_id)
    if preview is None:
        raise AssertionError(f"preview setup failed: missing preview {preview_id}")
    parsed_json = dict(preview["parsed_json"])
    candidates = dict(parsed_json["candidates"])
    items = list(candidates[section])
    items[0] = {**items[0], "status": status}
    candidates[section] = items
    parsed_json["candidates"] = candidates
    connection.execute(
        """
        UPDATE synthesis_import_previews
        SET parsed_json = ?
        WHERE id = ?
        """,
        (
            json.dumps(parsed_json, allow_nan=False, separators=(",", ":"), sort_keys=True),
            preview_id,
        ),
    )
    connection.commit()


def _approval(preview_id: str, *refs: tuple[str, int]) -> dict[str, object]:
    return {
        "preview_id": preview_id,
        "approved_candidates": [
            {
                "candidate_type": candidate_type,
                "candidate_index": candidate_index,
            }
            for candidate_type, candidate_index in refs
        ],
        "rejected_candidates": [],
        "approval_note": "Approved for internal SQLite state only.",
    }


def _payload() -> dict[str, object]:
    candidates = _empty_candidates()
    candidates["priorities"] = [_priority_candidate()]
    candidates["projects"] = [_project_candidate()]
    candidates["followups"] = [_followup_candidate()]
    candidates["routine_changes"] = [_routine_change_candidate()]
    candidates["todoist_tasks"] = [_todoist_candidate()]
    candidates["calendar_blocks"] = [_calendar_candidate()]
    candidates["clarity_notes"] = [_clarity_note_candidate()]
    candidates["review_questions"] = [_review_question()]
    return _payload_with_candidates(candidates)


def _safe_core_only_payload() -> dict[str, object]:
    candidates = _empty_candidates()
    candidates["priorities"] = [_priority_candidate()]
    candidates["projects"] = [_project_candidate()]
    candidates["followups"] = [_followup_candidate()]
    return _payload_with_candidates(candidates)


def _high_stakes_payload() -> dict[str, object]:
    candidates = _empty_candidates()
    candidates["priorities"] = [
        {
            **_priority_candidate(),
            "title": "Execute portfolio crypto rebalance",
            "summary": "Review whether to buy crypto for the investment portfolio.",
            "risk_level": "high",
            "approval_mode": "approval_required",
        }
    ]
    return _payload_with_candidates(candidates)


def _manual_only_payload() -> dict[str, object]:
    candidates = _empty_candidates()
    candidates["priorities"] = [
        {
            **_priority_candidate(),
            "approval_mode": "manual_only",
            "status": "paused",
        }
    ]
    return _payload_with_candidates(candidates)


def _payload_with_candidates(candidates: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    return {
        "schema_version": "synthesis_import.v1",
        "source_type": "chatgpt_synthesis",
        "source_timestamp": "2026-06-15T10:00:00+00:00",
        "source_reference": "chatgpt-thread-phase-13a",
        "summary": "Structured ChatGPT synthesis for approval-gated apply.",
        "candidates": candidates,
        "warnings": ["Internal state apply requires explicit approval."],
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


def _priority_candidate() -> dict[str, object]:
    return {
        "title": "Stabilize synthesis apply",
        "summary": "Apply safe synthesis candidates only after explicit approval.",
        "source_type": "chatgpt_synthesis",
        "source_id": "phase-13a",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "active",
        "review_note": "Review item-level apply outcomes.",
    }


def _project_candidate() -> dict[str, object]:
    return {
        "title": "Synthesis apply audit trail",
        "summary": "Track candidate-by-candidate apply decisions.",
        "source_type": "chatgpt_synthesis",
        "source_id": "phase-13a",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "active",
        "review_note": "Keep this internal-state-only.",
    }


def _followup_candidate() -> dict[str, object]:
    return {
        "title": "Review synthesis apply report",
        "summary": "Confirm unsupported targets stayed non-executable.",
        "source_type": "chatgpt_synthesis",
        "source_id": "phase-13a",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "open",
        "due_date_or_review_note": "Review after local tests.",
    }


def _routine_change_candidate() -> dict[str, object]:
    return {
        "routine_name": "Evening review",
        "change_type": "review",
        "summary": "Consider reviewing synthesis apply reports manually.",
        "proposed_fields": {"review_prompt": "Check synthesis apply runs."},
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
    }


def _todoist_candidate() -> dict[str, object]:
    return {
        "task_title": "Review synthesis apply preview",
        "description": "External rail candidate must not be written.",
        "source_type": "chatgpt_synthesis",
        "source_id": "phase-13a",
        "project": "Admin",
        "labels": ["synthesis", "apply"],
        "due_date_or_due_string": "2026-06-16",
        "priority": 2,
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "dedupe_key": "synthesis apply todoist review",
        "status": "proposed",
    }


def _calendar_candidate() -> dict[str, object]:
    return {
        "title": "Review synthesis apply preview",
        "description": "Self-only block still must not be written to Calendar.",
        "source_type": "chatgpt_synthesis",
        "source_id": "phase-13a",
        "start_time": "2026-06-16T10:00:00-07:00",
        "end_time": "2026-06-16T10:30:00-07:00",
        "duration_minutes": 30,
        "calendar_id": "primary",
        "timezone": DEFAULT_TIMEZONE,
        "approval_mode": "auto_allowed",
        "risk_level": "low",
        "dedupe_key": "synthesis apply calendar review",
        "status": "proposed",
    }


def _clarity_note_candidate() -> dict[str, object]:
    return {
        "title": "Apply remains SQLite-only",
        "summary": "Clarity notes are not Markdown writes in Phase 13A.",
        "category": "architecture",
        "source_reference": "chatgpt-thread-phase-13a",
        "durable_insight": "No PersonalOS Markdown writes happen during apply.",
        "risk_level": "low",
        "approval_mode": "auto_allowed",
        "status": "proposed",
    }


def _review_question() -> dict[str, object]:
    return {
        "question": "Should unsupported candidates be revisited later?",
        "reason": "Phase 13A only applies internal core state.",
        "candidate_refs": ["todoist_tasks[0]", "calendar_blocks[0]"],
        "status": "open",
    }


def _core_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "priorities": count_priorities(connection),
        "projects": count_projects(connection),
        "followups": count_followups(connection),
        "todoist_tasks": count_todoist_tasks(connection),
        "calendar_blocks": count_calendar_blocks(connection),
    }


def _all_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        **_core_counts(connection),
        "external_write_intents": count_external_write_intents(connection),
        "external_write_attempts": count_external_write_attempts(connection),
        "synthesis_import_previews": count_synthesis_import_previews(connection),
        "synthesis_apply_runs": count_synthesis_apply_runs(connection),
        "synthesis_apply_items": count_synthesis_apply_items(connection),
    }


def _enable_all_permissions(connection: sqlite3.Connection) -> None:
    _enable_synthesis_import_permissions(connection)
    _set_permission(connection, SYNTHESIS_APPLY_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_APPLY_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_APPLY_APPLY_PERMISSION)


def _enable_synthesis_import_permissions(connection: sqlite3.Connection) -> None:
    _set_permission(connection, SYNTHESIS_IMPORT_READ_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_WRITE_PERMISSION)
    _set_permission(connection, SYNTHESIS_IMPORT_PREVIEW_PERMISSION)


def _set_permission(connection: sqlite3.Connection, category: str) -> None:
    upsert_permission_setting(
        connection,
        category=category,
        mode=PermissionMode.AUTO_WRITE.value,
        metadata={"phase": "13a", "dev_test_only": True},
        updated_by="tests",
        updated_at_utc="2026-06-15T10:00:00+00:00",
    )


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

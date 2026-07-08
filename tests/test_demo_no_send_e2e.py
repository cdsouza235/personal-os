import json
import sqlite3
import tempfile
import unittest
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from personalos.demo.no_send_e2e import ARTIFACT_NAMES, run_no_send_e2e_demo
from personalos.state import (
    count_calendar_blocks,
    count_followups,
    count_priorities,
    count_projects,
    count_routines,
    count_todoist_tasks,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


class NoSendE2EDemoRunnerTest(unittest.TestCase):
    def test_runner_creates_expected_evidence_bundle_under_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evidence"
            report = run_no_send_e2e_demo(output_dir)

            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["demo_name"], "phase_13e_d_synthetic_no_send_e2e")
            self.assertEqual(report["phase_name"], "Phase 13E-D - synthetic end-to-end no-send demo")
            self.assertTrue(report["phase_14_blocked"])
            self.assertTrue(report["artifact_list"])
            self.assertEqual(
                {artifact["name"] for artifact in report["artifact_list"]},
                set(ARTIFACT_NAMES),
            )
            for artifact_name in ARTIFACT_NAMES:
                with self.subTest(artifact_name=artifact_name):
                    artifact_path = Path(report["artifact_paths"][artifact_name])
                    artifact_path.relative_to(output_dir.resolve())
                    self.assertTrue(artifact_path.exists())

            db_path = Path(report["generated_db_path"])
            db_path.relative_to(output_dir.resolve())
            self.assertEqual(db_path.name, "demo.sqlite3")
            self.assertTrue(db_path.is_file())
            self.assertEqual(report["fixture_manifest_hash"], _read_json(output_dir / "synthetic_input_manifest.json")["fixture_manifest_hash"])

    def test_runner_safety_assertions_are_complete_and_inert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evidence"
            report = run_no_send_e2e_demo(output_dir)

        safety = report["safety_assertions"]
        expected_false = (
            "any_rail_live",
            "any_rail_soaking",
            "launch_agent_installed",
            "crontab_modified",
            "daemon_started",
            "external_mutation",
            "gmail_touched",
            "todoist_touched",
            "calendar_touched",
            "personalos_markdown_written",
            "protected_paths_touched",
        )
        self.assertEqual(
            safety["rails"],
            {"todoist": "inert", "gmail": "inert", "calendar": "inert", "model_api": "inert"},
        )
        self.assertEqual(safety["scheduler_state"], "off")
        self.assertEqual(safety["invalid_rail_states"], [])
        for key in expected_false:
            with self.subTest(key=key):
                self.assertFalse(safety[key])
        self.assertTrue(safety["all_required_assertions_passed"])

    def test_runner_fixture_coverage_and_preview_only_external_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evidence"
            report = run_no_send_e2e_demo(output_dir)
            manifest = _read_json(output_dir / "synthetic_input_manifest.json")
            preview = _read_json(output_dir / "synthesis_preview.json")
            apply_report = _read_json(output_dir / "synthesis_apply_report.json")
            side_effects = _read_json(output_dir / "side_effect_ledger_summary.json")
            idempotency = _read_json(output_dir / "idempotency_ledger_summary.json")
            scheduler = _read_json(output_dir / "scheduler_simulation_evidence.json")
            db_path = Path(report["generated_db_path"])

            with _sqlite_connection(db_path) as connection:
                counts = {
                    "routines": count_routines(connection),
                    "priorities": count_priorities(connection),
                    "projects": count_projects(connection),
                    "followups": count_followups(connection),
                    "todoist_tasks": count_todoist_tasks(connection),
                    "calendar_blocks": count_calendar_blocks(connection),
                }

        coverage = manifest["coverage"]
        self.assertTrue(coverage["routines"])
        self.assertTrue(coverage["priorities"])
        self.assertTrue(coverage["projects_focus_areas"])
        self.assertTrue(coverage["followups"])
        self.assertTrue(coverage["todoist_preview_only_candidates"])
        self.assertTrue(coverage["calendar_preview_only_candidates"])
        self.assertTrue(coverage["gmail_no_send_briefing_export_only"])
        self.assertTrue(coverage["markdown_note_review_only_candidates"])
        self.assertEqual(
            set(coverage["blocked_high_stakes_candidates"]),
            {
                "tax",
                "legal_estate",
                "portfolio_crypto_investments",
                "health_medical",
                "relationship_messages",
            },
        )
        self.assertGreaterEqual(counts["routines"], 3)
        self.assertGreaterEqual(counts["priorities"], 2)
        self.assertGreaterEqual(counts["projects"], 2)
        self.assertGreaterEqual(counts["followups"], 2)
        self.assertEqual(counts["todoist_tasks"], 0)
        self.assertEqual(counts["calendar_blocks"], 0)
        self.assertGreaterEqual(len(preview["preview_report"]["blocked_candidates"]), 4)
        self.assertGreaterEqual(len(preview["preview_report"]["review_required_candidates"]), 4)
        self.assertEqual(apply_report["idempotency_evidence"]["rerun_status"], "blocked")
        self.assertFalse(apply_report["idempotency_evidence"]["internal_state_duplicated"])
        self.assertEqual(
            apply_report["idempotency_evidence"]["rerun_item_statuses"],
            ["blocked", "not_applied", "skipped_duplicate"],
        )
        self.assertEqual(side_effects["intent_count"], 4)
        self.assertEqual(side_effects["attempt_count"], 4)
        self.assertEqual(idempotency["duplicate_attempt_status"], "skipped_duplicate")
        self.assertTrue(idempotency["duplicate_skipped_without_external_mutation"])
        self.assertEqual(scheduler["status"], "simulated_preview_only")
        self.assertFalse(scheduler["scheduler_activated"])

    def test_runner_does_not_create_repo_var_or_repo_sqlite_artifacts(self) -> None:
        before_artifacts = _repo_db_artifacts()
        self.assertFalse((REPO_ROOT / "var").exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            run_no_send_e2e_demo(Path(temp_dir) / "evidence")

        self.assertFalse((REPO_ROOT / "var").exists())
        self.assertEqual(_repo_db_artifacts(), before_artifacts)

    def test_completion_report_json_is_deterministic_except_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir:
            first = run_no_send_e2e_demo(Path(first_dir) / "evidence")
        with tempfile.TemporaryDirectory() as second_dir:
            second = run_no_send_e2e_demo(Path(second_dir) / "evidence")

        first_normalized = _normalize_report_paths(first, first["output_dir"])
        second_normalized = _normalize_report_paths(second, second["output_dir"])
        self.assertEqual(first_normalized, second_normalized)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_report_paths(value: object, output_dir: str) -> object:
    if isinstance(value, Mapping):
        return {
            key: _normalize_report_paths(item, output_dir)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_report_paths(item, output_dir) for item in value]
    if isinstance(value, str):
        return value.replace(output_dir, "<OUTPUT_DIR>")
    return value


def _repo_db_artifacts() -> list[str]:
    artifacts: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix in DB_SUFFIXES:
            artifacts.append(str(path.relative_to(REPO_ROOT)))
    return sorted(artifacts)


@contextmanager
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()

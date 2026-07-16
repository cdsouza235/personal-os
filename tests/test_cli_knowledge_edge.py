"""P-KE-1C: `personalos knowledge-edge scan|queue show|flag-false-positive` CLI flows.

Exercises the CLI surface end-to-end against a migrated dev/test SQLite database:
a fixture-only scan (no live network), idempotent re-run, queue preview (human and
JSON output), and the false-positive flag round-trip (state-layer write via its own
public API, ``flag_entity_match_false_positive``).
"""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos import cli
from personalos.cli.reporting import _human_report
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations

QUEUE_DATE = "2026-07-16"


class CliRunResult:
    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr


def _run_cli(args: list[str]) -> CliRunResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = cli.main(args)
        except SystemExit as error:
            code = 0 if error.code is None else int(error.code)
    return CliRunResult(code, stdout.getvalue(), stderr.getvalue())


@contextmanager
def _migrated_db_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = PersonalOSConfig(
            environment=Environment.TEST,
            timezone=DEFAULT_TIMEZONE,
            database_path=runtime_dir / "test" / "personalos.sqlite3",
        )
        connection = connect_sqlite(config, runtime_dir=runtime_dir)
        apply_migrations(connection)
        connection.close()
        yield config.database_path


@contextmanager
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


class ScanCommandTest(unittest.TestCase):
    def test_scan_creates_fixture_media_and_events_and_reports_completion(self) -> None:
        with _migrated_db_path() as db_path:
            result = _run_cli(
                [
                    "knowledge-edge",
                    "scan",
                    "--db",
                    str(db_path),
                    "--date",
                    QUEUE_DATE,
                    "--now",
                    "2026-07-16T21:00:00+00:00",
                    "--json",
                ]
            )
            self.assertEqual(result.code, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["media_items_created"], 3)
            self.assertEqual(payload["events_created"], 1)
            self.assertEqual(payload["sources_healthy"], 5)
            self.assertEqual(payload["sources_failed"], 0)
            self.assertTrue(payload["no_external_writes"])
            self.assertFalse(payload["external_mutation"])

            with _sqlite_connection(db_path) as connection:
                self.assertEqual(ke.count_media_items(connection), 3)
                self.assertEqual(ke.count_scheduled_events(connection), 1)

    def test_rerunning_scan_is_idempotent(self) -> None:
        with _migrated_db_path() as db_path:
            first = _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00", "--json",
                ]
            )
            self.assertEqual(first.code, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["media_items_created"], 3)

            second = _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00", "--json",
                ]
            )
            self.assertEqual(second.code, 0, second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertEqual(second_payload["media_items_created"], 0)
            self.assertEqual(second_payload["events_created"], 0)
            self.assertEqual(second_payload["queue_snapshot_rows_created"], 0)

            with _sqlite_connection(db_path) as connection:
                self.assertEqual(ke.count_media_items(connection), 3)
                self.assertEqual(ke.count_scheduled_events(connection), 1)

    def test_scan_human_output_reports_counts(self) -> None:
        with _migrated_db_path() as db_path:
            result = _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00",
                ]
            )
            self.assertEqual(result.code, 0, result.stderr)
            self.assertIn("command: knowledge-edge scan", result.stdout)
            self.assertIn("status: completed", result.stdout)
            self.assertIn("media_items_created: 3", result.stdout)
            self.assertIn("events_created: 1", result.stdout)
            self.assertIn("fixture_set: cli-builtin-demo", result.stdout)


class QueueShowCommandTest(unittest.TestCase):
    def test_queue_show_reports_sections_and_coverage(self) -> None:
        with _migrated_db_path() as db_path:
            scan_result = _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00", "--json",
                ]
            )
            self.assertEqual(scan_result.code, 0, scan_result.stderr)

            show_result = _run_cli(
                ["knowledge-edge", "queue", "show", "--db", str(db_path), "--date", QUEUE_DATE, "--json"]
            )
            self.assertEqual(show_result.code, 0, show_result.stderr)
            payload = json.loads(show_result.stdout)
            queue_summary = payload["queue_summary"]
            self.assertEqual(queue_summary["feature_mode"], "fixture")
            self.assertTrue(queue_summary["available"])
            self.assertEqual(len(queue_summary["sections"]["p0_consequential_leaders"]), 1)
            self.assertEqual(len(queue_summary["sections"]["p1_core_podcasts"]), 1)
            self.assertEqual(len(queue_summary["sections"]["p2_market_voices"]), 1)
            self.assertEqual(len(queue_summary["sections"]["tomorrow_earnings_events"]), 1)
            self.assertIn("healthy", queue_summary["coverage"]["overall_summary"])
            self.assertFalse(payload["database_write"])

    def test_queue_show_human_output_renders_full_queue_content(self) -> None:
        with _migrated_db_path() as db_path:
            _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00", "--json",
                ]
            )
            show_result = _run_cli(
                ["knowledge-edge", "queue", "show", "--db", str(db_path), "--date", QUEUE_DATE]
            )
            self.assertEqual(show_result.code, 0, show_result.stderr)
            output = show_result.stdout
            self.assertIn("knowledge_edge_feature_mode: fixture", output)

            # Section headings and item titles -- not just row counts.
            self.assertIn("P0: Consequential Leader Appearances (1):", output)
            self.assertIn("Jensen Huang: The Future of Compute", output)
            self.assertIn("P1: Core Podcast Releases (1):", output)
            self.assertIn("A Long Conversation", output)
            self.assertIn("P2: Market Voice Appearances (1):", output)
            self.assertIn("Tom Lee on Bitcoin and Market Outlook", output)
            self.assertIn("Tomorrow: Earnings & Corporate Events (1):", output)
            self.assertIn("NVIDIA", output)

            # Directness / why-surfaced labels, not summarized away.
            self.assertIn("direct_primary", output)
            self.assertIn("directness=direct_primary", output)

            # The demoted/ambiguous section still renders (empty for this fixture set).
            self.assertIn("Demoted / Ambiguous (0):", output)

            # Coverage gaps/health, per-adapter, not a single collapsed line.
            self.assertIn("Coverage & Source Health:", output)
            self.assertIn("Earnings Calendar:", output)
            self.assertIn(
                "Coverage reflects only sources successfully checked this scan",
                output,
            )

    def test_human_report_renders_demoted_ambiguous_labels_and_quarantined_links(self) -> None:
        """Unit-tests the reporting-layer rendering directly against a synthetic
        queue_summary shaped like ``build_knowledge_edge_queue_summary``'s output,
        since the CLI's own built-in fixture scan never produces an ambiguous item
        or an unapproved-vendor webcast link (see knowledge_edge/dashboard.py's
        ``DEFAULT_APPROVED_WEBCAST_VENDOR_DOMAINS`` -- empty by default, so every
        live_webcast_url is quarantined, but the built-in CLI fixture events never
        set one)."""
        queue_summary = {
            "feature_mode": "fixture",
            "available": True,
            "queue_date": QUEUE_DATE,
            "sections": {
                "tomorrow_earnings_events": [
                    {
                        "entity_type": "scheduled_event",
                        "event_id": "evt-1",
                        "company_display_name": "NVIDIA",
                        "event_type": "quarterly_earnings",
                        "scheduled_date": QUEUE_DATE,
                        "event_status": "scheduled",
                        "link": {
                            "label": "Link pending (unknown vendor)",
                            "url": None,
                            "official_event_page_url": None,
                            "quarantined": True,
                        },
                    }
                ],
                "p0_consequential_leaders": [
                    {
                        "entity_type": "media_item",
                        "media_item_id": "med-1",
                        "title": "Jensen Huang: The Future of Compute",
                        "directness_class": "direct_primary",
                        "false_positive_flagged": False,
                        "why_surfaced": "directness=direct_primary (+100)",
                    }
                ],
                "p1_core_podcasts": [],
                "p2_market_voices": [],
                "saved_to_reconsider": [],
            },
            "demoted_ambiguous": [
                {
                    "entity_type": "media_item",
                    "media_item_id": "med-2",
                    "title": "Jensen Huang Segment (duration unknown)",
                    "directness_class": "ambiguous",
                    "false_positive_flagged": False,
                    "why_surfaced": (
                        "directness=ambiguous (+20); not substantive "
                        "(ambiguous_unknown_duration_demoted)"
                    ),
                }
            ],
            "coverage": {
                "overall_summary": "5 of 5 sources healthy",
                "report": {"sources_healthy": 5, "sources_total": 5},
                "per_adapter_lines": [
                    "Dwarkesh Podcast: healthy; last success 2026-07-16T18:00:00+00:00",
                ],
                "honesty_note": (
                    "Coverage reflects only sources successfully checked this scan; "
                    "absence of a result is never proof that no appearance occurred."
                ),
            },
            "empty_state": None,
        }
        rendered = _human_report(
            {"command": "knowledge-edge queue show", "status": "completed", "queue_summary": queue_summary}
        )

        self.assertIn("P0: Consequential Leader Appearances (1):", rendered)
        self.assertIn("Jensen Huang: The Future of Compute", rendered)
        self.assertIn("directness=direct_primary", rendered)

        self.assertIn("Demoted / Ambiguous (1):", rendered)
        self.assertIn("Jensen Huang Segment (duration unknown)", rendered)
        self.assertIn("ambiguous_unknown_duration_demoted", rendered)

        self.assertIn("Tomorrow: Earnings & Corporate Events (1):", rendered)
        self.assertIn("Link pending (unknown vendor)", rendered)

        self.assertIn("Coverage & Source Health:", rendered)
        self.assertIn("Dwarkesh Podcast: healthy", rendered)
        self.assertIn(
            "Coverage reflects only sources successfully checked this scan", rendered
        )

    def test_queue_show_on_empty_database_reports_unavailable_empty_state(self) -> None:
        with _migrated_db_path() as db_path:
            show_result = _run_cli(
                ["knowledge-edge", "queue", "show", "--db", str(db_path), "--date", QUEUE_DATE, "--json"]
            )
            self.assertEqual(show_result.code, 0, show_result.stderr)
            payload = json.loads(show_result.stdout)
            queue_summary = payload["queue_summary"]
            self.assertIsNotNone(queue_summary["empty_state"])
            self.assertIn("No qualifying item was found", queue_summary["empty_state"])


class FlagFalsePositiveCommandTest(unittest.TestCase):
    def test_flag_false_positive_round_trips_through_state_layer(self) -> None:
        with _migrated_db_path() as db_path:
            scan_result = _run_cli(
                [
                    "knowledge-edge", "scan", "--db", str(db_path),
                    "--date", QUEUE_DATE, "--now", "2026-07-16T21:00:00+00:00", "--json",
                ]
            )
            self.assertEqual(scan_result.code, 0, scan_result.stderr)

            with _sqlite_connection(db_path) as connection:
                p0_item = next(
                    item
                    for item in ke.list_media_items(connection)
                    if item["directness_class"] == "direct_primary"
                    and ke.get_source(connection, item["source_id"])["lane"] == "consequential_leaders"
                )
                entity_match = ke.list_entity_matches(
                    connection, target_type="media_item", target_id=p0_item["media_item_id"]
                )[0]
                self.assertFalse(entity_match["is_false_positive"])
                entity_match_id = entity_match["entity_match_id"]

            flag_result = _run_cli(
                [
                    "knowledge-edge", "flag-false-positive", "--db", str(db_path),
                    "--entity-match-id", entity_match_id, "--json",
                ]
            )
            self.assertEqual(flag_result.code, 0, flag_result.stderr)
            payload = json.loads(flag_result.stdout)
            self.assertEqual(payload["status"], "flagged")
            self.assertTrue(payload["entity_match"]["is_false_positive"])
            self.assertTrue(payload["database_write"])

            with _sqlite_connection(db_path) as connection:
                updated_match = ke.get_entity_match(connection, entity_match_id)
                self.assertTrue(updated_match["is_false_positive"])

            show_result = _run_cli(
                ["knowledge-edge", "queue", "show", "--db", str(db_path), "--date", QUEUE_DATE, "--json"]
            )
            queue_summary = json.loads(show_result.stdout)["queue_summary"]
            flagged_card = next(
                card
                for card in queue_summary["sections"]["p0_consequential_leaders"]
                if card["media_item_id"] == p0_item["media_item_id"]
            )
            self.assertTrue(flagged_card["false_positive_flagged"])

    def test_flag_false_positive_on_unknown_id_is_a_clean_cli_error(self) -> None:
        with _migrated_db_path() as db_path:
            result = _run_cli(
                [
                    "knowledge-edge", "flag-false-positive", "--db", str(db_path),
                    "--entity-match-id", "does-not-exist",
                ]
            )
            self.assertEqual(result.code, 1)
            self.assertIn("error:", result.stderr)
            self.assertIn("does-not-exist", result.stderr)


if __name__ == "__main__":
    unittest.main()

"""P-KE-2C: shadow-report generator tests (personalos.knowledge_edge.shadow_report).

Precision/recall/leakage math is hand-computed here against synthetic graded
ground truth -- no network, no live scan, no dependency on a real sample file.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.knowledge_edge.shadow_bootstrap import (
    LANE_A_SHADOW_VERIFICATION_FLIPS,
    bootstrap_shadow_database,
)
from personalos.knowledge_edge.shadow_report import (
    LANE_A_SOURCE_IDS,
    NAMED_COVERAGE_GAP_SEC10_3,
    PERSON_SEARCH_PER_SCAN_BUDGET,
    build_lane_a_coverage,
    compute_lane_metrics,
    render_shadow_report,
)


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
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


class LaneASourceIdsTest(unittest.TestCase):
    def test_matches_bootstrap_flip_list(self) -> None:
        self.assertEqual(
            LANE_A_SOURCE_IDS, tuple(flip.source_id for flip in LANE_A_SHADOW_VERIFICATION_FLIPS)
        )
        self.assertEqual(len(LANE_A_SOURCE_IDS), 9)


class PrecisionRecallLeakageMathTest(unittest.TestCase):
    def test_hand_computed_precision_and_leakage(self) -> None:
        items = [
            {"verdict": "confirmed"},
            {"verdict": "confirmed"},
            {"verdict": "confirmed"},
            {"verdict": "rejected"},
            {"verdict": "duplicate_leak"},
            {"verdict": None},  # ungraded -- excluded from denominator
        ]
        metrics = compute_lane_metrics(lane="market_voices", precision_items=items, recall_items=[])

        # graded = 3 confirmed + 1 rejected + 1 duplicate_leak = 5
        self.assertEqual(metrics.precision_confirmed, 3)
        self.assertEqual(metrics.precision_rejected, 1)
        self.assertEqual(metrics.precision_duplicate_leak, 1)
        self.assertEqual(metrics.precision_ungraded, 1)
        self.assertAlmostEqual(metrics.precision, 3 / 5)
        self.assertAlmostEqual(metrics.duplicate_leakage, 1 / 5)

    def test_hand_computed_recall(self) -> None:
        recall_items = [
            {"found_by_system": True},
            {"found_by_system": True},
            {"found_by_system": False},
            {"found_by_system": False},
            {"found_by_system": False},
            {},  # ungraded
        ]
        metrics = compute_lane_metrics(
            lane="consequential_leaders", precision_items=[], recall_items=recall_items
        )
        self.assertEqual(metrics.recall_found, 2)
        self.assertEqual(metrics.recall_missed, 3)
        self.assertEqual(metrics.recall_ungraded, 1)
        self.assertAlmostEqual(metrics.recall, 2 / 5)

    def test_zero_graded_items_yields_none_not_zero_division(self) -> None:
        metrics = compute_lane_metrics(
            lane="curated_podcasts",
            precision_items=[{"verdict": None}, {}],
            recall_items=[{"found_by_system": None}],
        )
        self.assertIsNone(metrics.precision)
        self.assertIsNone(metrics.duplicate_leakage)
        self.assertIsNone(metrics.recall)

    def test_all_confirmed_yields_100_percent_precision_zero_leakage(self) -> None:
        items = [{"verdict": "confirmed"} for _ in range(10)]
        metrics = compute_lane_metrics(lane="market_voices", precision_items=items, recall_items=[])
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.duplicate_leakage, 0.0)

    def test_sample_size_counts_every_item_including_ungraded(self) -> None:
        items = [{"verdict": "confirmed"}, {"verdict": None}, {}]
        metrics = compute_lane_metrics(lane="market_voices", precision_items=items, recall_items=[])
        self.assertEqual(metrics.precision_sample_size, 3)


class LaneACoverageTest(unittest.TestCase):
    def test_zero_bootstrapped_sources_are_all_named_exceptions(self) -> None:
        with _migrated_connection() as connection:
            coverage = build_lane_a_coverage(connection)
        self.assertEqual(coverage.total_count, 9)
        self.assertEqual(coverage.monitored_count, 0)
        for row in coverage.rows:
            self.assertFalse(row.monitored)
            self.assertIsNotNone(row.exception_reason)

    def test_bootstrap_alone_does_not_mark_monitored_without_health_record(self) -> None:
        # bootstrap flips status -> active and records endpoint verification, but a
        # source is only "monitored" once it has an actual healthy scan-health row --
        # verification and a successful fetch are two different facts.
        with _migrated_connection() as connection:
            bootstrap_shadow_database(connection)
            coverage = build_lane_a_coverage(connection)
        self.assertEqual(coverage.monitored_count, 0)
        for row in coverage.rows:
            self.assertEqual(row.status, "active")
            self.assertIsNone(row.health_status)

    def test_healthy_source_health_row_marks_monitored(self) -> None:
        with _migrated_connection() as connection:
            bootstrap_shadow_database(connection)
            for source_id in LANE_A_SOURCE_IDS:
                ke.upsert_source_health(
                    connection,
                    health_id=f"health-{source_id}",
                    source_id=source_id,
                    status="healthy",
                    last_success_at="2026-07-17T00:00:00+00:00",
                )
            coverage = build_lane_a_coverage(connection)
        self.assertEqual(coverage.monitored_count, 9)
        self.assertEqual(coverage.total_count, 9)

    def test_missing_source_row_is_a_named_exception_not_a_shrunk_denominator(self) -> None:
        with _migrated_connection() as connection:
            bootstrap_shadow_database(connection)
            connection.execute(
                "DELETE FROM ke_source_endpoints WHERE source_id = 'ke-source-dwarkesh-podcast'"
            )
            connection.execute("DELETE FROM ke_sources WHERE source_id = 'ke-source-dwarkesh-podcast'")
            connection.commit()
            coverage = build_lane_a_coverage(connection)
        self.assertEqual(coverage.total_count, 9)
        missing_row = next(
            row for row in coverage.rows if row.source_id == "ke-source-dwarkesh-podcast"
        )
        self.assertEqual(missing_row.status, "missing")
        self.assertFalse(missing_row.monitored)


class RenderShadowReportTest(unittest.TestCase):
    def _metrics(self, **overrides):
        base = dict(
            lane="x",
            precision_items=[{"verdict": "confirmed"}, {"verdict": "rejected"}],
            recall_items=[{"found_by_system": True}],
        )
        base.update(overrides)
        return compute_lane_metrics(**base)

    def test_report_names_the_sec10_3_gap_by_default(self) -> None:
        with _migrated_connection() as connection:
            coverage = build_lane_a_coverage(connection)
        report = render_shadow_report(
            report_date="2026-07-31",
            lane_a_coverage=coverage,
            lane_a_metrics=self._metrics(),
            lane_b_metrics=self._metrics(),
            lane_c_metrics=self._metrics(),
            lane_d_event_count=0,
            lane_d_window_start="2026-07-01",
            lane_d_window_end="2026-07-14",
            person_search_calls_made=None,
        )
        self.assertIn(NAMED_COVERAGE_GAP_SEC10_3, report)
        self.assertIn("§10.3", report)

    def test_report_shows_person_search_quota_when_provided(self) -> None:
        with _migrated_connection() as connection:
            coverage = build_lane_a_coverage(connection)
        report = render_shadow_report(
            report_date="2026-07-31",
            lane_a_coverage=coverage,
            lane_a_metrics=self._metrics(),
            lane_b_metrics=self._metrics(),
            lane_c_metrics=self._metrics(),
            lane_d_event_count=2,
            lane_d_window_start="2026-07-01",
            lane_d_window_end="2026-07-14",
            person_search_calls_made=87,
        )
        self.assertIn(f"87/{PERSON_SEARCH_PER_SCAN_BUDGET} calls used", report)
        self.assertIn("2 Tier A event(s)", report)

    def test_report_is_deterministic(self) -> None:
        with _migrated_connection() as connection:
            coverage = build_lane_a_coverage(connection)
        kwargs = dict(
            report_date="2026-07-31",
            lane_a_coverage=coverage,
            lane_a_metrics=self._metrics(),
            lane_b_metrics=self._metrics(),
            lane_c_metrics=self._metrics(),
            lane_d_event_count=1,
            lane_d_window_start="2026-07-01",
            lane_d_window_end="2026-07-14",
            person_search_calls_made=10,
        )
        self.assertEqual(render_shadow_report(**kwargs), render_shadow_report(**kwargs))


if __name__ == "__main__":
    unittest.main()

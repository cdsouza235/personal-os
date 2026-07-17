"""P-KE-2C: ground-truth sample construction + freeze tests
(personalos.knowledge_edge.ground_truth_sample).

No network-capable import anywhere in this module or the module under test. Sample
construction operates purely on already-persisted fixture-scan state.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.knowledge_edge.adapters.contracts import DiscoveredEvent, DiscoveredMediaItem
from personalos.knowledge_edge.adapters.fixtures import (
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixtureFilingsAdapter,
    FixturePodcastFeedAdapter,
)
from personalos.knowledge_edge.ground_truth_sample import (
    ACK_STATUS_ACKNOWLEDGED,
    LANE_A_PRECISION_SAMPLE_SIZE,
    GroundTruthSampleError,
    SampleAcknowledgmentError,
    build_ground_truth_sample,
    parse_sample_header,
    render_frozen_sample_files,
    require_acknowledged_sample,
)
from personalos.knowledge_edge.scan_orchestrator import run_scan

NOW = datetime(2026, 7, 30, 21, 0, 0, tzinfo=UTC)
WINDOW_START = "2026-07-01"
WINDOW_END = "2026-07-14"  # 14 days inclusive


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


def _seed(connection: sqlite3.Connection) -> None:
    ke.create_source(
        connection, source_id="src-a", source_type="podcast_feed", lane="curated_podcasts", name="Podcast A"
    )
    ke.create_source(
        connection, source_id="src-b", source_type="youtube_channel", lane="market_voices", name="Channel B"
    )
    ke.create_source(
        connection,
        source_id="src-c",
        source_type="youtube_channel",
        lane="consequential_leaders",
        name="Channel C",
    )
    ke.create_source(
        connection, source_id="src-cal", source_type="calendar_provider", lane="earnings_events", name="Calendar"
    )
    ke.create_person(connection, person_id="person-b1", display_name="Voice One", category="market_voice")
    ke.create_person(
        connection, person_id="person-c1", display_name="Leader One", category="consequential_leader"
    )
    ke.create_company(
        connection,
        company_id="company-tier-a",
        legal_name="Tier A Co",
        display_name="Tier A Co",
        roster_group="nasdaq100_top10",
        roster_status="confirmed",
        priority_tier="tier_a",
    )
    ke.create_company(
        connection,
        company_id="company-tier-b",
        legal_name="Tier B Co",
        display_name="Tier B Co",
        roster_group="wgmi_candidate_pool",
        roster_status="candidate",
        priority_tier="tier_b",
    )


def _media_item(*, source_id, item_id, title, published_at, **extra) -> DiscoveredMediaItem:
    return DiscoveredMediaItem(
        source_id=source_id,
        source_specific_id=item_id,
        canonical_url=f"https://example.com/{item_id}",
        title=title,
        media_type=extra.pop("media_type", "video_interview"),
        source_precedence="official",
        format_hint=extra.pop("format_hint", "original_long_form_interview"),
        published_at=published_at,
        duration_seconds=extra.pop("duration_seconds", 3600),
        cursor_value=published_at,
        **extra,
    )


def _run_scan_with_lane_b_items(connection: sqlite3.Connection, *, count: int) -> None:
    items = tuple(
        _media_item(
            source_id="src-b",
            item_id=f"vid-b-{index}",
            title=f"Voice One appearance {index}",
            published_at=f"2026-07-{(index % 10) + 1:02d}T12:00:00+00:00",
            matched_person_id="person-b1",
        )
        for index in range(count)
    )
    run_scan(
        connection,
        scan_run_id=f"run-lane-b-{count}",
        run_type="full_scan",
        triggered_by="scheduler",
        now=NOW,
        queue_date="2026-07-14",
        podcast_adapter=FixturePodcastFeedAdapter({}),
        channel_adapter=FixtureChannelVideoAdapter({"src-b": items}),
        earnings_adapter=FixtureEarningsEventAdapter({}),
        filings_adapter=FixtureFilingsAdapter({}),
    )


def _run_full_four_lane_scan(connection: sqlite3.Connection) -> None:
    podcast_items = tuple(
        _media_item(
            source_id="src-a",
            item_id=f"ep-{index}",
            title=f"Episode {index}",
            published_at=f"2026-07-{(index % 10) + 1:02d}T09:00:00+00:00",
            format_hint="original_podcast_guest",
            media_type="podcast_episode",
        )
        for index in range(12)
    )
    lane_b_items = tuple(
        _media_item(
            source_id="src-b",
            item_id=f"vid-b-{index}",
            title=f"Voice One appearance {index}",
            published_at=f"2026-07-{(index % 10) + 1:02d}T12:00:00+00:00",
            matched_person_id="person-b1",
        )
        for index in range(3)
    )
    lane_c_items = tuple(
        _media_item(
            source_id="src-c",
            item_id=f"vid-c-{index}",
            title=f"Leader One appearance {index}",
            published_at=f"2026-07-{(index % 10) + 1:02d}T15:00:00+00:00",
            matched_person_id="person-c1",
            matched_company_id="company-tier-a",
        )
        for index in range(3)
    )
    earnings_adapter = FixtureEarningsEventAdapter(
        {
            "src-cal": (
                DiscoveredEvent(
                    source_id="src-cal",
                    company_id="company-tier-a",
                    event_id_hint="2026-q2",
                    event_type="quarterly_earnings",
                    scheduled_date="2026-07-10",
                    fiscal_period="2026-Q2",
                    time_precision="date_only",
                    schedule_confidence="confirmed_secondary",
                    schedule_source="fixture calendar provider",
                    cursor_value="0001",
                ),
                DiscoveredEvent(
                    source_id="src-cal",
                    company_id="company-tier-b",
                    event_id_hint="2026-q2-b",
                    event_type="quarterly_earnings",
                    scheduled_date="2026-07-11",
                    fiscal_period="2026-Q2",
                    time_precision="date_only",
                    schedule_confidence="confirmed_secondary",
                    schedule_source="fixture calendar provider",
                    cursor_value="0002",
                ),
            ),
        }
    )
    run_scan(
        connection,
        scan_run_id="run-full",
        run_type="full_scan",
        triggered_by="scheduler",
        now=NOW,
        queue_date="2026-07-14",
        podcast_adapter=FixturePodcastFeedAdapter({"src-a": podcast_items}),
        channel_adapter=FixtureChannelVideoAdapter({"src-b": lane_b_items, "src-c": lane_c_items}),
        earnings_adapter=earnings_adapter,
        filings_adapter=FixtureFilingsAdapter({}),
    )


class WindowValidationTest(unittest.TestCase):
    def test_window_shorter_than_14_days_is_rejected(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            with self.assertRaises(GroundTruthSampleError):
                build_ground_truth_sample(
                    connection,
                    window_start="2026-07-01",
                    window_end="2026-07-05",
                    generated_at=NOW.isoformat(),
                )

    def test_window_end_before_start_is_rejected(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            with self.assertRaises(GroundTruthSampleError):
                build_ground_truth_sample(
                    connection,
                    window_start="2026-07-14",
                    window_end="2026-07-01",
                    generated_at=NOW.isoformat(),
                )

    def test_lane_d_window_end_before_window_end_is_rejected(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            with self.assertRaises(GroundTruthSampleError):
                build_ground_truth_sample(
                    connection,
                    window_start=WINDOW_START,
                    window_end=WINDOW_END,
                    lane_d_window_end="2026-07-10",
                    generated_at=NOW.isoformat(),
                )


class SampleConstructionTest(unittest.TestCase):
    def test_full_four_lane_sample_composition(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            _run_full_four_lane_scan(connection)
            sample = build_ground_truth_sample(
                connection,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
                generated_at=NOW.isoformat(),
                coverage_gaps=("no §10.3 channels seeded yet",),
            )

        self.assertEqual(len(sample.lane_a_precision_check), LANE_A_PRECISION_SAMPLE_SIZE)
        self.assertEqual(len(sample.lane_b_precision_check), 3)
        self.assertEqual(len(sample.lane_c_precision_check), 3)
        self.assertEqual(sample.lane_b_recall_check_minimum, 15)
        self.assertEqual(sample.lane_c_recall_check_minimum, 10)
        self.assertEqual(len(sample.lane_d_events), 1)  # only the tier_a company
        self.assertEqual(sample.lane_d_events[0]["company_id"], "company-tier-a")
        self.assertEqual(sample.coverage_gaps, ("no §10.3 channels seeded yet",))

    def test_sample_caps_at_declared_size_when_pool_is_larger(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            _run_scan_with_lane_b_items(connection, count=50)
            sample = build_ground_truth_sample(
                connection,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
                generated_at=NOW.isoformat(),
            )
        self.assertEqual(len(sample.lane_b_precision_check), 30)

    def test_sample_construction_is_deterministic_given_fixed_inputs(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            _run_full_four_lane_scan(connection)
            sample_1 = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
            sample_2 = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
        self.assertEqual(sample_1.to_canonical_dict(), sample_2.to_canonical_dict())
        self.assertEqual(sample_1.checksum_sha256(), sample_2.checksum_sha256())

    def test_selection_is_stable_across_two_independently_built_databases(self) -> None:
        """The whole point of hashing the entity id (not discovery order) is that an
        independently-built shadow DB with the same logical items selects the same
        sample -- proven here by seeding two separate connections and comparing."""

        def _build(connection: sqlite3.Connection):
            _seed(connection)
            _run_scan_with_lane_b_items(connection, count=50)
            return build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )

        with _migrated_connection() as connection_a:
            sample_a = _build(connection_a)
        with _migrated_connection() as connection_b:
            sample_b = _build(connection_b)

        ids_a = [item["media_item_id"] for item in sample_a.lane_b_precision_check]
        ids_b = [item["media_item_id"] for item in sample_b.lane_b_precision_check]
        self.assertEqual(ids_a, ids_b)

    def test_items_outside_window_are_excluded(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            out_of_window_item = _media_item(
                source_id="src-a",
                item_id="ep-out-of-window",
                title="Too late",
                published_at="2026-08-01T09:00:00+00:00",
                format_hint="original_podcast_guest",
                media_type="podcast_episode",
            )
            run_scan(
                connection,
                scan_run_id="run-out-of-window",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-14",
                podcast_adapter=FixturePodcastFeedAdapter({"src-a": (out_of_window_item,)}),
                channel_adapter=FixtureChannelVideoAdapter({}),
                earnings_adapter=FixtureEarningsEventAdapter({}),
                filings_adapter=FixtureFilingsAdapter({}),
            )
            sample = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
        self.assertEqual(sample.lane_a_precision_check, ())

    def test_lane_d_window_can_extend_past_window_end_for_zero_event_case(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            earnings_adapter = FixtureEarningsEventAdapter(
                {
                    "src-cal": (
                        DiscoveredEvent(
                            source_id="src-cal",
                            company_id="company-tier-a",
                            event_id_hint="2026-q3",
                            event_type="quarterly_earnings",
                            scheduled_date="2026-07-20",  # past WINDOW_END
                            fiscal_period="2026-Q3",
                            time_precision="date_only",
                            schedule_confidence="confirmed_secondary",
                            schedule_source="fixture calendar provider",
                            cursor_value="0001",
                        ),
                    ),
                }
            )
            run_scan(
                connection,
                scan_run_id="run-lane-d-extended",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-14",
                podcast_adapter=FixturePodcastFeedAdapter({}),
                channel_adapter=FixtureChannelVideoAdapter({}),
                earnings_adapter=earnings_adapter,
                filings_adapter=FixtureFilingsAdapter({}),
            )

            sample_unextended = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
            self.assertEqual(sample_unextended.lane_d_events, ())

            sample_extended = build_ground_truth_sample(
                connection,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
                lane_d_window_end="2026-07-21",
                generated_at=NOW.isoformat(),
            )
            self.assertEqual(len(sample_extended.lane_d_events), 1)


class FreezeArtifactTest(unittest.TestCase):
    def test_render_produces_matching_checksum_and_valid_header(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            _run_full_four_lane_scan(connection)
            sample = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
        files = render_frozen_sample_files(
            sample,
            sample_date="2026-07-30",
            frozen_json_relative_path="docs/knowledge_edge/ground_truth_samples/ground_truth_sample_2026-07-30.json",
            markdown_relative_path="docs/knowledge_edge/GROUND_TRUTH_SAMPLE_2026-07-30.md",
        )
        self.assertEqual(files.checksum_sha256, sample.checksum_sha256())
        header = parse_sample_header(files.markdown_text)
        self.assertEqual(header["checksum_sha256"], sample.checksum_sha256())
        self.assertIn("PENDING CONDUCTOR ACKNOWLEDGMENT", header["status"])
        self.assertEqual(header["acknowledged_by"], "")

    def test_render_is_deterministic(self) -> None:
        with _migrated_connection() as connection:
            _seed(connection)
            _run_full_four_lane_scan(connection)
            sample = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
        files_1 = render_frozen_sample_files(
            sample, sample_date="2026-07-30", frozen_json_relative_path="x.json", markdown_relative_path="x.md"
        )
        files_2 = render_frozen_sample_files(
            sample, sample_date="2026-07-30", frozen_json_relative_path="x.json", markdown_relative_path="x.md"
        )
        self.assertEqual(files_1.frozen_json_text, files_2.frozen_json_text)
        self.assertEqual(files_1.markdown_text, files_2.markdown_text)


class AcknowledgmentGateTest(unittest.TestCase):
    def _sample_files(self):
        with _migrated_connection() as connection:
            _seed(connection)
            _run_full_four_lane_scan(connection)
            sample = build_ground_truth_sample(
                connection, window_start=WINDOW_START, window_end=WINDOW_END, generated_at=NOW.isoformat()
            )
        return render_frozen_sample_files(
            sample,
            sample_date="2026-07-30",
            frozen_json_relative_path="x.json",
            markdown_relative_path="x.md",
        )

    def test_pending_sample_is_refused(self) -> None:
        files = self._sample_files()
        with self.assertRaises(SampleAcknowledgmentError):
            require_acknowledged_sample(files.markdown_text, frozen_json_text=files.frozen_json_text)

    def test_acknowledged_sample_with_matching_checksum_passes(self) -> None:
        files = self._sample_files()
        acknowledged_text = files.markdown_text.replace(
            'status: "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"',
            f'status: "{ACK_STATUS_ACKNOWLEDGED}"',
        ).replace('acknowledged_by: ""', 'acknowledged_by: "chris"').replace(
            'acknowledged_at: ""', 'acknowledged_at: "2026-07-31T00:00:00+00:00"'
        )
        fields = require_acknowledged_sample(acknowledged_text, frozen_json_text=files.frozen_json_text)
        self.assertEqual(fields["acknowledged_by"], "chris")

    def test_acknowledged_sample_with_tampered_frozen_file_is_refused(self) -> None:
        files = self._sample_files()
        acknowledged_text = files.markdown_text.replace(
            'status: "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"',
            f'status: "{ACK_STATUS_ACKNOWLEDGED}"',
        ).replace('acknowledged_by: ""', 'acknowledged_by: "chris"').replace(
            'acknowledged_at: ""', 'acknowledged_at: "2026-07-31T00:00:00+00:00"'
        )
        tampered_json = files.frozen_json_text.replace("}", ', "tampered": true}', 1)
        with self.assertRaises(SampleAcknowledgmentError):
            require_acknowledged_sample(acknowledged_text, frozen_json_text=tampered_json)

    def test_missing_header_fence_is_refused(self) -> None:
        with self.assertRaises(SampleAcknowledgmentError):
            parse_sample_header("# no header here\n")


if __name__ == "__main__":
    unittest.main()

"""P-KE-1B: scan_orchestrator end-to-end tests against fixture adapters only.

Covers the Phase 1 acceptance criteria this packet is responsible for: a fixture
four-lane queue build, idempotency under re-run (including re-processing the same
scan window), candidate-cap enforcement, the §8.3 P0-rule boundary cases, dedupe
collisions, and deterministic ordering. No network-capable import appears anywhere
in this module or in anything it imports.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import personalos.knowledge_edge.state as ke
from personalos.config import DEFAULT_TIMEZONE, Environment, PersonalOSConfig
from personalos.db.connection import connect_sqlite
from personalos.db.migrations import apply_migrations
from personalos.knowledge_edge.adapters.contracts import (
    DiscoveredEvent,
    DiscoveredFiling,
    DiscoveredMediaItem,
)
from personalos.knowledge_edge.adapters.fixtures import (
    FixtureChannelVideoAdapter,
    FixtureEarningsEventAdapter,
    FixtureFilingsAdapter,
    FixturePodcastFeedAdapter,
)
from personalos.knowledge_edge.engine import ranking
from personalos.knowledge_edge.scan_orchestrator import build_queue_snapshot_view, run_scan

NOW = datetime(2026, 7, 16, 21, 0, 0, tzinfo=UTC)


def _config_for(runtime_dir: Path, environment: Environment) -> PersonalOSConfig:
    directory_name = "dev" if environment is Environment.DEVELOPMENT else "test"
    return PersonalOSConfig(
        environment=environment,
        timezone=DEFAULT_TIMEZONE,
        database_path=runtime_dir / directory_name / "personalos.sqlite3",
    )


@contextmanager
def _connected_sqlite(config: PersonalOSConfig, *, runtime_dir: Path) -> Iterator[sqlite3.Connection]:
    connection = connect_sqlite(config, runtime_dir=runtime_dir)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def _migrated_connection() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir) / "runtime"
        config = _config_for(runtime_dir, Environment.TEST)
        with _connected_sqlite(config, runtime_dir=runtime_dir) as connection:
            apply_migrations(connection)
            yield connection


def _reset_all_cursors(connection: sqlite3.Connection) -> None:
    """Reset every source's persisted cursor to "never scanned", via public state APIs only.

    Simulates the amendment's §11.1 catch-up/overlap-window scenario (the source's
    cursor is reset, as if the Mac was off and the same window is being re-scanned)
    without touching ``ke_scan_cursors`` directly: reads each source's current cursor
    row with ``get_scan_cursor`` and rewrites it with ``advance_scan_cursor``, which is
    the same state-layer entry point ``run_scan`` itself uses to persist cursors.
    """
    for source in ke.list_sources(connection):
        cursor = ke.get_scan_cursor(connection, source_id=source["source_id"])
        if cursor is None:
            continue
        ke.advance_scan_cursor(
            connection,
            cursor_id=cursor["cursor_id"],
            source_id=cursor["source_id"],
            last_successful_cursor_value=None,
            overlap_window_seconds=cursor["overlap_window_seconds"],
        )


def _seed_registries(connection: sqlite3.Connection) -> None:
    ke.create_source(
        connection, source_id="src-dwarkesh", source_type="podcast_feed", lane="curated_podcasts", name="Dwarkesh Podcast"
    )
    ke.create_source(
        connection, source_id="src-cnbc", source_type="youtube_channel", lane="market_voices", name="CNBC Television"
    )
    ke.create_source(
        connection,
        source_id="src-frontier-ai",
        source_type="youtube_channel",
        lane="consequential_leaders",
        name="Official Frontier AI Lab Channel",
    )
    ke.create_source(
        connection, source_id="src-calendar", source_type="calendar_provider", lane="earnings_events", name="Earnings Calendar"
    )
    ke.create_source(
        connection, source_id="src-edgar", source_type="sec_edgar", lane="earnings_events", name="SEC EDGAR"
    )
    ke.create_person(connection, person_id="ke-person-tom-lee", display_name="Tom Lee", category="market_voice")
    ke.create_person(
        connection, person_id="ke-person-jensen-huang", display_name="Jensen Huang", category="consequential_leader"
    )


def _four_lane_records() -> dict:
    podcast_episode = DiscoveredMediaItem(
        source_id="src-dwarkesh",
        source_specific_id="ep-100",
        canonical_url="https://dwarkesh.com/ep-100",
        title="Episode 100: A Long Conversation",
        media_type="podcast_episode",
        source_precedence="official",
        format_hint="original_podcast_guest",
        feed_guid="dwarkesh-guid-100",
        published_at="2026-07-16T18:00:00+00:00",
        duration_seconds=5400,
        cursor_value="2026-07-16T18:00:00+00:00",
    )
    p0_interview = DiscoveredMediaItem(
        source_id="src-frontier-ai",
        source_specific_id="vid-jensen-1",
        canonical_url="https://example.com/watch?v=jensen-1",
        title="Jensen Huang: The Future of Compute",
        media_type="video_interview",
        source_precedence="official",
        format_hint="original_long_form_interview",
        underlying_id="jensen-interview-1",
        channel_id="frontier-ai-official",
        matched_person_id="ke-person-jensen-huang",
        matched_company_id="ke-company-nvda",
        published_at="2026-07-16T12:00:00+00:00",
        duration_seconds=3600,
        cursor_value="2026-07-16T12:00:00+00:00",
    )
    market_voice_appearance = DiscoveredMediaItem(
        source_id="src-cnbc",
        source_specific_id="vid-tomlee-1",
        canonical_url="https://example.com/watch?v=tomlee-1",
        title="Tom Lee on Bitcoin and Market Outlook",
        media_type="video_interview",
        source_precedence="official",
        format_hint="financial_media_segment",
        matched_person_id="ke-person-tom-lee",
        published_at="2026-07-16T14:00:00+00:00",
        duration_seconds=900,
        cursor_value="2026-07-16T14:00:00+00:00",
    )
    earnings_event = DiscoveredEvent(
        source_id="src-calendar",
        company_id="ke-company-nvda",
        event_id_hint="2026-q2",
        event_type="quarterly_earnings",
        scheduled_date="2026-08-19",
        fiscal_period="2026-Q2",
        time_precision="date_only",
        schedule_confidence="confirmed_secondary",
        schedule_source="fixture calendar provider",
        cursor_value="0001",
    )
    filing = DiscoveredFiling(
        company_id="ke-company-nvda",
        filing_type="8-K",
        filing_url="https://www.sec.gov/example/nvda-8k-2026q2",
        filed_at="2026-07-15T00:00:00+00:00",
        fiscal_period="2026-Q2",
        cursor_value="0001",
    )
    return {
        "podcast_episode": podcast_episode,
        "p0_interview": p0_interview,
        "market_voice_appearance": market_voice_appearance,
        "earnings_event": earnings_event,
        "filing": filing,
    }


def _build_adapters(records: dict):
    podcast_adapter = FixturePodcastFeedAdapter(
        {"src-dwarkesh": tuple(records.get("podcast_items", (records["podcast_episode"],)))}
    )
    channel_adapter = FixtureChannelVideoAdapter(
        {
            "src-frontier-ai": tuple(records.get("frontier_ai_items", (records["p0_interview"],))),
            "src-cnbc": tuple(records.get("cnbc_items", (records["market_voice_appearance"],))),
        }
    )
    earnings_adapter = FixtureEarningsEventAdapter({"src-calendar": (records["earnings_event"],)})
    filings_adapter = FixtureFilingsAdapter({"src-edgar": (records["filing"],)})
    return podcast_adapter, channel_adapter, earnings_adapter, filings_adapter


class FourLaneEndToEndTest(unittest.TestCase):
    def test_scan_populates_all_four_lanes_and_expected_queue_sections(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            summary = run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            self.assertEqual(summary.status, "completed")
            self.assertEqual(summary.media_items_created, 3)
            self.assertEqual(summary.events_created, 1)

            p1_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p1_core_podcasts")
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            p2_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            earnings_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="tomorrow_earnings_events")

            podcast_item = ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100")
            interview_item = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-jensen-1")
            voice_item = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-tomlee-1")

            self.assertEqual([row["entity_id"] for row in p1_rows], [podcast_item["media_item_id"]])
            self.assertEqual([row["entity_id"] for row in p0_rows], [interview_item["media_item_id"]])
            self.assertEqual([row["entity_id"] for row in p2_rows], [voice_item["media_item_id"]])
            self.assertEqual(len(earnings_rows), 1)

            event = ke.get_scheduled_event(connection, "event-ke-company-nvda-2026-q2")
            self.assertIsNotNone(event)
            self.assertIn("https://www.sec.gov/example/nvda-8k-2026q2", event["filing_urls"])

            self.assertEqual(interview_item["directness_class"], "direct_primary")
            self.assertEqual(voice_item["directness_class"], "direct_primary")  # known duration >= threshold

    def test_coverage_report_and_source_health_recorded(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)
            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            reports = ke.list_coverage_reports(connection, report_date="2026-07-16")
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]["report"]["sources_healthy"], 5)
            for source_id in ("src-dwarkesh", "src-cnbc", "src-frontier-ai", "src-calendar", "src-edgar"):
                health = ke.get_source_health(connection, source_id=source_id)
                self.assertEqual(health["status"], "healthy")


class IdempotencyTest(unittest.TestCase):
    def test_rerunning_after_natural_cursor_advance_creates_no_new_content(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            def _run(run_id: str):
                return run_scan(
                    connection,
                    scan_run_id=run_id,
                    run_type="full_scan",
                    triggered_by="scheduler",
                    now=NOW,
                    queue_date="2026-07-16",
                    podcast_adapter=podcast_adapter,
                    channel_adapter=channel_adapter,
                    earnings_adapter=earnings_adapter,
                    filings_adapter=filings_adapter,
                )

            first = _run("run-1")
            media_count_after_first = ke.count_media_items(connection)
            events_count_after_first = ke.count_scheduled_events(connection)
            queue_rows_after_first = ke.count_queue_snapshots(connection)

            second = _run("run-2")

            self.assertEqual(first.media_items_created, 3)
            self.assertEqual(second.media_items_created, 0)
            self.assertEqual(second.events_created, 0)
            self.assertEqual(ke.count_media_items(connection), media_count_after_first)
            self.assertEqual(ke.count_scheduled_events(connection), events_count_after_first)
            self.assertEqual(ke.count_queue_snapshots(connection), queue_rows_after_first)

    def test_reprocessing_same_window_via_reset_cursor_is_idempotent(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            media_count_after_first = ke.count_media_items(connection)
            occurrences_before = len(
                ke.list_discovery_occurrences(
                    connection, media_item_id=ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100")["media_item_id"]
                )
            )

            # Simulate the amendment's own §11.1 catch-up/overlap-window scenario:
            # the source's cursor is reset (as if the Mac was off and the same
            # window is being re-scanned).
            _reset_all_cursors(connection)

            run_scan(
                connection,
                scan_run_id="run-2",
                run_type="manual_scan_now",
                triggered_by="operator",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            self.assertEqual(ke.count_media_items(connection), media_count_after_first)
            occurrences_after = len(
                ke.list_discovery_occurrences(
                    connection, media_item_id=ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100")["media_item_id"]
                )
            )
            self.assertGreater(occurrences_after, occurrences_before)


class CapEnforcementTest(unittest.TestCase):
    def _many_market_voice_items(self, count: int) -> tuple[DiscoveredMediaItem, ...]:
        items = []
        for index in range(count):
            items.append(
                DiscoveredMediaItem(
                    source_id="src-cnbc",
                    source_specific_id=f"vid-mv-{index}",
                    canonical_url=f"https://example.com/watch?v=mv-{index}",
                    title=f"Market Voice Appearance {index}",
                    media_type="video_interview",
                    source_precedence="official",
                    format_hint="original_long_form_interview",
                    matched_person_id="ke-person-tom-lee",
                    published_at="2026-07-16T10:00:00+00:00",
                    duration_seconds=600 + index,  # small deterministic score spread
                    cursor_value=f"2026-07-16T10:00:0{index}+00:00" if index < 10 else f"2026-07-16T10:00:{index}+00:00",
                )
            )
        return tuple(items)

    def test_per_lane_candidate_cap_promotes_only_top_n_leaves_rest_as_candidate(self) -> None:
        cap = ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP
        total = cap + 3
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            records["cnbc_items"] = self._many_market_voice_items(total)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            p2_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertEqual(len(p2_rows), cap)

            all_voice_items = ke.list_media_items(connection, source_id="src-cnbc")
            self.assertEqual(len(all_voice_items), total)
            queued = [item for item in all_voice_items if item["queue_visibility_state"] == "queued"]
            still_candidate = [item for item in all_voice_items if item["queue_visibility_state"] == "candidate"]
            self.assertEqual(len(queued), cap)
            self.assertEqual(len(still_candidate), total - cap)

    def test_p0_lane_is_never_capped(self) -> None:
        cap = ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP
        total = cap + 4
        items = []
        for index in range(total):
            items.append(
                DiscoveredMediaItem(
                    source_id="src-frontier-ai",
                    source_specific_id=f"vid-p0-{index}",
                    canonical_url=f"https://example.com/watch?v=p0-{index}",
                    title=f"Jensen Huang Appearance {index}",
                    media_type="video_interview",
                    source_precedence="official",
                    format_hint="original_long_form_interview",
                    matched_person_id="ke-person-jensen-huang",
                    matched_company_id="ke-company-nvda",
                    published_at="2026-07-16T10:00:00+00:00",
                    duration_seconds=600,
                    cursor_value=f"cursor-{index:04d}",
                )
            )
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            records["frontier_ai_items"] = tuple(items)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            self.assertEqual(len(p0_rows), total)

    def _many_podcast_items(self, count: int) -> tuple[DiscoveredMediaItem, ...]:
        items = []
        for index in range(count):
            items.append(
                DiscoveredMediaItem(
                    source_id="src-dwarkesh",
                    source_specific_id=f"ep-p1-{index}",
                    canonical_url=f"https://dwarkesh.com/ep-p1-{index}",
                    title=f"Podcast Episode {index}",
                    media_type="podcast_episode",
                    source_precedence="official",
                    format_hint="original_podcast_guest",
                    feed_guid=f"dwarkesh-guid-p1-{index}",
                    published_at="2026-07-16T18:00:00+00:00",
                    duration_seconds=1200 + index,
                    cursor_value=f"2026-07-16T18:00:0{index}+00:00" if index < 10 else f"2026-07-16T18:00:{index}+00:00",
                )
            )
        return tuple(items)

    def test_total_cross_lane_cap_trims_combined_p1_p2_pool_by_score(self) -> None:
        """§12.1: the candidate surface is bounded by a total cap across P1+P2,
        not just a per-lane cap -- a strong P2 item can out-rank a weak P1 item
        for one of the shared total slots. The per-lane cap (5) alone can never
        exceed the provisional total cap (12) with only two cappable lanes, so
        this test patches the total cap down to below what the per-lane caps
        alone would admit (5 + 5 = 10) to actually exercise the trim."""
        per_lane_cap = ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP
        total_cap = per_lane_cap  # deliberately below per_lane_cap * 2 == 10
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            records["podcast_items"] = self._many_podcast_items(per_lane_cap)
            records["cnbc_items"] = self._many_market_voice_items(per_lane_cap)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            with mock.patch.object(ranking, "PROVISIONAL_TOTAL_P1_P2_CANDIDATE_CAP", total_cap):
                run_scan(
                    connection,
                    scan_run_id="run-1",
                    run_type="full_scan",
                    triggered_by="scheduler",
                    now=NOW,
                    queue_date="2026-07-16",
                    podcast_adapter=podcast_adapter,
                    channel_adapter=channel_adapter,
                    earnings_adapter=earnings_adapter,
                    filings_adapter=filings_adapter,
                )

            p1_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p1_core_podcasts")
            p2_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertEqual(len(p1_rows) + len(p2_rows), total_cap)

            podcast_items = ke.list_media_items(connection, source_id="src-dwarkesh")
            voice_items = ke.list_media_items(connection, source_id="src-cnbc")
            combined = list(podcast_items) + list(voice_items)
            self.assertEqual(len(combined), 2 * per_lane_cap)

            expected_queued_ids = {
                item["media_item_id"]
                for item in sorted(
                    combined, key=lambda item: (-(item["priority_score"] or 0.0), item["media_item_id"])
                )[:total_cap]
            }
            actual_queued_ids = {
                item["media_item_id"] for item in combined if item["queue_visibility_state"] == "queued"
            }
            self.assertEqual(actual_queued_ids, expected_queued_ids)

            actual_still_candidate = {
                item["media_item_id"] for item in combined if item["queue_visibility_state"] == "candidate"
            }
            self.assertEqual(actual_still_candidate, {item["media_item_id"] for item in combined} - expected_queued_ids)


class P0BoundaryCaseTest(unittest.TestCase):
    def test_unknown_duration_financial_segment_is_ambiguous_and_not_dropped(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            ambiguous_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-ambiguous-1",
                canonical_url="https://example.com/watch?v=ambiguous-1",
                title="Jensen Huang Segment (duration unknown)",
                media_type="video_interview",
                source_precedence="reputable_secondary",
                format_hint="financial_media_segment",
                matched_person_id="ke-person-jensen-huang",
                duration_seconds=None,
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0001",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (ambiguous_item,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            item = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-ambiguous-1")
            self.assertEqual(item["directness_class"], "ambiguous")
            # §8.3: ambiguous is "surfaced demoted with an ambiguity label" -- never
            # promoted to P0, never dropped. Not dropped: the row survives with a
            # non-suppressed visibility state and its ambiguity label intact in the
            # explanation. Never P0: it must not appear in the p0_consequential_leaders
            # (or any other priority-gated) queue_snapshot section, regardless of its
            # source lane being consequential_leaders.
            self.assertNotEqual(item["queue_visibility_state"], "suppressed")
            self.assertIn("ambiguous_unknown_duration_demoted", item["priority_explanation"])
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            self.assertNotIn(item["media_item_id"], [row["entity_id"] for row in p0_rows])
            p2_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertNotIn(item["media_item_id"], [row["entity_id"] for row in p2_rows])

            # "surfaced demoted", not silently dropped: it must actually be present
            # somewhere in the composed queue view, not merely absent from P0/P2.
            snapshot = build_queue_snapshot_view(connection, queue_date="2026-07-16")
            demoted_ids = {row["entity_id"] for row in snapshot["demoted_ambiguous"]}
            self.assertIn(item["media_item_id"], demoted_ids)
            demoted_row = next(
                row for row in snapshot["demoted_ambiguous"] if row["entity_id"] == item["media_item_id"]
            )
            self.assertIn("ambiguous_unknown_duration_demoted", demoted_row["explanation"])

    def test_unknown_duration_financial_segment_in_market_voices_lane_is_not_promoted_to_p2(self) -> None:
        """Same §8.3 rule, applied via engine/directness.py's shared P0/P2 gate to
        Lane B (market_voices): the eligibility check is per-candidate and
        lane-independent, so an ambiguous item must not win a p2_market_voices slot
        either, not just a p0_consequential_leaders one."""
        with _migrated_connection() as connection:
            _seed_registries(connection)
            ambiguous_item = DiscoveredMediaItem(
                source_id="src-cnbc",
                source_specific_id="vid-mv-ambiguous-1",
                canonical_url="https://example.com/watch?v=mv-ambiguous-1",
                title="Tom Lee Segment (duration unknown)",
                media_type="video_interview",
                source_precedence="reputable_secondary",
                format_hint="financial_media_segment",
                matched_person_id="ke-person-tom-lee",
                duration_seconds=None,
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0001",
            )
            records = _four_lane_records()
            records["cnbc_items"] = (ambiguous_item,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            item = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-ambiguous-1")
            self.assertEqual(item["directness_class"], "ambiguous")
            self.assertNotEqual(item["queue_visibility_state"], "suppressed")
            p2_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertNotIn(item["media_item_id"], [row["entity_id"] for row in p2_rows])
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            self.assertNotIn(item["media_item_id"], [row["entity_id"] for row in p0_rows])

            snapshot = build_queue_snapshot_view(connection, queue_date="2026-07-16")
            demoted_ids = {row["entity_id"] for row in snapshot["demoted_ambiguous"]}
            self.assertIn(item["media_item_id"], demoted_ids)
            demoted_row = next(
                row for row in snapshot["demoted_ambiguous"] if row["entity_id"] == item["media_item_id"]
            )
            self.assertIn("ambiguous_unknown_duration_demoted", demoted_row["explanation"])

    def test_ambiguous_item_never_promoted_even_when_mixed_with_eligible_p0_candidates(self) -> None:
        """Regression guard for the exact bug: lane membership alone (every candidate
        in the consequential_leaders lane mapped straight into p0_consequential_leaders)
        must not promote an ambiguous item just because genuinely eligible P0 items
        share its lane in the same scan."""
        with _migrated_connection() as connection:
            _seed_registries(connection)
            eligible_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-eligible-1",
                canonical_url="https://example.com/watch?v=eligible-1",
                title="Jensen Huang: Keynote",
                media_type="video_interview",
                source_precedence="official",
                format_hint="original_long_form_interview",
                matched_person_id="ke-person-jensen-huang",
                duration_seconds=1800,
                published_at="2026-07-16T09:00:00+00:00",
                cursor_value="0001",
            )
            ambiguous_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-ambiguous-2",
                canonical_url="https://example.com/watch?v=ambiguous-2",
                title="Jensen Huang Segment (duration unknown)",
                media_type="video_interview",
                source_precedence="reputable_secondary",
                format_hint="financial_media_segment",
                matched_person_id="ke-person-jensen-huang",
                duration_seconds=None,
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0002",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (eligible_item, ambiguous_item)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            eligible = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-eligible-1")
            ambiguous = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-ambiguous-2")
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            p0_ids = [row["entity_id"] for row in p0_rows]
            self.assertIn(eligible["media_item_id"], p0_ids)
            self.assertNotIn(ambiguous["media_item_id"], p0_ids)

            snapshot = build_queue_snapshot_view(connection, queue_date="2026-07-16")
            demoted_ids = {row["entity_id"] for row in snapshot["demoted_ambiguous"]}
            self.assertIn(ambiguous["media_item_id"], demoted_ids)
            self.assertNotIn(eligible["media_item_id"], demoted_ids)

    def test_below_threshold_known_duration_financial_segment_is_suppressed_not_ambiguous(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            short_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-short-1",
                canonical_url="https://example.com/watch?v=short-1",
                title="Jensen Huang Brief Comment",
                media_type="video_interview",
                source_precedence="official",
                format_hint="financial_media_segment",
                matched_person_id="ke-person-jensen-huang",
                duration_seconds=60,
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0001",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (short_item,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            item = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-short-1")
            self.assertEqual(item["directness_class"], "direct_primary")
            self.assertEqual(item["queue_visibility_state"], "suppressed")

    def test_excluded_format_reaction_video_is_suppressed(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            reaction_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-reaction-1",
                canonical_url="https://example.com/watch?v=reaction-1",
                title="Reacting to Jensen Huang's Interview",
                media_type="clip",
                source_precedence="broad_search",
                format_hint="reaction_video",
                matched_person_id="ke-person-jensen-huang",
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0001",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (reaction_item,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            item = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-reaction-1")
            self.assertEqual(item["queue_visibility_state"], "suppressed")
            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            self.assertNotIn(item["media_item_id"], [row["entity_id"] for row in p0_rows])


class DedupeCollisionTest(unittest.TestCase):
    def test_audio_and_video_versions_share_underlying_id_grouped_one_canonical(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            interview_video = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-dup-1",
                canonical_url="https://example.com/watch?v=dup-1",
                title="Jensen Huang: Live Keynote",
                media_type="video_interview",
                source_precedence="official",
                format_hint="keynote_or_product_presentation",
                underlying_id="keynote-underlying-1",
                matched_person_id="ke-person-jensen-huang",
                published_at="2026-07-16T09:00:00+00:00",
                cursor_value="0001",
            )
            interview_replay = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-dup-2",
                canonical_url="https://example.com/watch?v=dup-2",
                title="Jensen Huang: Live Keynote",
                media_type="video_interview",
                source_precedence="official",
                format_hint="keynote_or_product_presentation",
                underlying_id="keynote-underlying-1",
                matched_person_id="ke-person-jensen-huang",
                published_at="2026-07-16T09:05:00+00:00",
                cursor_value="0002",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (interview_video, interview_replay)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            first = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-dup-1")
            second = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-dup-2")
            self.assertIsNotNone(first["canonical_group_id"])
            self.assertEqual(first["canonical_group_id"], second["canonical_group_id"])
            self.assertTrue(first["is_canonical"])
            self.assertFalse(second["is_canonical"])
            self.assertEqual(second["queue_visibility_state"], "suppressed")

            group_id = first["canonical_group_id"]
            group = ke.create_canonical_group  # sanity: function exists (imported via ke module)
            self.assertTrue(callable(group))
            members = ke.list_canonical_group_members(connection, canonical_group_id=group_id)
            self.assertEqual({member["media_item_id"] for member in members}, {first["media_item_id"], second["media_item_id"]})

            p0_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p0_consequential_leaders")
            self.assertEqual([row["entity_id"] for row in p0_rows], [first["media_item_id"]])


class DeterministicOrderingTest(unittest.TestCase):
    def test_identical_inputs_produce_identical_queue_snapshot_ordering(self) -> None:
        def _run_and_collect() -> list[tuple[str, int, str]]:
            with _migrated_connection() as connection:
                _seed_registries(connection)
                records = _four_lane_records()
                records["cnbc_items"] = CapEnforcementTest()._many_market_voice_items(4)
                podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)
                run_scan(
                    connection,
                    scan_run_id="run-1",
                    run_type="full_scan",
                    triggered_by="scheduler",
                    now=NOW,
                    queue_date="2026-07-16",
                    podcast_adapter=podcast_adapter,
                    channel_adapter=channel_adapter,
                    earnings_adapter=earnings_adapter,
                    filings_adapter=filings_adapter,
                )
                rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
                return [(row["entity_id"], row["rank_position"], row["explanation"]) for row in rows]

        first_run = _run_and_collect()
        second_run = _run_and_collect()
        self.assertEqual(first_run, second_run)
        self.assertTrue(first_run)


class DemotedAmbiguousPersistenceTest(unittest.TestCase):
    """C5 fold-in (phase-end checkpoint 2026-07-16): the demoted/ambiguous tier is
    now persisted per scan into ``ke_queue_snapshot_demoted`` (migration 00022),
    not just composed at read time, so a past date's queue is fully recorded."""

    def test_demoted_ambiguous_item_is_persisted_after_scan(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            ambiguous_item = DiscoveredMediaItem(
                source_id="src-frontier-ai",
                source_specific_id="vid-ambiguous-persist-1",
                canonical_url="https://example.com/watch?v=ambiguous-persist-1",
                title="Jensen Huang Segment (duration unknown, persisted)",
                media_type="video_interview",
                source_precedence="reputable_secondary",
                format_hint="financial_media_segment",
                matched_person_id="ke-person-jensen-huang",
                duration_seconds=None,
                published_at="2026-07-16T10:00:00+00:00",
                cursor_value="0001",
            )
            records = _four_lane_records()
            records["frontier_ai_items"] = (ambiguous_item,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            item = ke.get_media_item_by_dedupe_key(connection, "src-frontier-ai:vid-ambiguous-persist-1")
            persisted = ke.list_queue_snapshot_demoted(connection, queue_date="2026-07-16")
            self.assertEqual([row["entity_id"] for row in persisted], [item["media_item_id"]])
            self.assertIn("ambiguous_unknown_duration_demoted", persisted[0]["explanation"])

            # Matches the same-run live composition exactly.
            live = build_queue_snapshot_view(connection, queue_date="2026-07-16")
            self.assertEqual(
                {row["entity_id"] for row in persisted},
                {row["entity_id"] for row in live["demoted_ambiguous"]},
            )

    def test_demoted_ambiguous_persistence_is_recomputed_not_accumulated_across_scans(self) -> None:
        """A second same-date scan must leave exactly the current demoted set
        persisted, not grow without bound (same C2 recompute-and-supersede
        discipline applied to this table)."""
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)
            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            self.assertEqual(ke.list_queue_snapshot_demoted(connection, queue_date="2026-07-16"), [])

            run_scan(
                connection,
                scan_run_id="run-2",
                run_type="manual_scan_now",
                triggered_by="operator",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            self.assertEqual(ke.list_queue_snapshot_demoted(connection, queue_date="2026-07-16"), [])


class SameDateRescanTest(unittest.TestCase):
    """C2 (phase-end checkpoint 2026-07-16): a same-``queue_date`` second scan (the
    amendment's own "scan-now" flow) must not corrupt ``ke_queue_snapshots``
    ordering or let a section's row count drift past its per-lane cap."""

    def _voice_item(
        self,
        *,
        index: int,
        cursor_value: str,
        duration_seconds: int,
        source_precedence: str = "official",
    ) -> DiscoveredMediaItem:
        return DiscoveredMediaItem(
            source_id="src-cnbc",
            source_specific_id=f"vid-mv-{index}",
            canonical_url=f"https://example.com/watch?v=mv-{index}",
            title=f"Market Voice Appearance {index}",
            media_type="video_interview",
            source_precedence=source_precedence,
            format_hint="original_long_form_interview",
            matched_person_id="ke-person-tom-lee",
            published_at="2026-07-16T10:00:00+00:00",
            duration_seconds=duration_seconds,
            cursor_value=cursor_value,
        )

    def test_reordering_second_scan_produces_no_duplicate_ranks(self) -> None:
        """Reproduces the checkpoint report's own probe: scan 1 records P2 ranks
        1, 2; a same-date second scan discovers one new item that outranks both.
        The fixed section must end up with three uniquely-ranked rows (the new
        item first), never two rows sharing ``rank_position == 1``."""
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            # item A: duration 3000s (50m) -> 3.0 penalty -> score 177
            # item B: duration 4200s (70m) -> 5.0 penalty -> score 175
            records["cnbc_items"] = (
                self._voice_item(index=0, cursor_value="0000", duration_seconds=3000),
                self._voice_item(index=1, cursor_value="0001", duration_seconds=4200),
            )
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)
            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            first_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertEqual([row["rank_position"] for row in first_rows], [1, 2])
            item_a = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-0")
            item_b = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-1")
            self.assertEqual([row["entity_id"] for row in first_rows], [item_a["media_item_id"], item_b["media_item_id"]])

            # Second same-date scan: a new, more recent-cursor item C (duration
            # 600s -> no penalty -> score 180) outranks both A and B.
            records2 = dict(records)
            records2["cnbc_items"] = (
                self._voice_item(index=2, cursor_value="0002", duration_seconds=600),
            )
            podcast_adapter2, channel_adapter2, earnings_adapter2, filings_adapter2 = _build_adapters(records2)
            run_scan(
                connection,
                scan_run_id="run-2",
                run_type="manual_scan_now",
                triggered_by="operator",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter2,
                channel_adapter=channel_adapter2,
                earnings_adapter=earnings_adapter2,
                filings_adapter=filings_adapter2,
            )

            second_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            item_c = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-2")

            # No duplicate rank positions.
            ranks = [row["rank_position"] for row in second_rows]
            self.assertEqual(ranks, sorted(set(ranks)))
            self.assertEqual(len(second_rows), 3)
            # C (highest score) now leads; A, B follow in original score order.
            self.assertEqual(
                [row["entity_id"] for row in second_rows],
                [item_c["media_item_id"], item_a["media_item_id"], item_b["media_item_id"]],
            )
            self.assertEqual(ranks, [1, 2, 3])

    def test_per_lane_cap_holds_across_same_date_scans(self) -> None:
        """The candidate surface's per-lane cap must not be exceeded by a second
        same-date scan: a fresh, higher-scoring item discovered on scan 2 must
        evict the weakest already-recorded item rather than being appended
        alongside all five prior rows (which would grow the section past its
        cap)."""
        cap = ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            # Four items with strictly decreasing scores via duration-penalty
            # spread (180, 179.833, 179.667, 179.5), plus one deliberately weak
            # item (reputable_secondary precedence -> score 150) to fill the cap
            # at exactly 5 and be the clear eviction candidate.
            records["cnbc_items"] = (
                self._voice_item(index=0, cursor_value="0000", duration_seconds=1200),
                self._voice_item(index=1, cursor_value="0001", duration_seconds=1300),
                self._voice_item(index=2, cursor_value="0002", duration_seconds=1400),
                self._voice_item(index=3, cursor_value="0003", duration_seconds=1500),
                self._voice_item(
                    index=4, cursor_value="0004", duration_seconds=1200,
                    source_precedence="reputable_secondary",
                ),
            )
            self.assertEqual(cap, 5, "test's fixed 5-item setup assumes the provisional per-lane cap is 5")
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)
            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            first_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertEqual(len(first_rows), cap)

            # Second same-date scan discovers one new item (duration 1250s ->
            # 0.833 penalty -> score ~179.917): better than items 1-4, worse than
            # item 0, so it must displace item 4 (score 150) rather than growing
            # the section to 6 rows.
            records2 = dict(records)
            records2["cnbc_items"] = (
                self._voice_item(index=5, cursor_value="0005", duration_seconds=1250),
            )
            podcast_adapter2, channel_adapter2, earnings_adapter2, filings_adapter2 = _build_adapters(records2)
            run_scan(
                connection,
                scan_run_id="run-2",
                run_type="manual_scan_now",
                triggered_by="operator",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter2,
                channel_adapter=channel_adapter2,
                earnings_adapter=earnings_adapter2,
                filings_adapter=filings_adapter2,
            )

            second_rows = ke.list_queue_snapshot(connection, queue_date="2026-07-16", section="p2_market_voices")
            self.assertEqual(len(second_rows), cap, "per-lane cap must hold across same-date scans")
            ranks = [row["rank_position"] for row in second_rows]
            self.assertEqual(ranks, list(range(1, cap + 1)))

            item4 = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-4")
            item5 = ke.get_media_item_by_dedupe_key(connection, "src-cnbc:vid-mv-5")
            entity_ids = [row["entity_id"] for row in second_rows]
            self.assertNotIn(item4["media_item_id"], entity_ids)
            self.assertIn(item5["media_item_id"], entity_ids)


class ExpirySweepProductionPathTest(unittest.TestCase):
    """C1 (phase-end checkpoint 2026-07-16): before this packet,
    ``ranking.is_saved_item_expired``/``is_replay_item_expired`` were unit-tested
    only -- nothing on any driveable path ever called them, so a saved or replay
    item lived forever. ``run_scan`` now calls ``_sweep_expired_decisions`` before
    building the day's queue (re-verification recipe item (1))."""

    def _empty_adapters(self):
        return (
            FixturePodcastFeedAdapter({}),
            FixtureChannelVideoAdapter({}),
            FixtureEarningsEventAdapter({}),
            FixtureFilingsAdapter({}),
        )

    def test_scan_expires_a_saved_media_item_past_the_14_day_cap(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            ke.create_media_item(
                connection,
                media_item_id="media-saved-old",
                source_id="src-dwarkesh",
                source_specific_id="ep-saved-old",
                canonical_url="https://dwarkesh.com/ep-saved-old",
                title="A Saved Episode",
                media_type="podcast_episode",
                source_precedence="official",
                dedupe_key="src-dwarkesh:ep-saved-old",
                published_at="2026-07-01T00:00:00+00:00",
                discovered_at="2026-07-01T00:00:00+00:00",
                directness_class="direct_primary",
                priority_score=100.0,
            )
            ke.update_media_decision_state(
                connection, media_item_id="media-saved-old", decision_state="save_for_later"
            )
            fifteen_days_ago = (NOW - timedelta(days=15)).isoformat()
            ke.upsert_user_decision(
                connection,
                decision_id="decision-saved-old",
                entity_type="media_item",
                entity_id="media-saved-old",
                decision_state="save_for_later",
                decided_at=fifteen_days_ago,
            )

            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = self._empty_adapters()
            run_scan(
                connection,
                scan_run_id="run-sweep",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            expired_item = ke.get_media_item(connection, "media-saved-old")
            self.assertEqual(expired_item["queue_visibility_state"], "expired")

            history = ke.list_decision_history(
                connection, entity_type="media_item", entity_id="media-saved-old"
            )
            expiry_rows = [row for row in history if row["track"] == "queue_visibility_state"]
            self.assertEqual(len(expiry_rows), 1)
            expiry_row = expiry_rows[0]
            self.assertEqual(expiry_row["to_value"], "expired")
            self.assertEqual(expiry_row["changed_by"], "system:expiry_sweep")
            self.assertIn("saved-14d", expiry_row["reason"])
            self.assertIn(fifteen_days_ago, expiry_row["reason"])

    def test_scan_does_not_expire_a_saved_media_item_within_the_14_day_cap(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            ke.create_media_item(
                connection,
                media_item_id="media-saved-fresh",
                source_id="src-dwarkesh",
                source_specific_id="ep-saved-fresh",
                canonical_url="https://dwarkesh.com/ep-saved-fresh",
                title="A Freshly Saved Episode",
                media_type="podcast_episode",
                source_precedence="official",
                dedupe_key="src-dwarkesh:ep-saved-fresh",
                published_at="2026-07-10T00:00:00+00:00",
                discovered_at="2026-07-10T00:00:00+00:00",
                directness_class="direct_primary",
                priority_score=100.0,
            )
            ke.update_media_decision_state(
                connection, media_item_id="media-saved-fresh", decision_state="save_for_later"
            )
            seven_days_ago = (NOW - timedelta(days=7)).isoformat()
            ke.upsert_user_decision(
                connection,
                decision_id="decision-saved-fresh",
                entity_type="media_item",
                entity_id="media-saved-fresh",
                decision_state="save_for_later",
                decided_at=seven_days_ago,
            )

            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = self._empty_adapters()
            run_scan(
                connection,
                scan_run_id="run-sweep",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            fresh_item = ke.get_media_item(connection, "media-saved-fresh")
            # Not expired -- it is instead resurfaced into "saved_to_reconsider" this
            # scan (it is the only saved item), which flips candidate -> queued via
            # the same _record_section path every other queued section uses.
            self.assertEqual(fresh_item["queue_visibility_state"], "queued")

            history = ke.list_decision_history(
                connection, entity_type="media_item", entity_id="media-saved-fresh"
            )
            self.assertFalse(
                [row for row in history if row["changed_by"] == "system:expiry_sweep"]
            )

    def test_scan_expires_a_replay_item_past_the_7_day_cap(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            eight_days_before_now = NOW - timedelta(days=8)
            ke.create_scheduled_event(
                connection,
                event_id="event-replay-old",
                company_id="ke-company-nvda",
                event_type="quarterly_earnings",
                scheduled_date=eight_days_before_now.date().isoformat(),
                schedule_confidence="confirmed_official",
                end_time_utc=eight_days_before_now.isoformat(),
                replay_url="https://example.com/replay/old",
            )
            for status in ("confirmed", "scheduled", "live", "ended", "replay_pending", "replay_available"):
                ke.update_event_status(connection, event_id="event-replay-old", event_status=status)
            ke.update_event_decision_state(
                connection, event_id="event-replay-old", decision_state="save_replay"
            )
            ke.upsert_user_decision(
                connection,
                decision_id="decision-replay-old",
                entity_type="scheduled_event",
                entity_id="event-replay-old",
                decision_state="save_replay",
                decided_at=eight_days_before_now.isoformat(),
            )

            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = self._empty_adapters()
            run_scan(
                connection,
                scan_run_id="run-sweep",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            expired_event = ke.get_scheduled_event(connection, "event-replay-old")
            self.assertEqual(expired_event["queue_visibility_state"], "expired")

            history = ke.list_decision_history(
                connection, entity_type="scheduled_event", entity_id="event-replay-old"
            )
            expiry_rows = [row for row in history if row["track"] == "queue_visibility_state"]
            self.assertEqual(len(expiry_rows), 1)
            expiry_row = expiry_rows[0]
            self.assertEqual(expiry_row["to_value"], "expired")
            self.assertEqual(expiry_row["changed_by"], "system:expiry_sweep")
            self.assertIn("replay-7d", expiry_row["reason"])


class CrossRunCorrectionTest(unittest.TestCase):
    """P-KE-2A iteration 2 (Conductor scope amendment): §8.1's "recognize
    corrected/reissued episodes without producing duplicates" evaluated *across*
    scan runs, not just within one batch -- the cross-run counterpart of
    ``DedupeCollisionTest`` above."""

    def test_reissued_episode_new_guid_matching_underlying_id_weeks_later_is_corrected_not_duplicated(
        self,
    ) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            original_episode = DiscoveredMediaItem(
                source_id="src-dwarkesh",
                source_specific_id="ep-100-guid-v1",
                canonical_url="https://dwarkesh.com/ep-100",
                title="Episode 100: A Long Conversation",
                media_type="podcast_episode",
                source_precedence="official",
                format_hint="original_podcast_guest",
                feed_guid="ep-100-guid-v1",
                underlying_id="100",
                published_at="2026-07-01T18:00:00+00:00",
                duration_seconds=5400,
                cursor_value="2026-07-01T18:00:00+00:00|ep-100-guid-v1",
            )
            records["podcast_items"] = (original_episode,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )

            original = ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100-guid-v1")
            self.assertIsNotNone(original)
            self.assertEqual(original["content_status"], "ranked")
            media_item_id = original["media_item_id"]
            media_count_after_first = ke.count_media_items(connection)

            # Two weeks later, the feed republishes the same episode (matched by
            # itunes:episode -> underlying_id="100") under a corrected GUID/title.
            corrected_episode = DiscoveredMediaItem(
                source_id="src-dwarkesh",
                source_specific_id="ep-100-guid-v2-corrected",
                canonical_url="https://dwarkesh.com/ep-100-corrected",
                title="Episode 100: A Long Conversation (Corrected Audio)",
                media_type="podcast_episode",
                source_precedence="official",
                format_hint="original_podcast_guest",
                feed_guid="ep-100-guid-v2-corrected",
                underlying_id="100",
                published_at="2026-07-01T18:00:00+00:00",
                duration_seconds=5400,
                cursor_value="2026-07-15T09:00:00+00:00|ep-100-guid-v2-corrected",
            )
            records["podcast_items"] = (corrected_episode,)
            podcast_adapter_2, channel_adapter_2, earnings_adapter_2, filings_adapter_2 = _build_adapters(records)

            summary = run_scan(
                connection,
                scan_run_id="run-2",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW + timedelta(weeks=2),
                queue_date="2026-07-30",
                podcast_adapter=podcast_adapter_2,
                channel_adapter=channel_adapter_2,
                earnings_adapter=earnings_adapter_2,
                filings_adapter=filings_adapter_2,
            )

            self.assertEqual(summary.media_items_created, 0)
            self.assertEqual(ke.count_media_items(connection), media_count_after_first)
            self.assertIsNone(ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100-guid-v1"))

            corrected = ke.get_media_item(connection, media_item_id)
            self.assertEqual(corrected["source_specific_id"], "ep-100-guid-v2-corrected")
            self.assertEqual(corrected["dedupe_key"], "src-dwarkesh:ep-100-guid-v2-corrected")
            self.assertEqual(corrected["feed_guid"], "ep-100-guid-v2-corrected")
            self.assertEqual(corrected["underlying_id"], "100")
            self.assertEqual(corrected["title"], "Episode 100: A Long Conversation (Corrected Audio)")
            self.assertEqual(corrected["canonical_url"], "https://dwarkesh.com/ep-100-corrected")
            self.assertEqual(corrected["content_status"], "normalized")
            # Untouched by the correction: it is an identity fix, not a re-classification.
            self.assertEqual(corrected["directness_class"], original["directness_class"])
            self.assertEqual(corrected["priority_score"], original["priority_score"])

            history = ke.list_decision_history(connection, entity_type="media_item", entity_id=media_item_id)
            content_status_transitions = [
                (row["from_value"], row["to_value"]) for row in history if row["track"] == "content_status"
            ]
            self.assertIn(("ranked", "corrected"), content_status_transitions)
            self.assertIn(("corrected", "normalized"), content_status_transitions)
            correction_row = next(row for row in history if row["to_value"] == "corrected")
            self.assertEqual(correction_row["changed_by"], "system:cross_run_identity_correction")
            self.assertIn("ep-100-guid-v1", correction_row["reason"])
            self.assertIn("ep-100-guid-v2-corrected", correction_row["reason"])

    def test_new_episode_with_different_underlying_id_creates_new_row_not_corrected(self) -> None:
        with _migrated_connection() as connection:
            _seed_registries(connection)
            records = _four_lane_records()
            original_episode = DiscoveredMediaItem(
                source_id="src-dwarkesh",
                source_specific_id="ep-100-guid-v1",
                canonical_url="https://dwarkesh.com/ep-100",
                title="Episode 100: A Long Conversation",
                media_type="podcast_episode",
                source_precedence="official",
                format_hint="original_podcast_guest",
                feed_guid="ep-100-guid-v1",
                underlying_id="100",
                published_at="2026-07-01T18:00:00+00:00",
                duration_seconds=5400,
                cursor_value="2026-07-01T18:00:00+00:00|ep-100-guid-v1",
            )
            records["podcast_items"] = (original_episode,)
            podcast_adapter, channel_adapter, earnings_adapter, filings_adapter = _build_adapters(records)

            run_scan(
                connection,
                scan_run_id="run-1",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW,
                queue_date="2026-07-16",
                podcast_adapter=podcast_adapter,
                channel_adapter=channel_adapter,
                earnings_adapter=earnings_adapter,
                filings_adapter=filings_adapter,
            )
            media_count_after_first = ke.count_media_items(connection)

            new_episode = DiscoveredMediaItem(
                source_id="src-dwarkesh",
                source_specific_id="ep-101",
                canonical_url="https://dwarkesh.com/ep-101",
                title="Episode 101: A Different Conversation",
                media_type="podcast_episode",
                source_precedence="official",
                format_hint="original_podcast_guest",
                feed_guid="ep-101-guid",
                underlying_id="101",
                published_at="2026-07-08T18:00:00+00:00",
                duration_seconds=4000,
                cursor_value="2026-07-08T18:00:00+00:00|ep-101-guid",
            )
            records["podcast_items"] = (new_episode,)
            podcast_adapter_2, channel_adapter_2, earnings_adapter_2, filings_adapter_2 = _build_adapters(records)

            summary = run_scan(
                connection,
                scan_run_id="run-2",
                run_type="full_scan",
                triggered_by="scheduler",
                now=NOW + timedelta(weeks=1),
                queue_date="2026-07-23",
                podcast_adapter=podcast_adapter_2,
                channel_adapter=channel_adapter_2,
                earnings_adapter=earnings_adapter_2,
                filings_adapter=filings_adapter_2,
            )

            self.assertEqual(summary.media_items_created, 1)
            self.assertEqual(ke.count_media_items(connection), media_count_after_first + 1)

            original = ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-100-guid-v1")
            self.assertIsNotNone(original)
            self.assertEqual(original["title"], "Episode 100: A Long Conversation")

            new_row = ke.get_media_item_by_dedupe_key(connection, "src-dwarkesh:ep-101")
            self.assertIsNotNone(new_row)
            self.assertEqual(new_row["underlying_id"], "101")
            self.assertEqual(new_row["title"], "Episode 101: A Different Conversation")

            history = ke.list_decision_history(connection, entity_type="media_item", entity_id=new_row["media_item_id"])
            self.assertEqual([row for row in history if row["track"] == "content_status" and row["to_value"] == "corrected"], [])


if __name__ == "__main__":
    unittest.main()

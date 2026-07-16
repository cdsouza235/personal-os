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
from datetime import UTC, datetime
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
from personalos.knowledge_edge.scan_orchestrator import run_scan

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
            connection.execute("UPDATE ke_scan_cursors SET last_successful_cursor_value = NULL")

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


if __name__ == "__main__":
    unittest.main()
